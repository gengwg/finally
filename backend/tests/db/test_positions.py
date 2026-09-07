"""Positions upsert, lookup and delete."""

import sqlite3

import pytest

from app.db import (
    delete_position,
    get_connection,
    get_position,
    list_positions,
    upsert_position,
)


def test_upsert_inserts_then_updates(db):
    upsert_position("AAPL", 10, 190.0)
    upsert_position("AAPL", 15, 192.0)

    positions = list_positions()
    assert len(positions) == 1
    assert positions[0].quantity == 15
    assert positions[0].avg_cost == 192.0


def test_get_position_is_case_insensitive(db):
    upsert_position("aapl", 5, 190.0)
    position = get_position("AAPL")
    assert position is not None
    assert position.ticker == "AAPL"
    assert get_position("aapl") == position


def test_get_missing_position(db):
    assert get_position("AAPL") is None


def test_listed_in_ticker_order(db):
    for ticker in ("TSLA", "AAPL", "MSFT"):
        upsert_position(ticker, 1, 1.0)
    assert [p.ticker for p in list_positions()] == ["AAPL", "MSFT", "TSLA"]


def test_delete(db):
    upsert_position("AAPL", 10, 190.0)
    delete_position("aapl")
    assert get_position("AAPL") is None


def test_delete_missing_is_silent(db):
    delete_position("AAPL")
    assert list_positions() == []


def test_unique_constraint(db):
    upsert_position("AAPL", 10, 190.0)
    with pytest.raises(sqlite3.IntegrityError), get_connection() as conn:
        conn.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES ('x', 'default', 'AAPL', 1, 1, 'now')
            """
        )


def test_to_dict(db):
    upsert_position("AAPL", 10, 190.0)
    position = get_position("AAPL")
    assert position.to_dict() == {
        "ticker": "AAPL",
        "quantity": 10.0,
        "avg_cost": 190.0,
        "updated_at": position.updated_at,
    }
