"""Portfolio, trading and value history routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CacheDep
from app.db import list_snapshots
from app.services.portfolio import TradeError, execute_trade, get_portfolio

MAX_HISTORY_LIMIT = 5000

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str


@router.get("")
def read_portfolio(cache: CacheDep) -> dict:
    return get_portfolio(cache).to_dict()


@router.post("/trade")
def trade(body: TradeRequest, cache: CacheDep) -> dict:
    try:
        executed, portfolio = execute_trade(cache, body.ticker, body.side, body.quantity)
    except TradeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"trade": executed.to_dict(), "portfolio": portfolio.to_dict()}


@router.get("/history")
def history(limit: int = 500) -> dict:
    limit = max(1, min(limit, MAX_HISTORY_LIMIT))
    return {"snapshots": [snapshot.to_dict() for snapshot in list_snapshots(limit=limit)]}
