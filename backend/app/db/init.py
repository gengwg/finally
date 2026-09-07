"""Lazy schema creation and seeding."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .connection import get_connection
from .models import now_iso
from .profile import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID
from .watchlist import add_to_watchlist

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


def init_db() -> None:
    """Create the schema and seed defaults if they are missing. Safe to call repeatedly."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        _seed(conn)
        conn.commit()


def _seed(conn: sqlite3.Connection) -> None:
    """Insert the default profile and watchlist, leaving any existing rows alone."""
    conn.execute(
        """
        INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)
        """,
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now_iso()),
    )
    # Only seed the watchlist on a genuinely fresh database: an empty watchlist is a
    # legitimate state once the user has removed every ticker.
    already_seeded = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? LIMIT 1", (DEFAULT_USER_ID,)
    ).fetchone()
    if already_seeded:
        return
    for ticker in DEFAULT_WATCHLIST:
        add_to_watchlist(ticker, user_id=DEFAULT_USER_ID, conn=conn)
