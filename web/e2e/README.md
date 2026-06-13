# End-to-end tests (Playwright)

Browser-driven tests that exercise the real UI against a live backend.

## Prerequisites

Run both servers, with execution enabled, against a **fresh** backend DB so the
seed is deterministic:

```bash
# from the repo root
rm -f aunix.db data/simship.json && rm -rf data/uploads
set -a; . ./.env; set +a          # OPENAI_API_KEY (+ optional Mailgun/HubSpot)
AUNIX_ACTIONS_ENABLED=true \
AUNIX_API_CORS_ORIGINS='["http://localhost:3001"]' \
  uv run uvicorn "aunix.api:create_default_app" --factory --port 8000 &

cd web && npm run dev          # note the port it binds (e.g. 3001)
```

## Run

```bash
cd web
npx playwright install chromium     # first time only
E2E_BASE_URL="http://localhost:3001" E2E_API_URL="http://localhost:8000" npm run test:e2e
```

`approvals.e2e.ts` triggers a procurement breach in the simulated ERP, runs an
L3 agent (which proposes a `resolve` action), then drives the Approvals inbox in
the browser to approve it — asserting via both the UI and the API that the
action executed and left the queue.
