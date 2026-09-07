"""Chat flow: build the prompt, call the model, execute what it asked for, persist."""

from __future__ import annotations

import logging

from app.db import (
    DEFAULT_USER_ID,
    add_chat_message,
    add_to_watchlist,
    list_chat_messages,
    list_watchlist,
    remove_from_watchlist,
)
from app.market import PriceCache
from app.services.portfolio import TradeError, execute_trade, get_portfolio

from .client import complete
from .prompt import SYSTEM_PROMPT, render_portfolio_context

logger = logging.getLogger(__name__)

# How much of the conversation to replay to the model. Enough for follow-ups
# ("do it", "sell half of that") without bloating every prompt.
HISTORY_LIMIT = 20


def handle_message(cache: PriceCache, user_message: str, *, user_id: str = DEFAULT_USER_ID) -> dict:
    """Run one chat turn and return the `POST /api/chat` response body.

    Raises LLMError if the model call fails; a trade or watchlist change that fails
    validation is reported per action and does not stop the others.
    """
    reply = complete(_build_messages(cache, user_message, user_id=user_id))

    trades = [_run_trade(cache, trade, user_id) for trade in reply.trades]
    watchlist_changes = [
        _run_watchlist_change(change, user_id) for change in reply.watchlist_changes
    ]
    actions = {"trades": trades, "watchlist_changes": watchlist_changes}

    add_chat_message("user", user_message, user_id=user_id)
    add_chat_message("assistant", reply.message, actions, user_id=user_id)

    return {
        "message": reply.message,
        **actions,
        "portfolio": get_portfolio(cache, user_id=user_id).to_dict(),
    }


def _build_messages(cache: PriceCache, user_message: str, *, user_id: str) -> list[dict]:
    """System prompt, live portfolio context, recent history, then the new message."""
    context = render_portfolio_context(
        get_portfolio(cache, user_id=user_id).to_dict(),
        _watchlist_context(cache, user_id=user_id),
    )
    history = list_chat_messages(limit=HISTORY_LIMIT, user_id=user_id)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context},
        *({"role": message.role, "content": message.content} for message in history),
        {"role": "user", "content": user_message},
    ]


def _watchlist_context(cache: PriceCache, *, user_id: str) -> list[dict]:
    rows = []
    for entry in list_watchlist(user_id=user_id):
        update = cache.get(entry.ticker)
        rows.append(
            {
                "ticker": entry.ticker,
                "price": update.price if update else None,
                "change_percent": update.change_percent if update else None,
            }
        )
    return rows


def _run_trade(cache: PriceCache, instruction, user_id: str) -> dict:
    result = {
        "ticker": instruction.ticker,
        "side": instruction.side,
        "quantity": instruction.quantity,
        "status": "executed",
        "price": None,
        "error": None,
    }
    try:
        trade, _ = execute_trade(
            cache,
            instruction.ticker,
            instruction.side,
            instruction.quantity,
            user_id=user_id,
        )
    except TradeError as exc:
        logger.info("LLM trade rejected: %s", exc)
        return {**result, "status": "failed", "error": str(exc)}

    return {**result, "price": trade.price}


def _run_watchlist_change(change, user_id: str) -> dict:
    if change.action == "add":
        applied = add_to_watchlist(change.ticker, user_id=user_id)
        error = None if applied else f"{change.ticker} is already on the watchlist"
    else:
        applied = remove_from_watchlist(change.ticker, user_id=user_id)
        error = None if applied else f"{change.ticker} is not on the watchlist"

    return {
        "ticker": change.ticker,
        "action": change.action,
        "status": "executed" if applied else "failed",
        "error": error,
    }
