"""Open positions."""

from __future__ import annotations

import sqlite3
import uuid

from .connection import get_connection, use_connection
from .models import Position, normalise_ticker, now_iso
from .profile import DEFAULT_USER_ID


def _to_position(row: sqlite3.Row) -> Position:
    return Position(
        ticker=row["ticker"],
        quantity=row["quantity"],
        avg_cost=row["avg_cost"],
        updated_at=row["updated_at"],
    )


def list_positions(*, user_id: str = DEFAULT_USER_ID) -> list[Position]:
    """All open positions in ticker order."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ticker, quantity, avg_cost, updated_at FROM positions
            WHERE user_id = ? ORDER BY ticker
            """,
            (user_id,),
        ).fetchall()
    return [_to_position(r) for r in rows]


def get_position(ticker: str, *, user_id: str = DEFAULT_USER_ID) -> Position | None:
    """One position, or None if the ticker is not held."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT ticker, quantity, avg_cost, updated_at FROM positions
            WHERE user_id = ? AND ticker = ?
            """,
            (user_id, normalise_ticker(ticker)),
        ).fetchone()
    return _to_position(row) if row else None


def upsert_position(
    ticker: str,
    quantity: float,
    avg_cost: float,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Create or replace the position in a ticker."""
    with use_connection(conn) as db:
        db.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, ticker) DO UPDATE SET
                quantity = excluded.quantity,
                avg_cost = excluded.avg_cost,
                updated_at = excluded.updated_at
            """,
            (
                str(uuid.uuid4()),
                user_id,
                normalise_ticker(ticker),
                quantity,
                avg_cost,
                now_iso(),
            ),
        )


def delete_position(
    ticker: str,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Remove a position. Silent if it is not there."""
    with use_connection(conn) as db:
        db.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, normalise_ticker(ticker)),
        )
