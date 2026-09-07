"""Portfolio value snapshots for the P&L chart."""

from __future__ import annotations

import sqlite3
import uuid

from .connection import get_connection, use_connection
from .models import Snapshot, now_iso
from .profile import DEFAULT_USER_ID


def record_snapshot(
    total_value: float,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> Snapshot:
    """Append a portfolio value snapshot and return it."""
    snapshot = Snapshot(total_value=total_value, recorded_at=now_iso())
    with use_connection(conn) as db:
        db.execute(
            """
            INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), user_id, snapshot.total_value, snapshot.recorded_at),
        )
    return snapshot


def list_snapshots(*, limit: int = 500, user_id: str = DEFAULT_USER_ID) -> list[Snapshot]:
    """The newest `limit` snapshots, returned oldest first so charts plot left to right."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT total_value, recorded_at FROM (
                SELECT total_value, recorded_at, rowid FROM portfolio_snapshots
                WHERE user_id = ? ORDER BY recorded_at DESC, rowid DESC LIMIT ?
            ) ORDER BY recorded_at, rowid
            """,
            (user_id, limit),
        ).fetchall()
    return [Snapshot(total_value=r["total_value"], recorded_at=r["recorded_at"]) for r in rows]
