"""FastAPI application: API routes, market data wiring, static frontend."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.api import chat, health, portfolio, watchlist
from app.db import init_db, list_watchlist
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.services.portfolio import record_current_snapshot

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_INTERVAL_SECONDS = 30

load_dotenv(PROJECT_ROOT / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise the database, start the price feed and the snapshot recorder."""
    init_db()

    source = create_market_data_source(app.state.price_cache)
    await source.start([entry.ticker for entry in list_watchlist()])
    app.state.market_source = source

    snapshots = asyncio.create_task(_snapshot_loop(app), name="portfolio-snapshots")
    try:
        yield
    finally:
        snapshots.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await snapshots
        await source.stop()
        app.state.market_source = None


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", version="0.1.0", lifespan=lifespan)
    app.state.price_cache = PriceCache()
    app.state.market_source = None

    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(chat.router)
    app.include_router(create_stream_router(app.state.price_cache))

    _mount_frontend(app)
    return app


async def _snapshot_loop(app: FastAPI) -> None:
    """Record total portfolio value every 30s so the P&L chart has history."""
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(record_current_snapshot, app.state.price_cache)
        except Exception:
            logger.exception("Portfolio snapshot failed")


class _SinglePageFiles(StaticFiles):
    """Static files with an index.html fallback, for client-side routing."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise


def _mount_frontend(app: FastAPI) -> None:
    """Serve the exported frontend at /, after every API route.

    Skipped when the export is missing so backend-only dev and tests still work.
    """
    static_dir = Path(os.environ.get("STATIC_DIR", "static"))
    if not static_dir.is_dir():
        logger.info("No static directory at %s - serving the API only", static_dir)
        return

    app.mount("/", _SinglePageFiles(directory=static_dir, html=True), name="frontend")


app = create_app()
