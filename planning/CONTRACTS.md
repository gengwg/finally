# FinAlly — Interface Contracts

This is the binding contract between team members. It exists so every engineer can
build in parallel against fixed interfaces. **Do not change a signature or JSON shape
here without telling the Tech Lead** — someone else is already coding against it.

Read `PLAN.md` for the product spec and `MARKET_DATA_SUMMARY.md` for the market data
subsystem (already complete).

## Conventions

- JSON is **snake_case** everywhere, backend and frontend.
- Money and quantities are plain JSON numbers (floats). Fractional shares allowed.
- Timestamps in the DB and in JSON are **ISO 8601 strings** (`datetime.now(UTC).isoformat()`),
  except `PriceUpdate.timestamp`, which is a Unix float (existing market data code).
- `user_id` is always `"default"`. Every DB function takes it as a keyword arg with
  that default. No auth, no sessions.
- All new FastAPI routes are **sync `def`** (not `async def`) so blocking SQLite and
  LiteLLM calls run in the threadpool. The SSE endpoint stays async.
- Errors use FastAPI `HTTPException`, so the body is `{"detail": "message"}`.

---

## 1. Database layer — `backend/app/db/` (Database Engineer)

Public API, importable as `from app.db import ...`:

```python
DEFAULT_USER_ID = "default"

init_db() -> None                    # idempotent: create schema + seed if empty
get_connection() -> ContextManager[sqlite3.Connection]   # row_factory = sqlite3.Row
```

`init_db()` is called once on app startup (Backend API Engineer wires it). The DB path
comes from env var `DB_PATH`, defaulting to `db/finally.db`, and parent dirs are created
if missing. Tests point `DB_PATH` at a tmp file.

### Row models — `app/db/models.py`

Plain frozen dataclasses with a `to_dict()` returning exactly the JSON field names below.

```python
Position(ticker: str, quantity: float, avg_cost: float, updated_at: str)
Trade(id: str, ticker: str, side: str, quantity: float, price: float, executed_at: str)
Snapshot(total_value: float, recorded_at: str)
ChatMessage(id: str, role: str, content: str, actions: dict | None, created_at: str)
WatchlistEntry(ticker: str, added_at: str)
```

### Functions

Every **mutating** function takes an optional `conn` keyword. When `conn` is passed the
function uses it and does **not** commit (caller owns the transaction, and must call
`conn.commit()` itself); when omitted it opens its own connection and commits. This is how
trade execution stays atomic. `get_connection()` rolls back on an exception in the block.

```python
# profile
get_cash_balance(*, user_id=DEFAULT_USER_ID) -> float
set_cash_balance(amount: float, *, user_id=DEFAULT_USER_ID, conn=None) -> None

# watchlist
list_watchlist(*, user_id=DEFAULT_USER_ID) -> list[WatchlistEntry]   # oldest first
add_to_watchlist(ticker: str, *, user_id=DEFAULT_USER_ID, conn=None) -> bool  # False if already there
remove_from_watchlist(ticker: str, *, user_id=DEFAULT_USER_ID, conn=None) -> bool  # False if absent

# positions
list_positions(*, user_id=DEFAULT_USER_ID) -> list[Position]         # ticker order
get_position(ticker: str, *, user_id=DEFAULT_USER_ID) -> Position | None
upsert_position(ticker: str, quantity: float, avg_cost: float, *, user_id=DEFAULT_USER_ID, conn=None) -> None
delete_position(ticker: str, *, user_id=DEFAULT_USER_ID, conn=None) -> None

# trades
record_trade(ticker: str, side: str, quantity: float, price: float, *, user_id=DEFAULT_USER_ID, conn=None) -> Trade
list_trades(*, limit=100, user_id=DEFAULT_USER_ID) -> list[Trade]    # newest first

# snapshots
record_snapshot(total_value: float, *, user_id=DEFAULT_USER_ID, conn=None) -> Snapshot
list_snapshots(*, limit=500, user_id=DEFAULT_USER_ID) -> list[Snapshot]  # oldest first

# chat
add_chat_message(role: str, content: str, actions: dict | None = None, *, user_id=DEFAULT_USER_ID, conn=None) -> ChatMessage
list_chat_messages(*, limit=50, user_id=DEFAULT_USER_ID) -> list[ChatMessage]  # oldest first
```

