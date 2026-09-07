"""Trade log (append-only)."""

from __future__ import annotations

import sqlite3
import uuid

from .connection import get_connection, use_connection
from .models import Trade, normalise_ticker, now_iso
from .profile import DEFAULT_USER_ID


def record_trade(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> Trade:
    """Append a trade and return it."""
    trade = Trade(
        id=str(uuid.uuid4()),
        ticker=normalise_ticker(ticker),
        side=side,
        quantity=quantity,
        price=price,
        executed_at=now_iso(),
    )
    with use_connection(conn) as db:
        db.execute(
            """
            INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.id,
                user_id,
                trade.ticker,
                trade.side,
                trade.quantity,
                trade.price,
                trade.executed_at,
            ),
        )
    return trade


def list_trades(*, limit: int = 100, user_id: str = DEFAULT_USER_ID) -> list[Trade]:
    """Most recent trades, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, ticker, side, quantity, price, executed_at FROM trades
            WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        Trade(
            id=r["id"],
            ticker=r["ticker"],
            side=r["side"],
            quantity=r["quantity"],
            price=r["price"],
            executed_at=r["executed_at"],
        )
        for r in rows
    ]
