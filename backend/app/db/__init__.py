"""SQLite data layer for FinAlly.

Everything downstream imports from here:

    from app.db import init_db, get_connection, get_cash_balance

`init_db()` is called once on app startup and is idempotent. Every mutating
function takes an optional `conn` keyword: pass one to join the caller's
transaction (nothing is committed), omit it to write and commit standalone.
"""

from .chat import add_chat_message, list_chat_messages
from .connection import get_connection
from .init import init_db
from .models import ChatMessage, Position, Snapshot, Trade, WatchlistEntry
from .positions import delete_position, get_position, list_positions, upsert_position
from .profile import DEFAULT_USER_ID, get_cash_balance, set_cash_balance
from .snapshots import list_snapshots, record_snapshot
from .trades import list_trades, record_trade
from .watchlist import add_to_watchlist, list_watchlist, remove_from_watchlist

__all__ = [
    "DEFAULT_USER_ID",
    "ChatMessage",
    "Position",
    "Snapshot",
    "Trade",
    "WatchlistEntry",
    "add_chat_message",
    "add_to_watchlist",
    "delete_position",
    "get_cash_balance",
    "get_connection",
    "get_position",
    "init_db",
    "list_chat_messages",
    "list_positions",
    "list_snapshots",
    "list_trades",
    "list_watchlist",
    "record_snapshot",
    "record_trade",
    "remove_from_watchlist",
    "set_cash_balance",
    "upsert_position",
]
