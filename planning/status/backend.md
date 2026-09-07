# Backend API — done

Service layer, HTTP routes and app wiring. 72 new tests
(`backend/tests/services/` 28, `backend/tests/api/` 44); full suite 248 passing,
`ruff check app tests` clean.

## Files

| File | What |
|---|---|
| `app/services/portfolio.py` | `PositionView`, `PortfolioView`, `TradeError`, `get_portfolio`, `execute_trade`, `record_current_snapshot` |
| `app/api/deps.py` | `CacheDep`, `SourceDep` — typed access to `app.state` |
| `app/api/health.py` | `GET /api/health` |
| `app/api/portfolio.py` | `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history` |
| `app/api/watchlist.py` | `GET`/`POST /api/watchlist`, `DELETE /api/watchlist/{ticker}` |
| `app/main.py` | `create_app()`, lifespan, snapshot loop, static frontend mount |
| `app/market/stream.py` | router now built inside `create_stream_router()` (was module level) |

All routes are sync `def` and match CONTRACTS.md §3 exactly. `TradeError` → `400`,
duplicate watchlist ticker → `409`, unknown ticker on delete → `404`, bad symbol → `400`.

## Running it

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
uv run --extra dev pytest -q
uv run --extra dev ruff check app tests
```

Env: `DB_PATH` (default `db/finally.db`), `STATIC_DIR` (default `static`),
`MASSIVE_API_KEY`. `app/main.py` loads the project-root `.env` at import.

## For the LLM Engineer

```python
from app.services.portfolio import TradeError, execute_trade, get_portfolio

trade, portfolio = execute_trade(cache, "AAPL", "buy", 10)   # raises TradeError
body = get_portfolio(cache).to_dict()                        # the "portfolio" key
```

`execute_trade` already records the snapshot and adds a bought ticker to the watchlist,
so `handle_message` only has to catch `TradeError` per instruction and carry on.

Register your router by adding one line in `create_app()`:

```python
from app.api import chat          # next to the other app.api imports
app.include_router(chat.router)   # anywhere before _mount_frontend(app)
```

Give it `prefix="/api/chat"` and reach the cache with `app/api/deps.py`:

```python
from app.api.deps import CacheDep

@router.post("")
def chat(body: ChatRequest, cache: CacheDep) -> dict: ...
```

`app.state.price_cache` is created in `create_app()` (not in the lifespan), so tests can
seed it before startup. `app.state.market_source` is set by the lifespan and is `None`
before startup — use `SourceDep` and skip the call when it is `None`.

## Interpretations of the contract

1. **Positions with no cached price** are valued at `avg_cost`: `current_price = avg_cost`,
   so P&L is `0.0` and the position keeps its cost basis as market value instead of
   dropping to zero. Happens only in the seconds between a buy and the next feed tick.
2. **`app` is built by a `create_app()` factory**, with `app = create_app()` at the bottom
   for `uvicorn app.main:app`. Needed so tests can build a fresh app per test rather than
   re-running the lifespan on a shared singleton.
3. **Source lifecycle calls from sync routes** go through FastAPI `BackgroundTasks`:
   `add_ticker` / `remove_ticker` are coroutines and a sync route runs in a threadpool,
   so they are handed back to the event loop once the response is built. Consequence: the
   `201` body from `POST /api/watchlist` still has `null` prices for the new ticker — the
   contract already allows that, and the next SSE frame carries the price.
4. **`history?limit=` is clamped** to 1–5000 rather than returning `422`, since the contract
   says "defaults to 500, max 5000". `list_snapshots(limit=n)` returns the newest `n`
   snapshots in chronological order (the data layer's documented behaviour).
5. **Static mount** is `StaticFiles(html=True)` subclassed to fall back to `index.html` on a
   404, except under `/api/`, so a mistyped API path stays a JSON 404 instead of returning
   the SPA shell.
6. **`GET /api/portfolio`** is registered as `@router.get("")` under `prefix="/api/portfolio"`,
   so the path is `/api/portfolio` with no trailing slash, as the contract shows.
