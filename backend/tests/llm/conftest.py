"""Fixtures for the chat flow: a real temp DB, a real price cache, a stubbed model."""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import init_db
from app.llm import client as llm_client
from app.market import MarketDataSource, PriceCache

SEED_PRICES = {"AAPL": 190.0, "MSFT": 400.0, "NVDA": 120.0}


def reply_json(message="ok", trades=(), watchlist_changes=()):
    return json.dumps(
        {
            "message": message,
            "trades": list(trades),
            "watchlist_changes": list(watchlist_changes),
        }
    )


class StubModel:
    """Stands in for litellm.completion: canned content, recorded call kwargs."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.error: Exception | None = None
        self.content: str = reply_json()

    def set(self, message="ok", trades=(), watchlist_changes=()) -> None:
        self.content = reply_json(message, trades, watchlist_changes)

    def raw(self, content: str) -> None:
        self.content = content

    def fail(self, error: Exception) -> None:
        self.error = error

    @property
    def messages(self) -> list[dict]:
        """The prompt from the most recent call."""
        return self.calls[-1]["messages"]

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class RecordingSource(MarketDataSource):
    """Records lifecycle calls instead of generating prices, so the cache stays fixed."""

    def __init__(self) -> None:
        self.tickers: list[str] = []

    async def start(self, tickers: list[str]) -> None:
        self.tickers = list(tickers)

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self.tickers:
            self.tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self.tickers:
            self.tickers.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self.tickers)


@pytest.fixture
def model(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    stub = StubModel()
    monkeypatch.setattr(llm_client.litellm, "completion", stub)
    return stub


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    init_db()


@pytest.fixture
def cache(db):
    cache = PriceCache()
    for ticker, price in SEED_PRICES.items():
        cache.update(ticker, price)
    return cache


@pytest.fixture
def source():
    return RecordingSource()


@pytest.fixture
def app(tmp_path, monkeypatch, source):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-frontend-here"))
    monkeypatch.delenv("LLM_MOCK", raising=False)
    monkeypatch.setattr(main, "create_market_data_source", lambda cache: source)

    app = main.create_app()
    for ticker, price in SEED_PRICES.items():
        app.state.price_cache.update(ticker, price)
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
