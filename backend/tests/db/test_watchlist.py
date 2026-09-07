"""Watchlist behaviour."""

import sqlite3

import pytest

from app.db import add_to_watchlist, get_connection, list_watchlist, remove_from_watchlist


def test_add_returns_true_then_false(db):
    assert add_to_watchlist("PYPL") is True
    assert add_to_watchlist("PYPL") is False
    assert [e.ticker for e in list_watchlist()].count("PYPL") == 1


def test_tickers_are_normalised(db):
    assert add_to_watchlist("  pypl ") is True
    assert "PYPL" in [e.ticker for e in list_watchlist()]
    assert add_to_watchlist("PyPl") is False
    assert remove_from_watchlist("pypl") is True


def test_remove_missing_returns_false(db):
    assert remove_from_watchlist("ZZZZ") is False


def test_listed_oldest_first(db):
    add_to_watchlist("PYPL")
    add_to_watchlist("SHOP")
    entries = list_watchlist()
    assert [e.ticker for e in entries[-2:]] == ["PYPL", "SHOP"]
    assert [e.added_at for e in entries] == sorted(e.added_at for e in entries)


def test_unique_constraint_per_user(db):
    add_to_watchlist("PYPL")
    with pytest.raises(sqlite3.IntegrityError), get_connection() as conn:
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES ('x', 'default', 'PYPL', 'now')"
        )
    # the same ticker for a different user is fine
    assert add_to_watchlist("PYPL", user_id="default") is False


def test_entry_to_dict(db):
    entry = list_watchlist()[0]
    assert entry.to_dict() == {"ticker": entry.ticker, "added_at": entry.added_at}
