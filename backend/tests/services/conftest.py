"""Fixtures for the service tests: a real seeded SQLite file and a real PriceCache."""

import pytest

from app.db import init_db
from app.market import PriceCache


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    """A fresh, seeded database per test."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    init_db()


@pytest.fixture
def cache():
    """Known prices, so trade and P&L maths is exact."""
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("MSFT", 400.0)
    return cache
