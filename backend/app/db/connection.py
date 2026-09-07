"""SQLite connection handling."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = "db/finally.db"


def db_path() -> Path:
    """Resolved database file path from the DB_PATH env var.

    Read on every call rather than at import time so tests can repoint it.
    """
    return Path(os.getenv("DB_PATH") or DEFAULT_DB_PATH)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a connection with row access by name. Rolls back on error, always closes.

    Does not commit: callers that write either commit themselves or go through
    use_connection().
    """
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # concurrent readers while a write is in flight
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def use_connection(conn: sqlite3.Connection | None) -> Iterator[sqlite3.Connection]:
    """Yield the connection a mutating function should write through.

    Given a connection, the caller owns the transaction and we must not commit —
    this is what keeps multi-table writes such as trade execution atomic.
    Given None, we open our own connection and commit before closing it.
    """
    if conn is not None:
        yield conn
    else:
        with get_connection() as own:
            yield own
            own.commit()
