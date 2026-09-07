"""Watchlist routes. Keeps the DB watchlist and the market data source in step."""

from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.api.deps import CacheDep, SourceDep
from app.db import add_to_watchlist, get_position, list_watchlist, remove_from_watchlist
from app.market import PriceCache

TICKER_RE = re.compile(r"^[A-Z]{1,5}$")

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistRequest(BaseModel):
    ticker: str


@router.get("")
def read_watchlist(cache: CacheDep) -> dict:
    return _payload(cache)


@router.post("", status_code=201)
def add(body: WatchlistRequest, cache: CacheDep, source: SourceDep, tasks: BackgroundTasks) -> dict:
    ticker = body.ticker.strip().upper()
    if not TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail=f"Invalid ticker '{body.ticker}'")

    if not add_to_watchlist(ticker):
        raise HTTPException(status_code=409, detail=f"{ticker} is already on the watchlist")

    if source:
        # Sync routes run in a threadpool; the source's coroutines belong to the
        # event loop, so hand them back to it once the response is built.
        tasks.add_task(source.add_ticker, ticker)

    return _payload(cache)


@router.delete("/{ticker}")
def remove(ticker: str, cache: CacheDep, source: SourceDep, tasks: BackgroundTasks) -> dict:
    ticker = ticker.strip().upper()
    if not remove_from_watchlist(ticker):
        raise HTTPException(status_code=404, detail=f"{ticker} is not on the watchlist")

    # Keep pricing what we own, even once it is off the watchlist.
    if source and get_position(ticker) is None:
        tasks.add_task(source.remove_ticker, ticker)

    return _payload(cache)


def _payload(cache: PriceCache) -> dict:
    tickers = []
    for entry in list_watchlist():
        update = cache.get(entry.ticker)
        tickers.append(
            {
                "ticker": entry.ticker,
                "added_at": entry.added_at,
                "price": update.price if update else None,
                "previous_price": update.previous_price if update else None,
                "change": update.change if update else None,
                "change_percent": update.change_percent if update else None,
                "direction": update.direction if update else None,
            }
        )
    return {"tickers": tickers}