Tickers are normalised to upper case on write and on lookup. `actions` is stored as a
JSON string in the `actions` TEXT column and returned as a parsed dict (or `None`).

Schema and seed data are exactly as specified in `PLAN.md` §7.

---

## 2. Service layer — `backend/app/services/` (Backend API Engineer)

```python
# app/services/portfolio.py
@dataclass(frozen=True)
class PositionView:
    ticker: str; quantity: float; avg_cost: float; current_price: float
    market_value: float; unrealized_pnl: float; pnl_percent: float
    def to_dict(self) -> dict: ...

@dataclass(frozen=True)
class PortfolioView:
    cash_balance: float; positions: list[PositionView]
    positions_value: float; total_value: float; total_unrealized_pnl: float
    def to_dict(self) -> dict: ...

class TradeError(Exception):
    """Validation failure — insufficient cash, insufficient shares, unknown ticker."""

def get_portfolio(cache: PriceCache, *, user_id="default") -> PortfolioView
def execute_trade(cache: PriceCache, ticker: str, side: str, quantity: float, *, user_id="default") -> tuple[Trade, PortfolioView]
def record_current_snapshot(cache: PriceCache, *, user_id="default") -> Snapshot
```

`execute_trade` rules:

- `quantity` must be `> 0`, `side` must be `"buy"` or `"sell"` → else `TradeError`.
- Price comes from `cache.get_price(ticker)`; `None` → `TradeError` (unknown/untracked ticker).
- Buy: cost = `price * quantity`; `cost > cash_balance` → `TradeError`. New `avg_cost` is
  the weighted average of old and new lots. Cash decreases.
- Sell: `quantity > position.quantity` → `TradeError`. `avg_cost` is unchanged.
  Position row is deleted when the remaining quantity is `<= 1e-9`. Cash increases.
- Positions, cash and the trade row are written in **one transaction** (shared `conn`).
- A portfolio snapshot is recorded immediately after each successful trade.
- If the ticker is not on the watchlist, a buy adds it (so the user can see what they own).

`unrealized_pnl = (current_price - avg_cost) * quantity`,
`pnl_percent = (current_price / avg_cost - 1) * 100` (0.0 when `avg_cost == 0`).
Round money to 2 dp and percentages to 2 dp in `to_dict()` only — keep full precision internally.

---

## 3. HTTP API (Backend API Engineer, except `/api/chat*` → LLM Engineer)

App instance: `app.main:app`. Startup wires: `init_db()`, a single `PriceCache`, a market
data source started with the watchlist tickers, the SSE router, and a 30-second snapshot
background task. Shutdown stops both.

`app.state.price_cache` holds the cache so routes and tests can reach it.

### `GET /api/health`
```json
{"status": "ok"}
```

### `GET /api/portfolio`
```json
{
  "cash_balance": 8080.0,
  "positions": [
    {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 192.0, "current_price": 193.5,
     "market_value": 1935.0, "unrealized_pnl": 15.0, "pnl_percent": 0.78}
  ],
  "positions_value": 1935.0,
  "total_value": 10015.0,
  "total_unrealized_pnl": 15.0
}
```

### `POST /api/portfolio/trade`
Request: `{"ticker": "AAPL", "quantity": 10, "side": "buy"}`
Response `200`:
```json
{
  "trade": {"id": "uuid", "ticker": "AAPL", "side": "buy", "quantity": 10.0,
            "price": 192.0, "executed_at": "2026-09-07T12:00:00+00:00"},
  "portfolio": { ... same shape as GET /api/portfolio ... }
}
```
`400` with `{"detail": "..."}` on any `TradeError`.

