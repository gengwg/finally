# Integration Tester — phase 2 (suite run against the container)

**21 passed, 0 failed** on a pristine database via `docker-compose.test.yml`, in 13s.
One real frontend bug was found and fixed along the way (below).

Harness bugs found and fixed during phase 2, all in `test/`:

- `page.goto` hit `ERR_SSL_PROTOCOL_ERROR` because Chrome upgrades `http://` to `https://`
  for a single-label host like `app`. The Playwright container now uses
  `network_mode: "service:app"` and `E2E_BASE_URL=http://localhost:8000`.
- `parseMoney` asserted internally and was called inside an `expect.poll` body; a throw
  there aborts the poll instead of retrying, so a price cell still showing its placeholder
  failed the test in 372ms. Split into non-throwing `toMoney`/`pollMoney` for polls and
  asserting `parseMoney` for one-shot reads.
- Retries are now 0. With one shared SQLite portfolio a retry replays mutations against
  state the first attempt already changed, which compounded 3 holdings into 6 and then 9
  and drained the cash that 05 needed.
- Each spec except 01 calls `resetState` in `beforeAll` (sell every position, drop every
  non-default watchlist ticker) instead of inheriting state from the spec before it.
- `context.setOffline(true)` does **not** sever an SSE response that is already streaming:
  probed directly, prices kept arriving and the dot stayed `connected`. `06` proxies the
  browser through a TCP proxy it owns and destroys the sockets, which is a real
  interruption. The dot leaves `connected` and native EventSource recovers on its own.
- `04` is not a serial describe, so one failing test there cannot hide the rest.
- The Playwright container runs as the host user (`user: "${E2E_UID:-1000}:${E2E_GID:-1000}"`,
  `HOME`/`npm_config_cache` under `/tmp`) and the `node_modules` volume is gone, so
  `test-results/` and `playwright-report/` are owned by whoever ran the suite.

## The bug the suite caught

`04-portfolio-visuals` failed with 3 heatmap tiles for 2 positions; the extra element was
`data-testid="heatmap-tile-"` with an empty ticker, `data-pnl="flat"` and text `0.00%`.
Recharts calls the Treemap content renderer for its synthetic root as well as the leaves.
Fixed by the Frontend Engineer with a depth guard. Their unit tests queried tiles by exact
ticker, so the extra node was invisible to them.

## Contract gaps — all resolved

1. **Mock LLM rules — resolved.** `backend/app/llm/README.md` landed while I was writing,
   so `05-chat` now asserts the mock's exact replies (`Buying 2 NVDA at market.`,
   `Selling 1 NVDA at market.`, `Added PLTR to your watchlist.`,
   `Your portfolio looks balanced. No action taken.`) and the exact ticker, quantity and
   status of each action. If those strings or the keyword order change, tell me.
2. **Chat history `actions` — resolved.** Section 3 now says chat history keeps the
   executed action objects verbatim, including `status`, `error` and the fill price, so
   `05-chat` reads them from `/api/chat/history` and the reload assertion stands.
3. **"A buy adds an unwatched ticker" — resolved, contract unchanged.** I first read the
   rule as unreachable, because an unwatched ticker has no cached price to fill against.
   The Tech Lead corrected me: DELETE only calls `source.remove_ticker` when there is no
   open position, so a ticker we hold leaves the watchlist and stays priced, and the next
   buy fills and re-adds it. `03-trading` now covers exactly that path - buy, remove via
   the API, confirm it is off the watchlist but still re-pricing, buy again, confirm the
   row is back - then sells out to leave the portfolio flat. A first-ever buy of a
   never-watched ticker really is unreachable and is not tested.
4. **Heatmap hooks — granted and implemented.** The testid table now carries
   `heatmap-tile-{TICKER}` with `data-pnl="profit|loss|flat"`, so `04` asserts one tile per
   position and polls each tile's `data-pnl` against the sign of that position's
   `unrealized_pnl` from the API. It asserts the sign, never the colour, so a palette
   change cannot break it. The P&L chart is now its own test: history is non-empty and the
   container holds a sized `canvas`/`svg`.
5. **Chat history renders on load — confirmed.** `05-chat` keeps the reload assertion.
6. **`connection-status` recovery — confirmed intended.** `06` stays strict: a frontend
   that never leaves `connected` when the stream drops fails the test, which is correct.
7. **`GET /api/trades` — declined**, not in PLAN.md section 8. `03` keeps the 10% bound on
   sale proceeds, which is the honest way to assert a value that moves between the read and
   the fill.

Also note `01-fresh-start` requires a pristine database. That is guaranteed under
`docker-compose.test.yml`; a local run against a container that has already traded will
fail it.

Waiting on the phase 2 go-ahead to run the suite.
