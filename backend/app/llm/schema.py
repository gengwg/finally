"""Pydantic models used as the LLM structured-output target."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _normalise_ticker(value: str) -> str:
    return value.strip().upper()


class TradeInstruction(BaseModel):
    """A trade the assistant wants executed. Market order, instant fill."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float

    @field_validator("ticker")
    @classmethod
    def _upper_ticker(cls, value: str) -> str:
        return _normalise_ticker(value)


class WatchlistChange(BaseModel):
    """A watchlist edit the assistant wants applied."""

    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def _upper_ticker(cls, value: str) -> str:
        return _normalise_ticker(value)


class AssistantReply(BaseModel):
    """The complete assistant response: prose plus the actions to execute."""

    message: str
    trades: list[TradeInstruction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)