### `GET /api/portfolio/history?limit=500`
```json
{"snapshots": [{"total_value": 10000.0, "recorded_at": "2026-09-07T12:00:00+00:00"}]}
```
Oldest first. `limit` defaults to 500, max 5000.

### `GET /api/watchlist`
```json
{"tickers": [
  {"ticker": "AAPL", "added_at": "2026-09-07T12:00:00+00:00", "price": 193.5,
   "previous_price": 193.4, "change": 0.1, "change_percent": 0.05, "direction": "up"}
]}
```
Price fields are `null` when the cache has no price for that ticker yet.

### `POST /api/watchlist`
Request: `{"ticker": "pypl"}` → normalised to `PYPL`. Also calls
`source.add_ticker(...)` so prices start streaming.
Response `201`: the same `{"tickers": [...]}` body as `GET`.
`409` if already present, `400` if the ticker is empty or not 1–5 A–Z characters.

### `DELETE /api/watchlist/{ticker}`
Removes from the watchlist and calls `source.remove_ticker(...)` **only if** there is no
open position in that ticker (we must keep pricing what we own).
Response `200`: `{"tickers": [...]}`. `404` if not on the watchlist.

### `GET /api/stream/prices`
Already implemented — SSE, one `data:` frame with **all** tickers keyed by symbol, pushed
on change at ~500ms:
```
data: {"AAPL": {"ticker":"AAPL","price":193.5,"previous_price":193.4,"timestamp":1757246400.0,"change":0.1,"change_percent":0.05,"direction":"up"}, ...}
```
The frontend accumulates its own price history from this stream for sparklines and the
detail chart, and computes session change % against the first price it observed.

### `POST /api/chat` (LLM Engineer)
Request: `{"message": "buy me 10 apple shares"}`
Response `200`:
```json
{
  "message": "Bought 10 AAPL at $192.00. That's 19% of your portfolio.",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10.0, "status": "executed",
              "price": 192.0, "error": null}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add", "status": "executed", "error": null}],
  "portfolio": { ... same shape as GET /api/portfolio ... }
}
```
`status` is `"executed"` or `"failed"`; `error` carries the failure message and is `null`
on success. `502` with `{"detail": "..."}` if the LLM call itself fails.

### `GET /api/chat/history?limit=50` (LLM Engineer)
```json
{"messages": [{"id": "uuid", "role": "user", "content": "...", "actions": null,
               "created_at": "2026-09-07T12:00:00+00:00"}]}
```
Oldest first. `actions` on assistant messages is `{"trades": [...], "watchlist_changes": [...]}`
holding the executed action objects **verbatim** — each one keeps its `status`, `error` and
(for trades) the fill `price`, exactly as it appeared in the `POST /api/chat` response. A
reloaded conversation must therefore show the same inline confirmations, successes and
failures alike, as the live one did.

### Static files
`app.main` mounts the frontend export last, after all `/api/*` routes: `/` serves
`static/index.html` and unknown non-API paths fall back to it. The static dir is
`STATIC_DIR` env var, default `static`, and the mount is skipped when the directory is
absent (so backend-only dev and tests still work).

---

## 4. LLM layer — `backend/app/llm/` (LLM Engineer)

```python
# app/llm/schema.py — pydantic models used as the structured output target
class TradeInstruction(BaseModel): ticker: str; side: Literal["buy","sell"]; quantity: float
class WatchlistChange(BaseModel): ticker: str; action: Literal["add","remove"]
class AssistantReply(BaseModel):
    message: str
    trades: list[TradeInstruction] = []
    watchlist_changes: list[WatchlistChange] = []

# app/llm/client.py
def complete(messages: list[dict]) -> AssistantReply
    """LiteLLM -> OpenRouter -> Cerebras with structured outputs.
    Returns a mock reply when LLM_MOCK=true. Raises LLMError on failure."""

# app/llm/chat.py
def handle_message(cache: PriceCache, user_message: str, *, user_id="default") -> dict
    """Full flow: build context, call the LLM, execute actions, persist, return the
    POST /api/chat response body."""
```

