# Team Charter

Six engineers build FinAlly in parallel on the branch `feat/trading-workstation`.
`CONTRACTS.md` is the binding interface spec; `PLAN.md` is the product spec.

## File ownership — never edit outside your lane

| Engineer | Owns |
|---|---|
| Database Engineer | `backend/app/db/**`, `backend/tests/db/**` |
| Backend API Engineer | `backend/app/api/**`, `backend/app/services/**`, `backend/app/main.py`, `backend/app/market/stream.py`, `backend/tests/api/**`, `backend/tests/services/**` |
| LLM Engineer | `backend/app/llm/**`, `backend/app/api/chat.py`, `backend/tests/llm/**` |
| Frontend Engineer | `frontend/**` |
| DevOps Engineer | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/**`, `.env.example` |
| Integration Tester | `test/**` |
| Tech Lead (orchestrator) | `backend/pyproject.toml`, `planning/**`, `README.md`, `.gitignore` |

Need a change outside your lane, a new dependency, or a contract amendment? Ask the Tech
Lead. Do not reach into someone else's files, and do not run `git commit`, `git checkout`,
or `git stash` — the Tech Lead handles version control.

## Rules

- Python: `uv` only, run from `backend/`. `uv run --extra dev pytest`, `uv run --extra dev ruff check`.
  Never `pip`, never `requirements.txt`. Ask the Tech Lead to add dependencies.
- Match the existing style in `backend/app/market/` — `from __future__ import annotations`,
  type hints, module docstrings, comments only where the *why* isn't obvious.
- Write real unit tests, not mock theatre. Test behaviour and edge cases.
- Leave no TODOs behind. No emojis anywhere. Keep it simple; do not over-engineer.
- Before you report done: your tests pass, `ruff check` is clean, and nothing you changed
  breaks the existing 73 market data tests.

## Status board

Write your own file: `planning/status/<your-role>.md` (e.g. `database.md`, `frontend.md`).
Keep it short — what you built, what you tested, anything the next engineer must know.
One file per engineer so nobody clobbers anybody.
