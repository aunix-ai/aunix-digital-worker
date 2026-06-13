# Aunix Digital Worker

Agentic monitoring/analysis platform MVP. Agents are created conversationally,
run on schedules, evaluate conditions deterministically, narrate findings with
an LLM, and alert via the in-app feed and email - exactly once per issue.

## Quickstart

    uv sync
    uv run pytest                      # full offline test suite

    # demo (no API key needed - rule-based reasoner):
    uv run python -m aunix.demo

    # product surface (LLM runs on OpenAI; see .env):
    export OPENAI_API_KEY=sk-proj-...   # or put it in .env
    uv run uvicorn "aunix.api:create_default_app" --factory --reload  # API on :8000
    uv run python -m aunix.worker                                     # scheduler worker

## Configuration

The LLM runs on OpenAI's Responses API. `OPENAI_API_KEY` is read by the OpenAI
SDK directly; `OPENAI_MODEL` sets the compiler/reasoner model. Everything else is
prefixed `AUNIX_` (env vars or `.env`).

| Var | Default | Purpose |
|---|---|---|
| OPENAI_API_KEY | - | OpenAI credential (read by the SDK) |
| OPENAI_MODEL | gpt-5.1 | Compiler/reasoner model (alias of AUNIX_LLM_MODEL) |
| AUNIX_DATABASE_URL | sqlite:///aunix.db | SQLAlchemy URL (Postgres in prod) |
| AUNIX_RESEND_API_KEY | - | Enables the email channel |
| AUNIX_EMAIL_FROM | alerts@aunix.local | Email sender |
| AUNIX_HUBSPOT_ACCESS_TOKEN | - | Enables the hubspot data source |
| AUNIX_SIMSHIP_STATE_PATH | data/simship.json | Simulated shipment feed state |

The LLM seam (`aunix/llm.py`) ships `OpenAiLlm` (default) and `AnthropicLlm` as
drop-in alternates behind the `LlmClient` protocol; tests use `FakeLlm` and never
touch a live API.

## API sketch

POST /agents/compile {text} -> {spec | questions}
POST /agents {owner, spec} -> draft; POST /agents/{id}/activate | /pause | /run
GET /agents, /agents/{id}, /agents/{id}/runs, /runs/{id} (decision trace), /feed
POST /uploads/csv (multipart)

## Web UI

An operations-console front end (Next.js + Tailwind v4, dark instrument-grade
theme). Design direction is captured in `PRODUCT.md` and `DESIGN.md`.

    cd web
    npm install
    npm run dev        # http://localhost:3000 (API must be on :8000)
    npm test           # component tests (vitest)

Set `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) to point at the API,
and make sure that origin is in `AUNIX_API_CORS_ORIGINS`.

Pages: `/` (agents + lifecycle controls), `/create` (conversational creation
with plan confirmation), `/feed` (activity feed with "why?" links), `/runs/{id}`
(decision trace + data evaluated), `/agents/{id}` (plan, run history),
`/approvals` (pending action proposals, approve / reject).

## Execution agents (L3)

Agents at `autonomy_level: 3` propose actions (email / HubSpot note / task / resolve) on new
findings instead of only notifying. Proposals queue in the **Approvals** inbox; approving runs
the action and audits the result; stale proposals auto-expire.

- Global kill switch: `AUNIX_ACTIONS_ENABLED` (default `false` — set `true` to enable execution).
- Approval TTL: `AUNIX_ACTION_TTL_HOURS` (default 24).
- HubSpot writes need the `crm.objects.deals.write` scope on the private app.

API: `GET /actions?status=pending`, `POST /actions/{id}/approve` (optional edited `params`),
`POST /actions/{id}/reject`. Actions also appear on `GET /runs/{id}`.
