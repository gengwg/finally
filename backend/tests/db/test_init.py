"""Schema creation and seeding."""

import sqlite3

import pytest

from app.db import (
    add_to_watchlist,
    get_cash_balance,
    get_connection,
    init_db,
    list_watchlist,
    remove_from_watchlist,
    set_cash_balance,
)
from app.db.init import DEFAULT_WATCHLIST

TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


def test_init_creates_file_and_parent_directory(db_env):
    assert not db_env.parent.exists()
    init_db()
    assert db_env.exists()


def test_init_creates_all_tables(db):
    with get_connection() as conn:
        names = {
            r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert TABLES <= names


def test_seeds_default_profile_and_watchlist(db):
    assert get_cash_balance() == 10000.0
    assert [e.ticker for e in list_watchlist()] == DEFAULT_WATCHLIST


def test_init_is_idempotent(db):
    init_db()
    init_db()
    assert len(list_watchlist()) == len(DEFAULT_WATCHLIST)
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM users_profile").fetchone()["n"] == 1


def test_init_preserves_existing_state(db):
    set_cash_balance(4242.0)
    remove_from_watchlist("AAPL")
    add_to_watchlist("PYPL")

    init_db()

    assert get_cash_balance() == 4242.0
    tickers = [e.ticker for e in list_watchlist()]
    assert "AAPL" not in tickers  # a removed ticker is not resurrected on restart
    assert "PYPL" in tickers


def test_foreign_keys_are_enforced(db):
    with pytest.raises(sqlite3.IntegrityError), get_connection() as conn:
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES ('x', 'ghost', 'AAPL', 'now')"
        )
