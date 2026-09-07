"""Deterministic replies for LLM_MOCK=true. Rules are documented in README.md."""

from __future__ import annotations

import re

from .schema import AssistantReply, TradeInstruction, WatchlistChange

DEFAULT_TICKER = "AAPL"
DEFAULT_QUANTITY = 1.0
ANALYSIS_MESSAGE = "Your portfolio looks balanced. No action taken."

_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
_QUANTITY_RE = re.compile(r"\d+(?:\.\d+)?")

# "I" and "A" are English words, not tickers. Single-letter tickers (V, F, T) are real,
# so we cannot just require two characters.
_NOT_TICKERS = {"I", "A"}


def _last_user_message(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content") or ""
    return ""


def _extract_ticker(text: str) -> str:
    for candidate in _TICKER_RE.findall(text):
        if candidate not in _NOT_TICKERS:
            return candidate
    return DEFAULT_TICKER


def _extract_quantity(text: str) -> float:
    match = _QUANTITY_RE.search(text)
    return float(match.group()) if match else DEFAULT_QUANTITY


def mock_complete(messages: list[dict]) -> AssistantReply:
    """Keyword-matched reply to the last user message. No network calls."""
    text = _last_user_message(messages)
    lowered = text.lower()
    ticker = _extract_ticker(text)

    if "buy" in lowered:
        quantity = _extract_quantity(text)
        return AssistantReply(
            message=f"Buying {quantity:g} {ticker} at market.",
            trades=[TradeInstruction(ticker=ticker, side="buy", quantity=quantity)],
        )

    if "sell" in lowered:
        quantity = _extract_quantity(text)
        return AssistantReply(
            message=f"Selling {quantity:g} {ticker} at market.",
            trades=[TradeInstruction(ticker=ticker, side="sell", quantity=quantity)],
        )

    if "watch" in lowered or "add" in lowered:
        return AssistantReply(
            message=f"Added {ticker} to your watchlist.",
            watchlist_changes=[WatchlistChange(ticker=ticker, action="add")],
        )

    return AssistantReply(message=ANALYSIS_MESSAGE)
