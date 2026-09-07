# DevOps status

## Files

- `Dockerfile` — stage 1 `node:22-slim` builds `frontend/` (`npm ci` if `package-lock.json`
  exists, else `npm install`) and stage 2 `python:3.12-slim` + uv runs the app. Contract
  values are baked in as env: `DB_PATH=/app/db/finally.db`, `STATIC_DIR=/app/static`,
  cwd `/app`, `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`. Runs as the non-root
  `finally` user, which owns `/app/db`. `HEALTHCHECK` hits `/api/health` with `urllib`
  (no curl in the slim image).
- `.dockerignore`, `docker-compose.yml` (service `finally`, volume `finally-data`, `env_file: .env`).
- `scripts/{start,stop}_mac.sh`, `scripts/{start,stop}_windows.ps1` — container `finally`,
  image `finally`, volume `finally-data`, `--env-file .env`. Start takes `--build` and
  `--no-open`; it builds when the image is missing, replaces a running container, prints
  the URL and opens the browser. Stop removes the container only, never the volume.
- `.env.example` unchanged — it already matches PLAN.md §5.

## Verified

Re-validated after the chat route and frontend heatmap changes landed, with
`docker build --no-cache` (what a first-time user gets) and the real scripts rather than
the E2E compose path. A buy of 10 AAPL survived replacing the container: cash 8100.5 and
the position came back from the `finally-data` volume in a container with a new ID.

`docker build -t finally .` succeeds end to end (both stages), and the container was run
against a throwaway volume:

- `GET /api/health` returns `{"status":"ok"}`; `GET /` serves the Next.js export (200);
  `GET /api/portfolio` shows the seeded `cash_balance: 10000.0`; `GET /api/watchlist`
  returns all ten tickers with live simulator prices.
- `/app/db/finally.db` is created in the volume, owned by the non-root `finally` user, and
  survives replacing the container (watchlist still 10 rows, cash still 10000).
- Docker reports the container `healthy`, so the `HEALTHCHECK` works; the urllib command
  was also checked directly to exit non-zero on an unhealthy response.
- `uv sync --frozen --no-dev` works against the current `backend/pyproject.toml` and
  `uv.lock` (dev tools live in `[project.optional-dependencies] dev`, so they are not
  installed). Only `--dry-run` locally — a real local run would uninstall the team's
  pytest and ruff — and for real inside the image.
- `docker compose config` resolves as intended.
- Scripts: `bash -n` clean, and start/stop were run for real — build skip when the image
  exists, rerunning start replaces a running container, stop removes the container and
  keeps the volume, stop twice is a clean no-op. Docker-not-running, missing-`.env` and
  bad-argument paths all produce the intended message and exit 1.
- Cleaned up afterwards: no test containers, volumes or images left behind.

### PowerShell scripts — parse-checked only, never executed

Checked in the `mcr.microsoft.com/powershell` container (pwsh 7.4.2) with
`[System.Management.Automation.Language.Parser]::ParseFile()` and PSScriptAnalyzer 1.22.0
(1.24+ refuses to load below pwsh 7.4.6):

- `start_windows.ps1` and `stop_windows.ps1` both parse with zero errors.
- PSScriptAnalyzer: 9 findings, all `PSAvoidUsingWriteHost` warnings, no errors.

**This proves the scripts parse and are free of the flagged lint classes. It does not prove
they work.** Nobody has ever run them: no Windows host, no Docker Desktop, no check that
`docker` resolves, that `--env-file` accepts a Windows path, that `Start-Process` opens a
browser, or that `$LASTEXITCODE` reads as expected after each call. Treat the Windows path
as untested until someone runs it on Windows. The parse also used PowerShell 7 on Linux,
which does not prove Windows PowerShell 5.1 compatibility — the scripts avoid 7-only syntax
(no ternary, no `??`) so 5.1 should be fine, but that too is reasoning, not a test.

The `Write-Host` warnings are deliberate and were not "fixed". These are interactive
launcher scripts whose entire job is printing to a console. `Write-Output` would push the
strings onto the success stream, and `Write-Information` is silent by default, so the user
would see nothing. The rule targets reusable modules, not user-facing scripts.

## Notes for the team

- `frontend/package-lock.json` should stay committed — otherwise the image build falls back
  to `npm install` and is not reproducible.
- `npm run build` type checks, so a TypeScript error fails the Docker build, not just
  `next dev`. Two such errors blocked the build during development and are now fixed.
- `PLAN.md` §11 says Node 20; the image uses `node:22-slim` (current LTS).
- No `.env` exists in the repo (gitignored). `scripts/start_*` refuse to run without one,
  and `docker compose` errors out too, so everyone needs to copy `.env.example` first.
- The compose volume is pinned to `name: finally-data` so `docker compose up` and
  `scripts/start_*` share one volume instead of two.
- `NEXT_PUBLIC_API_BASE` is unset in the image and `api.ts` falls back to `""`, which is
  what production wants — no build arg needed.
