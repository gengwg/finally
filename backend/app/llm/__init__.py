"""LLM layer: structured-output chat assistant for FinAlly."""

from __future__ import annotations

from .client import LLMError, complete
from .schema import AssistantReply, TradeInstruction, WatchlistChange

__all__ = [
    "AssistantReply",
    "LLMError",
    "TradeInstruction",
    "WatchlistChange",
    "complete",
]
