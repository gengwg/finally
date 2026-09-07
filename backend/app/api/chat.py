"""Chat routes. Wraps the LLM layer and keeps the price feed in step with its edits."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.api.deps import CacheDep, SourceDep
from app.db import get_position, list_chat_messages
from app.llm.chat import handle_message
from app.llm.client import LLMError
from app.market import MarketDataSource

MAX_HISTORY_LIMIT = 500

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("")
def chat(body: ChatRequest, cache: CacheDep, source: SourceDep, tasks: BackgroundTasks) -> dict:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        payload = handle_message(cache, message)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if source:
        _sync_source(payload["watchlist_changes"], source, tasks)

    return payload


@router.get("/history")
def history(limit: int = 50) -> dict:
    limit = max(1, min(limit, MAX_HISTORY_LIMIT))
    return {"messages": [message.to_dict() for message in list_chat_messages(limit=limit)]}


def _sync_source(changes: list[dict], source: MarketDataSource, tasks: BackgroundTasks) -> None:
    """Start or stop streaming for the tickers the assistant just added or removed.

    Same mechanism as the watchlist routes: these are coroutines and the route is
    sync, so they are handed back to the event loop once the response is built.
    """
    for change in changes:
        if change["status"] != "executed":
            continue
        if change["action"] == "add":
            tasks.add_task(source.add_ticker, change["ticker"])
        elif get_position(change["ticker"]) is None:
            # Keep pricing what we own, even once it is off the watchlist.
            tasks.add_task(source.remove_ticker, change["ticker"])
