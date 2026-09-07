"""Trade log."""

import sqlite3

import pytest

from app.db import get_connection, list_trades, record_trade


def test_record_returns_the_stored_trade(db):
    trade = record_trade("aapl", "buy", 10, 190.0)
    assert trade.ticker == "AAPL"
    assert trade.id
    assert list_trades() == [trade]


def test_listed_newest_first(db):
    record_trade("AAPL", "buy", 1, 100.0)
    record_trade("MSFT", "buy", 2, 200.0)
    record_trade("TSLA", "sell", 3, 300.0)
    assert [t.ticker for t in list_trades()] == ["TSLA", "MSFT", "AAPL"]


def test_limit_keeps_the_newest(db):
    for i in range(5):
        record_trade("AAPL", "buy", i + 1, 100.0)
    trades = list_trades(limit=2)
    assert [t.quantity for t in trades] == [5, 4]


def test_side_is_constrained(db):
    with pytest.raises(sqlite3.IntegrityError):
        record_trade("AAPL", "hold", 1, 100.0)
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM trades").fetchone()["n"] == 0


def test_to_dict(db):
    trade = record_trade("AAPL", "sell", 2.5, 190.0)
    assert trade.to_dict() == {
        "id": trade.id,
        "ticker": "AAPL",
        "side": "sell",
        "quantity": 2.5,
        "price": 190.0,
        "executed_at": trade.executed_at,
    }
