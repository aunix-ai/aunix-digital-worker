# Aunix Digital Worker

Agentic monitoring/analysis platform MVP. Agents are created conversationally,
run on schedules, evaluate conditions deterministically, narrate findings with
an LLM, and alert via the in-app feed and email - exactly once per issue.

## Quickstart

    uv sync
    uv run pytest                      # full offline test suite

    # demo (no API key needed - rule-based reasoner):
    uv run python -m aunix.demo

    # product surface:
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run uvicorn "aunix.api:create_default_app" --factory --reload  # API on :8000
    uv run python -m aunix.worker                                     # scheduler worker

## Configuration (env / .env, prefix AUNIX_)

| Var | Default | Purpose |
|---|---|---|
| AUNIX_DATABASE_URL | sqlite:///aunix.db | SQLAlchemy URL (Postgres in prod) |
| AUNIX_LLM_MODEL | claude-opus-4-8 | Compiler/reasoner model |
| AUNIX_RESEND_API_KEY | - | Enables the email channel |
| AUNIX_EMAIL_FROM | alerts@aunix.local | Email sender |
| AUNIX_HUBSPOT_ACCESS_TOKEN | - | Enables the hubspot data source |
| AUNIX_SIMSHIP_STATE_PATH | data/simship.json | Simulated shipment feed state |

ANTHROPIC_API_KEY resolves via the Anthropic SDK's standard chain.

## API sketch

POST /agents/compile {text} -> {spec | questions}
POST /agents {owner, spec} -> draft; POST /agents/{id}/activate | /pause | /run
GET /agents, /agents/{id}, /agents/{id}/runs, /runs/{id} (decision trace), /feed
POST /uploads/csv (multipart)
