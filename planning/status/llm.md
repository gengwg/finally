# LLM Engineer — done

`backend/app/llm/` and `backend/app/api/chat.py`. 113 tests in `backend/tests/llm/`;
full suite 299 passing, `ruff check app tests` clean.

## Files

| File | What |
|---|---|
| `app/llm/schema.py` | `TradeInstruction`, `WatchlistChange`, `AssistantReply` — the structured-output target. Tickers stripped and upper-cased by a validator |
| `app/llm/prompt.py` | `SYSTEM_PROMPT`, `render_portfolio_context(portfolio: dict, watchlist: list[dict]) -> str` |
| `app/llm/client.py` | `complete(messages) -> AssistantReply`, `LLMError`, `mock_enabled()` |
| `app/llm/mock.py` | the `LLM_MOCK=true` replies |
| `app/llm/chat.py` | `handle_message(cache, user_message, *, user_id)` — the full turn |
| `app/api/chat.py` | `POST /api/chat`, `GET /api/chat/history` |
| `app/llm/README.md` | mock rules in full, plus a manual smoke test that needs an API key |

Model config per the `cerebras` skill: `openrouter/openai/gpt-oss-120b`,
`extra_body={"provider": {"order": ["cerebras"]}}`, `reasoning_effort="low"`,
`response_format=AssistantReply`. No retries beyond LiteLLM's own.

`app/main.py`: added `chat` to the `app.api` import and one `app.include_router(chat.router)`
line in `create_app()`. Nothing else in that file was touched.

## The turn

1. `get_portfolio(cache)` plus the watchlist with live prices render the context block.
2. The prompt is system prompt, context, the last 20 stored messages, then the new message.
3. `complete()` — `LLMError` propagates and the route turns it into a `502`.
4. Every trade goes through `services.portfolio.execute_trade`; a `TradeError` becomes
   `status: "failed"` with the message in `error`, and the remaining actions still run.
5. Watchlist changes go through `add_to_watchlist` / `remove_from_watchlist`; a no-op
   (already there, or absent) is a `failed` action, not an exception.
6. User then assistant message persisted, with the executed actions on the assistant row.
7. The body carries a fresh `get_portfolio(...).to_dict()`, so it is post-execution.

The route mirrors executed watchlist changes onto `app.state.market_source` through
`BackgroundTasks`, exactly like `app/api/watchlist.py`, and keeps streaming a removed
ticker while there is still an open position in it.

## Mock rules (Integration Tester — assert against these)

Keyword match on the **last user message**, first match wins:

| contains (case-insensitive) | message | actions |
|---|---|---|
| `buy` | `Buying {qty} {TICKER} at market.` | one buy `{TICKER}` × `{qty}` |
| `sell` | `Selling {qty} {TICKER} at market.` | one sell `{TICKER}` × `{qty}` |
| `watch` or `add` | `Added {TICKER} to your watchlist.` | watchlist add `{TICKER}` |
| anything else | `Your portfolio looks balanced. No action taken.` | none |

`{TICKER}` = first all-upper-case 1–5 letter word, ignoring `I` and `A`, default `AAPL`
(a lower-case ticker is **not** detected — use upper case in E2E messages). `{qty}` = first
number in the message, default `1`, no trailing zeros. So `"buy 10 AAPL"` →
`Buying 10 AAPL at market.` + buy 10 AAPL, filled at the cached price.

## Interpretations of the contract

1. **`render_portfolio_context(portfolio, watchlist)`** takes plain dicts — a
   `PortfolioView.to_dict()` and the `GET /api/watchlist` ticker list — so the prompt layer
   needs no service imports and is testable on its own.
2. **Mock branch precedence is buy > sell > watch/add.** The contract lists the branches but
   not an order, and one message can contain several keywords.
3. **`LLM_MOCK` counts as on only for the literal `"true"`** (trimmed, case-insensitive).
4. **`client.py` uses `import litellm` and calls `litellm.completion(...)`** rather than the
   skill's `from litellm import completion`. Same call; it leaves the boundary patchable.
5. **An empty or whitespace-only `message` is a `400`.** The contract does not cover it.
6. **`actions` on an assistant message is always the object**, with empty lists when nothing
   ran, rather than `null`. One shape for the frontend to render. User rows stay `null`.
   Each action object is stored verbatim — `status`, `error` and the fill `price` included —
   so a reloaded conversation renders the same chips as the live one
   (`test_actions_survive_the_db_round_trip_verbatim`).
7. **Nothing is persisted when the model call fails** — no orphan user message, so the next
   prompt does not replay a turn that never happened.
8. **`history?limit=` is clamped to 1–500** (the contract gives a default of 50 but no max),
   matching how `/api/portfolio/history` clamps.
9. **A buy of an unwatched ticker needs no feed change**: `execute_trade` requires a cached
   price, so the source is already tracking it. Only explicit watchlist adds start a feed.
