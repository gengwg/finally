# Frontend — status

Complete. `frontend/` is a Next.js 16 + TypeScript + Tailwind 4 static export.

## Run it

```
cd frontend
npm install          # if node_modules is missing
npm run build        # static export -> frontend/out/  (Dockerfile copies this to backend static/)
npm run lint
npm test             # vitest, 61 tests
npm run dev          # localhost:3000, talks to the backend via .env.development
```

`NEXT_PUBLIC_API_BASE` is the API origin: empty in production (same origin as the
backend), `http://localhost:8000` in dev via `frontend/.env.development`.

Note for whoever runs `npm install` on this machine: the global `~/.npmrc` sets
`allow-scripts`, which npm 11 rejects for project installs. Prefix with
`npm_config_allow_scripts= npm install` if it errors with `EALLOWSCRIPTS`.

## Structure

```
src/app/page.tsx          the whole workstation: owns REST state, wires everything
src/app/layout.tsx        dark shell
src/app/globals.css       Tailwind theme tokens + the price flash keyframes
src/hooks/usePrices.ts    EventSource -> {prices, history, status}
src/hooks/useFlash.ts     tick direction for 500ms after a value changes
src/lib/{types,api,format}.ts
src/components/           Header, Watchlist, Sparkline, MainChart, Heatmap,
                          PnlChart, PositionsTable, TradeBar, ChatPanel, Panel
src/test/{setup,fixtures}.ts
```

State model: `usePrices` owns the SSE stream (prices keyed by ticker, plus a
per-ticker price series accumulated since page load, capped at 400 points).
`page.tsx` owns the REST state with plain `fetch` and refetches the portfolio,
watchlist and snapshot history after a trade or a chat reply, plus a 30s poll for
snapshots. No state-management or data-fetching library. All charts are Recharts.

## Contract testids — all present

`connection-status` (`data-state=connected|reconnecting|disconnected`),
`cash-balance`, `total-value`, `watchlist`, `watchlist-row-{T}`,
`watchlist-price-{T}`, `watchlist-add-input`, `watchlist-add-submit`,
`watchlist-remove-{T}`, `main-chart` (`data-ticker`), `positions-table`,
`position-row-{T}`, `heatmap`, `heatmap-tile-{T}` (`data-pnl=profit|loss|flat`),
`pnl-chart`, `trade-ticker`, `trade-quantity`,
`trade-buy`, `trade-sell`, `trade-error`, `chat-panel`, `chat-input`,
`chat-send`, `chat-loading`, `chat-message-{n}` (`data-role=user|assistant`).

## Notes for the Integration Tester

- `chat-message-{n}` is **0-indexed**: the first message in the panel is
  `chat-message-0`. A fresh send appends the user message first, then the
  assistant reply, so indices grow by two per exchange.
- `chat-loading` exists only while a `POST /api/chat` is in flight;
  `trade-error` exists only after a rejected trade. Neither is rendered
  otherwise, so assert with presence/absence, not text content.
- The chat panel starts expanded. It can be collapsed via the `›` button
  (`aria-label="Collapse AI assistant"`); collapsed, `chat-panel` is absent and
  the rail button is `aria-label="Open AI assistant"`.
- `positions-table` is absent when there are no positions — an empty-state
  paragraph renders instead. Same for `heatmap`/`pnl-chart`/`main-chart`: those
  containers always exist, but they hold a placeholder until data arrives
  (`main-chart` and `pnl-chart` need 2+ points).
- Price flash is the CSS class `flash-up` / `flash-down` on the price cell,
  removed after 500ms.
- `heatmap-tile-{T}` is the `<g>` wrapping one treemap tile. There is exactly
  one per position: Recharts renders tile content for its synthetic root node
  too, and that root is suppressed, so a prefix count
  (`[data-testid^="heatmap-tile-"]`) equals the position count. `data-pnl` is
  `profit` when `unrealized_pnl > 0`, `loss` when `< 0`, `flat` at exactly 0,
  and the tile fill is derived from the same sign, so asserting the attribute
  asserts the colour semantics. Tiles exist only for positions with a
  market value above 0; with no positions the container holds a
  "No positions yet" placeholder and no tiles.
- Persisted chat history from `GET /api/chat/history` renders on load, so the
  message count after a reload equals the stored count, and stored `actions` on
  assistant messages render as the same inline chips as a live reply.
- `connection-status` leaves `connected` the moment the stream drops (it goes to
  `reconnecting` while EventSource retries, or `disconnected` if the browser
  gives up with the socket closed) and returns to `connected` on its own once
  the stream recovers. There is no hand-rolled retry: the dot only reflects
  EventSource's own `onopen`/`onerror`.
- Session change % is computed on the client from the first price seen since page
  load, so it is `0.00%` immediately after load and only meaningful after a few
  stream frames. It is not the backend's `change_percent`.
- Header `total-value` is recomputed live from stream prices
  (`cash + sum(qty * live price)`), so it will differ slightly from
  `GET /api/portfolio`'s `total_value` between polls. `cash-balance` comes
  straight from the API.
- Removing the currently selected ticker falls back to the first watchlist row.
- Buy is green and Sell is red (trading convention); the purple `#753991`
  submit colour is used for the chat send button.

## Contract mismatches

None. Every shape in CONTRACTS.md sections 3 and 4 was consumed as written,
including `GET /api/chat/history` and the `{"detail": ...}` error body.
