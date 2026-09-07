# Database layer — done

`backend/app/db/`, tested by `backend/tests/db/` (41 tests). Import everything from
`app.db`; the submodules are an implementation detail.

## Files

| File | What |
|---|---|
| `schema.sql` | DDL for the six tables in PLAN.md §7, unique constraints, indexes, FKs to `users_profile` |
| `connection.py` | `get_connection()`, `use_connection()`, `db_path()` |
| `init.py` | `init_db()`, `DEFAULT_WATCHLIST` |
| `models.py` | `Position`, `Trade`, `Snapshot`, `ChatMessage`, `WatchlistEntry`, `now_iso()`, `normalise_ticker()` |
| `profile.py` `watchlist.py` `positions.py` `trades.py` `snapshots.py` `chat.py` | the repository functions from CONTRACTS.md §1 |

## What the Backend API Engineer needs to know

- Call `init_db()` once on startup. It creates the parent directory, applies the schema
  and seeds. Safe to call repeatedly.
- `DB_PATH` env var, default `db/finally.db`, read on every connection so tests can
  repoint it with `monkeypatch.setenv`.
- Atomic trade execution:

  ```python
  with get_connection() as conn:
      set_cash_balance(new_cash, conn=conn)
      upsert_position(ticker, qty, avg_cost, conn=conn)
      trade = record_trade(ticker, side, qty, price, conn=conn)
      conn.commit()
  ```

  Passing `conn` means the function does not commit. Any exception inside the `with`
  rolls back the whole thing — covered by `tests/db/test_transactions.py`.
- Tickers are upper-cased and stripped on every write and lookup, so `get_position("aapl")`
  works.
- `record_trade`, `record_snapshot` and `add_chat_message` return the row they wrote,
  including the generated `id` and ISO timestamp.
- `Position.to_dict()` returns the four DB columns only. The API's richer position shape
  (current price, P&L) is the service layer's `PositionView`.

## Interpretations of the contract

1. **Seeding the watchlist.** The ten default tickers are seeded only when the watchlist is
   empty, not per-ticker. Otherwise a ticker the user removed would come back on the next
   restart. The profile row is a plain `INSERT OR IGNORE`, so an edited cash balance survives.
2. **`limit` with oldest-first ordering.** `list_snapshots` and `list_chat_messages` return
   the *newest* `limit` rows in chronological order — the latest 500 points for the chart and
   the most recent 50 messages for the prompt. A literal "oldest first, limit 500" would pin
   both to the beginning of history forever.
3. **`get_cash_balance` with no profile row** returns `0.0` rather than raising;
   `set_cash_balance` upserts, so it creates the profile if it is missing.
4. **`ChatMessage.to_dict()` includes `id`**, which the `GET /api/chat/history` example omits.
   Drop the key in the route if you want an exact match.
