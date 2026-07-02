# Composio Integration Plan — Aunix Digital Worker

**Project:** `Newapproches/aunix-digital-worker`  
**Date:** July 2026  
**Status:** Proposed  
**References:** [Composio docs](https://docs.composio.dev), [Mastra docs](https://mastra.ai/docs), FlowOps implementation (`Newapproches/flowops`)

---

## 1. Executive summary

Digital Worker today uses **hardcoded connectors** (e.g. HubSpot deals via raw `httpx`). That does not scale to multiple systems, objects, or OAuth.

**Recommendation:** Add **Composio Python SDK** as the external integration layer. Keep the existing Python/FastAPI engine, `AgentSpec`, L1–L4 autonomy, and approval inbox.

**Do not adopt Mastra inside Digital Worker.** Mastra is TypeScript-only. Use it as a **pattern reference** from FlowOps (tools, approval, compile-time discovery). Implement the equivalent in Python.

### Core rule

| Phase | Dynamic? | Mechanism |
|-------|----------|-----------|
| **Agent setup (compile)** | Yes | Composio `session.search()` + schema + optional probe |
| **Scheduled runs (runtime)** | No | Frozen `tool_slug` + `arguments` in `AgentSpec` → `session.execute()` |

This matches Composio’s own guidance: sessions for discovery; direct/session execute for deterministic calls. It also matches FlowOps (discover in chat, fixed tool nodes at runtime).

---

## 2. Current state (baseline)

### What works today

| Component | Location | Role |
|-----------|----------|------|
| Compiler | `aunix/compiler.py` | NL → `AgentSpec` |
| Runner | `aunix/runner.py` | fetch → evaluate → reason → notify → act |
| HubSpot read | `aunix/connectors/hubspot.py` | Hardcoded `/crm/v3/objects/deals` |
| HubSpot write | `aunix/actions/executors.py` | Hardcoded note + property patch |
| L3/L4 actions | `aunix/actions/service.py`, `gate.py` | Approval queue + policy |
| SimShip / CSV | `connectors/simship.py`, `csv_source.py` | Local sources (keep as-is) |

### Pain points

1. Every new CRM object or platform = new Python connector + executor.
2. HubSpot auth is a single env token; OAuth is explicitly deferred.
3. Compiler only knows `simship | hubspot | csv`.
4. No way to **test** a connected system without shipping code.

### What FlowOps already proved (organizational reference)

FlowOps (`@composio/core` + Mastra) uses:

- `composio.create(userId, { toolkits, authConfigs })` — scoped session
- `session.search()`, `session.execute()`, `session.authorize()` — discovery + runtime
- Human approval for planning-time `execute_composio_tool`
- Fixed `composioToolSlug` on workflow nodes at runtime

Digital Worker should mirror the **Composio patterns**, not the Mastra stack.

---

## 3. Composio concepts (from official docs)

Source: [What is a session?](https://docs.composio.dev/docs/how-composio-works), [Sessions vs direct execution](https://docs.composio.dev/docs/sessions-vs-direct-execution), [Configuring sessions](https://docs.composio.dev/docs/configuring-sessions)

### Terminology (v3)

| Old term | Current term |
|----------|--------------|
| entity ID | **user ID** (`user_id`) |
| actions | **tools** (e.g. `HUBSPOT_LIST_DEALS`) |
| apps | **toolkits** (e.g. `hubspot`, `salesforce`) |
| integration | **auth config** |
| connection | **connected account** |

### Session

```python
from composio import Composio

composio = Composio()  # reads COMPOSIO_API_KEY
session = composio.create(
    user_id="org-user-uuid",           # stable ID from your DB — not email
    toolkits=["hubspot", "salesforce"],
    auth_configs={"hubspot": "ac_..."},  # optional white-label OAuth
)
```

A session scopes: **user**, **toolkits**, **auth**, **connected accounts**, **execution state**.

### Two integration modes — how we use each

| Composio mode | When Digital Worker uses it |
|---------------|------------------------------|
| **Session + meta tools** (`session.tools()` → `COMPOSIO_SEARCH_TOOLS`, etc.) | Optional for open-ended compile chat |
| **Session + `search()` / `execute()` / `authorize()`** | **Primary** — compile discovery, runtime fetch, OAuth |
| **Direct tools preset** (`SESSION_PRESET_DIRECT_TOOLS`) | Optional narrow agents with known tool set |
| **Direct execution** (`composio.tools.execute`) | Discouraged by Composio unless you need full control; we prefer `session.execute()` for auth scoping |

### Sessions vs direct execution (Composio comparison)

| | Sessions (discovery) | Direct execute (runtime) |
|--|---------------------|--------------------------|
| Discovery | Agent/code searches at setup | Tool slug fixed in `AgentSpec` |
| Latency | Multiple steps | Single call |
| Human approval | Configurable on session | **We intercept in L3/L4 code** |
| Auth | `session.authorize()` + Connect Link | Reuses connected accounts |
| Determinism | Low (runtime discovery) | **High** — required for scheduled monitoring |

**Digital Worker uses both deliberately:** discovery at compile, frozen execute at run.

### User ID best practices (Composio)

- ✅ Use stable DB primary key per operator/org
- ⚠️ Avoid email (can change)
- ❌ Never use `default` in production (cross-user data leak)

Map `Agent.owner` or org tenant ID → `COMPOSIO_USER_ID`.

---

## 4. Mastra concepts — reference only

Source: [Mastra Agents](https://mastra.ai/docs/agents/overview), [Using tools](https://mastra.ai/docs/agents/using-tools), [Agent approval](https://mastra.ai/docs/agents/agent-approval)

Mastra is **TypeScript**. Digital Worker stays **Python**. Use these as design patterns:

| Mastra feature | Digital Worker equivalent today | Composio integration |
|----------------|--------------------------------|----------------------|
| `createTool()` + `execute` | `Connector.fetch()` / `ActionExecutor.execute()` | `ComposioConnector` / `ComposioActionExecutor` |
| `requireApproval: true` on tools | L3 `Approvals` inbox | Gate before `session.execute()` for write tools |
| `beforeToolCall` hooks | `actions/gate.py` L4 policy | Validate slug against `ActionPolicy` allowlist |
| Agent + tools in instructions | `compiler.py` system prompt | Add Composio search tools to compile flow |
| Skills / workspace | None today | Optional later: markdown playbooks per toolkit |
| MCP tools | N/A | Composio also offers `session.mcp.url` — **not recommended** for Digital Worker MVP (SDK is simpler) |

### Why not add Mastra to Digital Worker?

1. Entire backend is Python (FastAPI, SQLAlchemy, pytest).
2. Mastra requires TypeScript — would mean a second service or full rewrite.
3. FlowOps already owns the Mastra + Composio **workflow builder** lane.
4. Digital Worker’s value is **scheduled deterministic monitoring** — a thin Composio layer is enough.

**Convergence path:** Share Composio project credentials and toolkit config across FlowOps and Digital Worker; share patterns, not code.

---

## 5. Target architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js Web UI (web/)                                          │
│  /create  /feed  /approvals  /integrations (new)                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST
┌───────────────────────────▼─────────────────────────────────────┐
│  FastAPI (aunix/api.py)                                           │
│  compile · agents · runs · actions · integrations/* (new)         │
└───────┬───────────────────────────────────────┬───────────────────┘
        │                                       │
┌───────▼────────┐                    ┌─────────▼─────────┐
│ COMPILE-TIME   │                    │ RUNTIME           │
│ compiler.py    │                    │ worker.py         │
│ + composio     │                    │ runner.py         │
│   search/schema│                    │ + composio        │
│   probe (opt)  │                    │   session.execute │
└───────┬────────┘                    └─────────┬─────────┘
        │                                       │
        └──────────────────┬────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  aunix/composio/       │
              │  client.py             │
              │  operations.py         │
              │  connector.py          │
              │  executor.py           │
              │  normalize.py          │
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │  Composio Python SDK   │
              │  composio.create()     │
              │  session.search()      │
              │  session.execute()     │
              │  session.authorize()   │
              └────────────────────────┘
```

### Data flow

**Setup (once per agent):**

1. User describes intent in `/create`.
2. Compiler checks `session.toolkits()` — what’s connected?
3. Compiler calls `session.search(query)` — which tools match?
4. Compiler fetches tool input schema — required fields?
5. Optional: **probe** read-only `session.execute()` — sample rows?
6. Compiler emits `AgentSpec` with `ComposioSource` (frozen slug + args + row mapping).

**Every scheduled run:**

1. `ComposioConnector.fetch()` → `session.execute(tool_slug, arguments)`.
2. `normalize.py` maps JSON → `list[dict]` rows.
3. Existing pipeline: conditions → reason → findings → notify → L3/L4 actions.
4. Write actions → `ComposioActionExecutor` → `session.execute(action_slug, params)`.

---

## 6. Schema changes (`AgentSpec`)

### New: Composio data source

```python
class ComposioSource(BaseModel):
    type: Literal["composio"] = "composio"
    toolkit: str                    # e.g. "hubspot"
    tool_slug: str                  # e.g. "HUBSPOT_LIST_DEALS"
    arguments: dict[str, Any] = {}  # frozen at compile time
    record_key: str                 # e.g. "hubspot_id"
    row_mapping: dict[str, str]     # response path → row field
    # e.g. {"properties.dealname": "lead", "properties.amount": "deal_size"}
```

`AgentSpec.data_sources` becomes `list[str | ComposioSource]` or a discriminated union:

- `"simship"`, `"csv"` — unchanged legacy string slugs
- `ComposioSource` — external SaaS via Composio

### New: Composio action permission

```python
class ComposioActionPermission(BaseModel):
    type: Literal["composio"] = "composio"
    tool_slug: str
    argument_template: dict[str, Any]  # supports {{finding.*}} interpolation
```

Extend L4 `ActionPolicy` with:

```python
composio_auto: bool = False
composio_tool_slugs: list[str] = []   # allowlist for auto-execute
```

### Migration

- Existing agents with `"hubspot"` string → migration script or runtime alias to default Composio slug.
- Deprecate `HubSpotConnector` / `HubSpotActionExecutor` after Phase 2 validation.

---

## 7. New module layout

```
aunix/composio/
├── __init__.py
├── client.py          # Composio(), get_session(user_id), auth_configs from env
├── constants.py       # ENABLED_TOOLKITS, display names (mirror FlowOps)
├── operations.py      # search, get_schema, execute, list_connections, authorize
├── connector.py       # ComposioConnector implements Connector protocol
├── executor.py        # ComposioActionExecutor implements ActionExecutor
├── normalize.py       # response JSON → list[dict] via row_mapping
└── __tests__/
    ├── test_normalize.py
    ├── test_connector.py      # mocked session.execute
    └── test_operations.py     # mocked SDK

aunix/api/
└── integrations.py    # GET /integrations/status, POST /integrations/connect, POST /integrations/probe
```

### `client.py` (pattern from FlowOps)

```python
from composio import Composio

composio = Composio()  # COMPOSIO_API_KEY from env

def get_session(user_id: str, toolkits: list[str] | None = None):
    auth_configs = resolve_auth_configs()  # COMPOSIO_AUTH_CONFIG_* env vars
    return composio.create(
        user_id=user_id,
        toolkits=toolkits or get_enabled_toolkits(),
        auth_configs=auth_configs or None,
    )
```

### `operations.py` (pattern from FlowOps `operations.ts`)

```python
def search_tools(session, query: str, toolkits: list[str] | None = None):
    return session.search(query=query, **({"toolkits": toolkits} if toolkits else {}))

def execute_tool(session, tool_slug: str, arguments: dict) -> dict:
    return session.execute(tool_slug, arguments)

def get_connect_link(session, toolkit: str, callback_url: str):
    return session.authorize(toolkit, {"callback_url": callback_url})
```

### Runtime connector

```python
class ComposioConnector:
    source_id = "composio"

    def __init__(self, session, spec: ComposioSource):
        self.session = session
        self.spec = spec

    def fetch(self) -> list[dict]:
        result = execute_tool(self.session, self.spec.tool_slug, self.spec.arguments)
        return normalize_rows(result, self.spec.row_mapping)
```

---

## 8. Compiler changes

Update `aunix/compiler.py` system prompt and optionally add a **compile-time tool loop**:

### Phase 2a — Prompt-only (fastest)

Extend rules:

```
- data_sources may include "simship", "csv", or a composio object:
  { type: "composio", toolkit, tool_slug, arguments, record_key, row_mapping }
- Before choosing a composio source, assume these toolkits may be available:
  hubspot, salesforce, quickbooks, netsuite, gmail
- Prefer read/list/query tools for monitoring; never guess tool slugs — use
  placeholders and let the compile API resolve them via Composio search.
```

Add API step **before** LLM compile:

```python
connections = list_connections(user_id)
search_results = search_tools(session, user_message)
# Pass connection status + top search hits into compiler context
```

### Phase 2b — Structured compile pipeline (recommended)

```
POST /agents/compile
  1. list_connections(user_id)
  2. search_tools(user_id, intent_text)
  3. get_tool_schema(top_slug)
  4. LLM → AgentSpec with ComposioSource
  5. optional POST /integrations/probe → validate rows
```

---

## 9. API additions

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/integrations/status` | GET | Connected toolkits + auth status per user |
| `/integrations/connect` | POST | `{ toolkit }` → OAuth redirect URL |
| `/integrations/callback` | GET | OAuth return (or reuse web page) |
| `/integrations/probe` | POST | `{ tool_slug, arguments, row_mapping }` → sample rows |
| `/integrations/search` | POST | `{ query, toolkits? }` → Composio search results (compile helper) |

### OAuth callback

Mirror FlowOps `connections/callback`: popup posts message to opener, refresh connection status.

`callback_url` = `{NEXT_PUBLIC_APP_URL}/integrations/callback`

---

## 10. Environment variables

Add to `.env` and document in `README.md` (create `.env.example`):

| Variable | Required | Purpose |
|----------|----------|---------|
| `COMPOSIO_API_KEY` | **Yes** | Composio API authentication |
| `COMPOSIO_USER_ID` | Dev only | Default user when agent has no owner mapping |
| `COMPOSIO_AUTH_CONFIG_HUBSPOT` | No | Auth config ID override |
| `COMPOSIO_AUTH_CONFIG_SALESFORCE` | No | Same pattern per toolkit |
| `COMPOSIO_AUTH_CONFIG_QUICKBOOKS` | No | |
| `COMPOSIO_AUTH_CONFIG_NETSUITE` | No | |
| `COMPOSIO_AUTH_CONFIG_GMAIL` | No | |
| `NEXT_PUBLIC_APP_URL` | No | OAuth callback base (default `http://localhost:3000`) |

### Python dependency

Add to `pyproject.toml`:

```toml
dependencies = [
    ...
    "composio>=0.8",  # pin after spike — verify session.search/execute API
]
```

Run spike against installed version; Composio v3 session API is the target.

---

## 11. Autonomy levels with Composio (business view)

Use case: *"Tell me when HubSpot deals over $50k sit in Negotiation for 7+ days."*

| Level | What the operator experiences | Composio involvement |
|-------|------------------------------|----------------------|
| **L1 Notify** | One alert in feed/email per stale deal | **Read:** `session.execute` list/query tool on schedule |
| **L2 Recommend** | Alert + suggested next step in text | Same read; LLM narrates recommendation |
| **L3 Execute w/ approval** | Approvals card: "Add note to Deal #1842" → Approve | **Read** on schedule; **Write** `session.execute` only after approval |
| **L4 Autonomous** | Auto internal notes; exceptions queue to Approvals | **Write** auto when `policy.composio_tool_slugs` allows |

**Safety:** L4 never bypasses L3 for non-whitelisted tools. Global `AUNIX_ACTIONS_ENABLED` kill switch unchanged.

### Two-system example (HubSpot + email)

| Level | Behavior |
|-------|----------|
| L1 | Alert you only |
| L2 | Alert + "Recommend notifying deal owner" |
| L3 | Two approval cards: HubSpot note + email to owner |
| L4 | Auto HubSpot note; email only if `email_to_domains` policy matches |

---

## 12. Phased implementation plan

### Phase 0 — Spike (2–3 days)

**Goal:** Prove Python SDK works for one HubSpot read tool.

- [ ] Add `composio` package; `COMPOSIO_API_KEY` in `.env`
- [ ] Script: `scripts/composio_spike.py` — create session, search "list deals", execute, print rows
- [ ] Document exact tool slug Composio uses for HubSpot deals
- [ ] Confirm `session.execute(slug, args)` works with connected account

**Exit criteria:** Sample deal rows printed from Composio, not `hubspot.py`.

---

### Phase 1 — Generic read connector (1 week)

**Goal:** Replace `HubSpotConnector` for new agents.

- [ ] Implement `aunix/composio/*` (client, operations, connector, normalize)
- [ ] Add `ComposioSource` to `spec.py`
- [ ] Wire `runtime.py` → `ComposioConnector` when spec has composio source
- [ ] Unit tests with mocked `session.execute`
- [ ] Keep legacy `"hubspot"` string working via alias

**Exit criteria:** Monitoring agent fetches deals via Composio on schedule; conditions still evaluate.

---

### Phase 2 — Compile-time discovery (1 week)

**Goal:** Stop hardcoding tool slugs in compiler prompt.

- [ ] `GET /integrations/status`
- [ ] `POST /integrations/search` + schema fetch in compile pipeline
- [ ] Update `compiler.py` to emit `ComposioSource` with `row_mapping`
- [ ] `POST /integrations/probe` — show sample rows in `/create` UI

**Exit criteria:** User says "watch stale HubSpot deals" → compile resolves tool without code change.

---

### Phase 3 — Write path via Composio (1 week)

**Goal:** Replace `HubSpotActionExecutor`.

- [ ] `ComposioActionPermission` + `ComposioActionExecutor`
- [ ] Extend `ActionPolicy` for composio slug allowlist
- [ ] L3 approval shows tool slug + arguments before execute
- [ ] Integration test: breach → pending action → approve → Composio write

**Exit criteria:** L3 note-on-deal works via Composio; L4 policy respects slug allowlist.

---

### Phase 4 — Connections UI (1 week, optional)

**Goal:** Operators connect systems without editing `.env`.

- [ ] Web page `/integrations` — toolkit cards, connect buttons
- [ ] OAuth popup + callback
- [ ] Status indicators on `/create` when toolkit not connected

**Exit criteria:** Connect HubSpot from UI; compile detects connection.

---

### Phase 5 — Cleanup (ongoing)

- [ ] Remove `aunix/connectors/hubspot.py` and `HubSpotActionExecutor` when parity proven
- [ ] Add `.env.example`
- [ ] Export tool catalog script (like FlowOps `scripts/export-composio-tool-catalog.mjs`)
- [ ] Align enabled toolkits with FlowOps org config

---

## 13. Testing strategy

### Unit tests (offline, required for every PR)

| Test | Mocks |
|------|-------|
| `normalize_rows` | Static Composio JSON fixtures |
| `ComposioConnector.fetch` | Mock `session.execute` |
| `ComposioActionExecutor` | Mock execute + L3 gate |
| Compiler emits `ComposioSource` | `FakeLlm` + fixture search results |

### Integration tests (optional CI job, secrets required)

```bash
COMPOSIO_API_KEY=... COMPOSIO_USER_ID=test-user uv run pytest -m composio_integration
```

- Connect test HubSpot account in Composio dashboard
- Probe read tool returns rows
- Write tool rolls back or uses sandbox deal

### Manual QA checklist

- [ ] Compile agent with unconnected toolkit → clear "connect HubSpot" message
- [ ] Connect via OAuth → compile succeeds
- [ ] Scheduled run fetches rows → condition breach → single alert
- [ ] L3 approve → write visible in HubSpot
- [ ] L4 auto only fires for allowlisted slugs

---

## 14. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Composio tool slug changes | Store slug in spec; version agents; probe on compile |
| Row shape varies per account | `row_mapping` in spec; probe step shows sample |
| Latency on scheduled runs | No search at runtime; single `execute` call |
| Cross-user data leak | Never use shared `COMPOSIO_USER_ID` in prod; map `Agent.owner` |
| L3/L4 bypass | Keep `AUNIX_ACTIONS_ENABLED`; gate all writes |
| Python SDK drift vs FlowOps TS SDK | Pin versions; share spike results across teams |
| Adding Mastra "for consistency" | **Reject** — doubles stack complexity without benefit |

---

## 15. Decision log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Integration SDK | Composio Python | Official v3 session API; matches FlowOps |
| Agent framework | **Keep Python compiler** | No Mastra in Python app |
| Discovery | Compile-time `session.search()` | Composio recommends sessions for discovery |
| Runtime | `session.execute()` frozen slug | Deterministic scheduled monitoring |
| MCP | Not used | SDK simpler for our use case |
| SimShip / CSV | Keep hardcoded | Local data; no Composio needed |
| Approval | Keep L3 inbox + L4 policy | Maps to Mastra `requireApproval` pattern without Mastra |

---

## 16. References

### Composio

- [Welcome / SDK guardrails](https://docs.composio.dev/python/quickstart)
- [What is a session?](https://docs.composio.dev/docs/how-composio-works)
- [Sessions vs direct execution](https://docs.composio.dev/docs/sessions-vs-direct-execution)
- [Configuring sessions](https://docs.composio.dev/docs/configuring-sessions)
- [Python session SDK reference](https://docs.composio.dev/reference/sdk-reference/python/session-context-impl)

### Mastra (patterns only)

- [Using tools](https://mastra.ai/docs/agents/using-tools)
- [Agent approval](https://mastra.ai/docs/agents/agent-approval)
- [Agent Builder / integrations](https://mastra.ai/docs/agent-builder/integrations)

### Internal

- FlowOps Composio layer: `Newapproches/flowops/src/lib/composio/`
- FlowOps master agent tools: `Newapproches/flowops/src/mastra/master-agent.ts`
- Digital Worker README autonomy table: `README.md`

---

## 17. Next action

Start **Phase 0 spike**: `scripts/composio_spike.py` with your Composio API key and a connected HubSpot test account. Confirm the exact `tool_slug` for listing deals, then proceed to Phase 1.
