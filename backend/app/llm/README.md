# LLM layer

`complete(messages) -> AssistantReply` calls `openrouter/openai/gpt-oss-120b` through
LiteLLM with `provider.order = ["cerebras"]`, `reasoning_effort="low"` and
`response_format=AssistantReply` (structured outputs). Failures — network, API, empty
body, or a response that does not parse into the schema — raise `LLMError`.

- `schema.py` — `TradeInstruction`, `WatchlistChange`, `AssistantReply`. Tickers are
  upper-cased by a validator.
- `prompt.py` — `SYSTEM_PROMPT` and `render_portfolio_context(portfolio, watchlist)`,
  which takes a `PortfolioView.to_dict()` and the `GET /api/watchlist` ticker list.
- `client.py` — the LiteLLM call. `LLM_MOCK` is read on every call, not at import.
- `mock.py` — the mock replies below.
- `chat.py` — `handle_message(cache, user_message)` runs one turn: build the prompt from
  the live portfolio and the last 20 stored messages, call the model, execute every trade
  and watchlist change, persist both sides of the turn, return the `POST /api/chat` body.

`app/api/chat.py` wraps it: `LLMError` becomes a `502`, an empty message a `400`, and a
watchlist add or remove is mirrored onto the market data source via `BackgroundTasks`.

A trade or watchlist change that fails validation does not stop the rest. Each action
carries `"status": "executed" | "failed"` and an `error` string that is `null` on success,
and the same list is stored as the assistant message's `actions`.

## Mock mode

With `LLM_MOCK=true`, `complete()` never touches the network. It keyword-matches the
**last user message** and returns one of four fixed replies. Checks run in this order,
first match wins:

| Message contains (case-insensitive) | Reply message | Actions |
|---|---|---|
| `buy` | `Buying {qty} {TICKER} at market.` | one buy trade for `{TICKER}` × `{qty}` |
| `sell` | `Selling {qty} {TICKER} at market.` | one sell trade for `{TICKER}` × `{qty}` |
| `watch` or `add` | `Added {TICKER} to your watchlist.` | one watchlist `add` for `{TICKER}` |
| anything else | `Your portfolio looks balanced. No action taken.` | none |

`{TICKER}` is the first all-upper-case 1–5 letter word in the message, ignoring `I` and
`A`; it defaults to `AAPL` when there is none, so a lower-case ticker is not detected.
`{qty}` is the first number in the message, defaulting to `1`, formatted without
trailing zeros (`10`, `2.5`).

Examples:

- `"buy 10 AAPL"` → `Buying 10 AAPL at market.` + buy 10 AAPL
- `"sell 2.5 TSLA now"` → `Selling 2.5 TSLA at market.` + sell 2.5 TSLA
- `"add PYPL to my watchlist"` → `Added PYPL to your watchlist.` + add PYPL
- `"how is my portfolio doing?"` → `Your portfolio looks balanced. No action taken.`
- `"buy something"` → `Buying 1 AAPL at market.` + buy 1 AAPL

## Manual smoke test

Requires a real `OPENROUTER_API_KEY` in the environment; the unit tests do not.

```bash
cd backend
uv run python -c "
from app.llm import complete
from app.llm.prompt import SYSTEM_PROMPT
print(complete([
    {'role': 'system', 'content': SYSTEM_PROMPT},
    {'role': 'user', 'content': 'buy 10 apple shares'},
]))
"
```
