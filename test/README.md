# E2E tests

Playwright against the built container. `LLM_MOCK=true`, and a fresh empty database
each run, because `01-fresh-start` asserts the untouched $10,000 seed state.

## Docker (the way CI runs it)

```bash
docker compose -f test/docker-compose.test.yml up --build \
  --abort-on-container-exit --exit-code-from playwright
docker compose -f test/docker-compose.test.yml down -v
```

The app gets a tmpfs on `/app/db`, so the developer's `finally-data` volume is untouched.

## Against a locally running app

```bash
cd test
npm ci
npx playwright install --with-deps chromium
E2E_BASE_URL=http://localhost:8000 npx playwright test
```

The suite is single-worker and ordered: one SQLite portfolio is shared by every test,
and the numbered specs build on each other's state.
