"""Fixtures for the API tests: the real app over a temp DB, with a stand-in price feed."""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.market import MarketDataSource

SEED_PRICES = {"AAPL": 190.0, "MSFT": 400.0}


class RecordingSource(MarketDataSource):
    """A market data source that records its lifecycle instead of generating prices.

    Keeps the cache under the test's control while still exercising the real
    add_ticker / remove_ticker wiring the watchlist routes depend on.
    """

    def __init__(self) -> None:
        self.tickers: list[str] = []
        self.started = False
        self.stopped = False

    async def start(self, tickers: list[str]) -> None:
        self.tickers = list(tickers)
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self.tickers:
            self.tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self.tickers:
            self.tickers.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self.tickers)


@pytest.fixture
def source():
    return RecordingSource()


@pytest.fixture
def app(tmp_path, monkeypatch, source):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-frontend-here"))
    monkeypatch.setattr(main, "create_market_data_source", lambda cache: source)

    app = main.create_app()
    for ticker, price in SEED_PRICES.items():
        app.state.price_cache.update(ticker, price)
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def cache(app):
    return app.state.price_cache
