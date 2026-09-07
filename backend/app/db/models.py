"""Row models for the FinAlly database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string, the storage format for all timestamps."""
    return datetime.now(UTC).isoformat()


def normalise_ticker(ticker: str) -> str:
    """Canonical ticker form: upper case, no surrounding whitespace."""
    return ticker.strip().upper()


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    """A ticker the user is watching."""

    ticker: str
    added_at: str

    def to_dict(self) -> dict:
        return {"ticker": self.ticker, "added_at": self.added_at}


@dataclass(frozen=True, slots=True)
class Position:
    """An open holding in one ticker."""

    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class Trade:
    """One executed trade from the append-only trade log."""

    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "executed_at": self.executed_at,
        }


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Total portfolio value at a point in time."""

    total_value: float
    recorded_at: str

    def to_dict(self) -> dict:
        return {"total_value": self.total_value, "recorded_at": self.recorded_at}


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One message in the conversation with the assistant."""

    id: str
    role: str
    content: str
    actions: dict | None
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "actions": self.actions,
            "created_at": self.created_at,
        }
