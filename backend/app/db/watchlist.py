"""Watchlist reads and writes."""

from __future__ import annotations

import sqlite3
import uuid

from .connection import get_connection, use_connection
from .models import WatchlistEntry, normalise_ticker, now_iso
from .profile import DEFAULT_USER_ID


def list_watchlist(*, user_id: str = DEFAULT_USER_ID) -> list[WatchlistEntry]:
    """Watched tickers, oldest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ticker, added_at FROM watchlist
            WHERE user_id = ? ORDER BY added_at, rowid
            """,
            (user_id,),
        ).fetchall()
    return [WatchlistEntry(ticker=r["ticker"], added_at=r["added_at"]) for r in rows]


def add_to_watchlist(
    ticker: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Add a ticker. False if it was already on the watchlist."""
    with use_connection(conn) as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), user_id, normalise_ticker(ticker), now_iso()),
        )
        return cursor.rowcount > 0


def remove_from_watchlist(
    ticker: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Remove a ticker. False if it was not on the watchlist."""
    with use_connection(conn) as db:
        cursor = db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, normalise_ticker(ticker)),
        )
        return cursor.rowcount > 0
