"""Route access to the objects `app.main` puts on `app.state`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.market import MarketDataSource, PriceCache


def price_cache(request: Request) -> PriceCache:
    return request.app.state.price_cache


def market_source(request: Request) -> MarketDataSource | None:
    """The running data source, or None before startup has wired one up."""
    return getattr(request.app.state, "market_source", None)


CacheDep = Annotated[PriceCache, Depends(price_cache)]
SourceDep = Annotated[MarketDataSource | None, Depends(market_source)]