- Model config exactly as the `cerebras-inference` skill says:
  `MODEL = "openrouter/openai/gpt-oss-120b"`, `extra_body={"provider": {"order": ["cerebras"]}}`,
  `reasoning_effort="low"`, `response_format=AssistantReply`.
- Trades from the LLM go through `services.portfolio.execute_trade` — same validation as
  manual trades. A `TradeError` becomes `status: "failed"` with the message in `error`,
  and the remaining actions still run.
- `LLM_MOCK=true` returns deterministic replies driven by simple keyword matching on the
  user message, so E2E tests can assert on them. Document the mock rules in
  `backend/app/llm/README.md` (short) — the Integration Tester writes assertions against it.
  At minimum: a message containing "buy" produces one buy trade, "sell" a sell trade,
  "watch"/"add" a watchlist add, anything else a plain analysis message with no actions.

---

## 5. Frontend — `frontend/` (Frontend Engineer)

Next.js + TypeScript + Tailwind, `output: 'export'`, `trailingSlash: true`, no image
optimisation. Build output goes to `frontend/out/`; the Dockerfile copies it to
`backend/static/`. For local dev, `next dev` proxies nothing — point it at the backend
with `NEXT_PUBLIC_API_BASE` (empty string in production, `http://localhost:8000` in dev).

Types mirroring the JSON above live in `frontend/src/lib/types.ts`, API calls in
`frontend/src/lib/api.ts`, the SSE hook in `frontend/src/hooks/usePrices.ts`. Everything
else is the Frontend Engineer's call. UI elements required: see `PLAN.md` §10.

E2E hooks the Integration Tester depends on — these `data-testid` attributes are part of
the contract:

| testid | element |
|---|---|
| `connection-status` | header SSE status dot, with `data-state="connected\|reconnecting\|disconnected"` |
| `cash-balance` | header cash figure |
| `total-value` | header portfolio total |
| `watchlist` | watchlist container |
| `watchlist-row-{TICKER}` | one watchlist row |
| `watchlist-price-{TICKER}` | the price cell inside that row |
| `watchlist-add-input` / `watchlist-add-submit` | add-ticker form |
| `watchlist-remove-{TICKER}` | remove button |
| `main-chart` | detail chart container, with `data-ticker="{TICKER}"` |
| `positions-table` | positions table |
| `position-row-{TICKER}` | one position row |
| `heatmap` | portfolio treemap container |
| `heatmap-tile-{TICKER}` | one treemap tile, with `data-pnl="profit|loss|flat"` |
| `pnl-chart` | portfolio value chart container |
| `trade-ticker` / `trade-quantity` / `trade-buy` / `trade-sell` | trade bar |
| `trade-error` | trade error message (present only on error) |
| `chat-panel` / `chat-input` / `chat-send` / `chat-loading` | chat panel |
| `chat-message-{n}` | nth chat message, with `data-role="user\|assistant"` |

---

## 6. Docker & scripts (DevOps Engineer)

Multi-stage build per `PLAN.md` §11, with one amendment: the build stage is `node:22-slim`,
not Node 20 — current Next.js needs Node 20+ and 22 is the active LTS. Node builds `frontend/` → copy `out/` into the
Python image at `/app/static`. `uv sync --frozen --no-dev` for deps. Runtime cwd `/app`,
DB at `/app/db/finally.db` (`DB_PATH=/app/db/finally.db`), `STATIC_DIR=/app/static`,
`CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`. Healthcheck hits `/api/health`.

`scripts/start_mac.sh`, `stop_mac.sh`, `start_windows.ps1`, `stop_windows.ps1` — idempotent,
container name `finally`, volume `finally-data`, `--env-file .env`.

---

## 7. E2E tests (Integration Tester)

`test/` holds the Playwright project and `docker-compose.test.yml`. Tests run against the
built container with `LLM_MOCK=true` and a fresh DB. Scenarios: `PLAN.md` §12.
