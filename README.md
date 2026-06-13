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

## Autonomy levels

Every agent declares an `autonomy_level`. The ladder runs from *informs you* to *acts for
you*; each level is a strict superset of the one below it.

| Level | Name | What the agent does | Actions | Status |
|---|---|---|---|---|
| **L1** | Notify | Polls sources on schedule, evaluates conditions deterministically, narrates findings with the LLM, and alerts **once per issue** via feed + email. | — (forbidden) | ✅ implemented |
| **L2** | Recommend | Same monitoring + alert-once pipeline as L1, with the narration framed as a recommended next step. | — (forbidden) | ✅ implemented |
| **L3** | Execute with approval | On each **new** finding, proposes actions (`email` / `hubspot` note·property / `task` / `resolve`). Proposals queue in the **Approvals** inbox; a human approves (optionally editing) or rejects; approving executes and audits the result; stale proposals auto-expire. | required (`actions`) | ✅ implemented |
| **L4** | Autonomous within policy | Same proposal step, but a declarative `policy` auto-executes the whitelisted, in-bounds subset within per-run / per-day caps. Anything outside the policy falls back to the L3 approval queue — never dropped. | required (`actions` + `policy`) | ✅ implemented |

Safety invariant — **L4 ⊆ L3**: L4 only auto-approves what its policy explicitly permits
(type whitelist + target bounds + caps); everything else queues for a human. Nothing executes
unless the global kill switch is on, and L1/L2 agents never reach the act phase.

### Configuration & API

- Global kill switch: `AUNIX_ACTIONS_ENABLED` (default `false` — set `true` to enable execution).
- Approval / proposal TTL: `AUNIX_ACTION_TTL_HOURS` (default 24); also bounds the L4 per-day cap window.
- HubSpot writes need the `crm.objects.deals.write` scope on the private app.

An L4 `policy` declares per-type auto flags + bounds and caps:

    "autonomy_level": 4,
    "actions": [{ "type": "hubspot", "ops": ["add_note"] }],
    "policy": {
      "hubspot_auto": true, "hubspot_ops": ["add_note"],
      "per_run": 3, "per_day": 20
    }

API: `GET /actions?status=pending`, `POST /actions/{id}/approve` (optional edited `params`),
`POST /actions/{id}/reject`. Auto-executed and queued actions also appear on `GET /runs/{id}`
(with `origin` L3/L4 and `policy_decision` auto/queued).
