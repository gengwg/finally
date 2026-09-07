"""Chat message history."""

from __future__ import annotations

import json
import sqlite3
import uuid

from .connection import get_connection, use_connection
from .models import ChatMessage, now_iso
from .profile import DEFAULT_USER_ID


def add_chat_message(
    role: str,
    content: str,
    actions: dict | None = None,
    *,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> ChatMessage:
    """Append a message. `actions` is stored as JSON and read back as a dict."""
    message = ChatMessage(
        id=str(uuid.uuid4()),
        role=role,
        content=content,
        actions=actions,
        created_at=now_iso(),
    )
    with use_connection(conn) as db:
        db.execute(
            """
            INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                user_id,
                message.role,
                message.content,
                json.dumps(actions) if actions is not None else None,
                message.created_at,
            ),
        )
    return message


def list_chat_messages(*, limit: int = 50, user_id: str = DEFAULT_USER_ID) -> list[ChatMessage]:
    """The newest `limit` messages, returned oldest first for prompt and UI order."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, actions, created_at FROM (
                SELECT id, role, content, actions, created_at, rowid FROM chat_messages
                WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?
            ) ORDER BY created_at, rowid
            """,
            (user_id, limit),
        ).fetchall()
    return [
        ChatMessage(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            actions=json.loads(r["actions"]) if r["actions"] else None,
            created_at=r["created_at"],
        )
        for r in rows
    ]
