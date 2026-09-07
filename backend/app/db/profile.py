"""User profile: the cash balance."""

from __future__ import annotations

import sqlite3

from .connection import get_connection, use_connection
from .models import now_iso

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0


def get_cash_balance(*, user_id: str = DEFAULT_USER_ID) -> float:
    """Cash available to spend. 0.0 if the profile does not exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
    return row["cash_balance"] if row else 0.0


def set_cash_balance(
    amount: float,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Overwrite the cash balance, creating the profile if it is missing."""
    with use_connection(conn) as db:
        db.execute(
            """
            INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET cash_balance = excluded.cash_balance
            """,
            (user_id, amount, now_iso()),
        )
