# Digital Worker — Stage 0 & Stage 1 Implementation Plan

**Project:** `Newapproches/aunix-digital-worker` (+ Mastra compile in `Newapproches/flowops`)  
**Goal:** Test full DWA in the **current DW web UI** before unifying with FlowOps Automation Studio  
**Date:** July 2026  
**Status:** Proposed for review

---

## Straight answer: Are Stage 0 and Stage 1 enough to test full DWA in the DW UI?

**No — but they are the only *new build phases* you need before FlowOps unification.**

| What Stage 0 + 1 cover | What you still need (already built or operational) |
|------------------------|--------------------------------------------------|
| Define “done” + test checklist | Run **API** + **web** + **worker** (3 terminals) |
| Reliable **compile** via full Mastra agent | Existing **Python runtime** (run, feed, L3/L4) |
| Validation, probe approval, judge before Confirm | **Composio** connections + `.env` keys |
| Wire DW **Create** UI to Mastra compile | **Mailgun** for email-channel L1/L2 tests |

**You do not need Stage 2+ (FlowOps UI merge, two studios)** to test in the DW UI.

**During Stage 1 testing**, you may find small runtime/UI fixes (not a new stage — fix as part of Stage 1 exit criteria until L1–L4 golden paths pass).

---

## Architecture for Stage 0 & 1

```text
┌─────────────────────────────────────────────────────────────┐
│  DW Web UI (localhost:3000) — UNCHANGED as your test surface   │
│  /create  /agents  /feed  /approvals  /integrations          │
└───────────────────────────┬─────────────────────────────────┘
                            │
         compile (NEW)      │      runtime (EXISTING)
                            ▼
┌───────────────────────────────┐   ┌──────────────────────────┐
│  FlowOps Mastra               │   │  DW Python API (:8000)   │
│  digitalWorkerAgent           │   │  + worker scheduler        │
│  search / schema / probe      │   │  run → findings → notify   │
│  judge → submit AgentSpec     │   │  L3/L4 action gate         │
└───────────────────────────────┘   └──────────────────────────┘
```

**Principle:** Compile = dynamic (Mastra). Run = frozen `AgentSpec` (Python). No runtime arg defaults.

---

# Stage 0 — Define “Done” (no product code)

**Duration:** ~3–5 days  
**Output:** Documents + checklist you can review and sign off

## Purpose

Agree on what “working DWA” means **before** building the Mastra compile agent. Prevents debating success mid-implementation.

## Deliverables

### 0.1 — L1–L4 golden test matrix

Manual tests you will run in the **current DW UI** after Stage 1.

| ID | Level | Scenario (example) | Pass criteria |
|----|-------|-------------------|---------------|
| G1 | L1 | Salesforce opps updated in 5 days → feed only | Plan shows tool + args; Run now → Activity has findings |
| G2 | L1 | QuickBooks overdue invoices → feed + email | Email received at configured address |
| G3 | L2 | Stale SF opps → recommendation in alert text | Finding has non-empty `recommendation` |
| G4 | L3 | SF finding → Gmail follow-up with approval | Approvals card → Approve → action executed |
| G5 | L4 | Auto Composio note within policy whitelist | Auto-executes; non-whitelisted still queues |
| G6 | — | Compile rejects **missing required** args (schema-based) | Confirm disabled + lists missing fields; `{}` OK when schema has no required |
| G7 | — | Probe approval before live Composio call | User must Accept probe; sample rows visible |
| G8 | — | Scheduled run (5 min interval) | Worker running; run appears without manual Run now |

*Customize G1–G5 for your real Salesforce / QuickBooks / Gmail data.*

### 0.2 — “Good plan” checklist (pre-Confirm)

A plan is **confirmable** only when ALL are true:

- [ ] Composio toolkit is **connected** for `COMPOSIO_USER_ID`
- [ ] `tool_slug` is set and matches search recommendation (or documented override)
- [ ] `arguments` pass schema validation (no missing required fields)
- [ ] Date placeholders resolved in spec (`{{now_iso}}`, `{{now_minus_N_days_iso}}`) where needed
- [ ] `record_key` matches a field in **probe sample rows**
- [ ] `conditions` use fields that exist in probe rows (or tool pre-filters time window)
- [ ] Probe executed (user approved) OR user explicitly skips probe with acknowledgment
- [ ] LLM judge verdict = **pass**
- [ ] Deterministic validation report = **passed**

### 0.3 — Compile session states

| State | Meaning | UI |
|-------|---------|-----|
| `interpreting` | Mastra agent running (search, schema, draft) | Spinner on Interpret |
| `validating` | Deterministic checks on draft spec | Checklist updating |
| `awaiting_probe_approval` | Live Composio call needs Accept/Reject | Approval card |
| `probing` | Probe executing | “Running sample fetch…” |
| `judging` | LLM judge reviewing plan | Optional progress |
| `awaiting_confirmation` | Ready for user Confirm | PlanSummary + checklist green |
| `failed` | Stuck or validation failed | Errors + Revise |

### 0.4 — AgentSpec contract notes

Document required fields for `ComposioSource` in compiled specs:

```json
{
  "type": "composio",
  "toolkit": "salesforce",
  "tool_slug": "SALESFORCE_GET_S_OBJECTS_UPDATED",
  "arguments": "{\"sobject\":\"Opportunity\",\"start\":\"{{now_minus_5_days_iso}}\",\"end\":\"{{now_iso}}\"}",
  "record_key": "Id",
  "row_mapping": "{}"
}
```

### 0.5 — Environment checklist for testers

- [ ] `COMPOSIO_API_KEY`, `COMPOSIO_USER_ID` in DW `.env`
- [ ] `OPENAI_API_KEY` in DW `.env`
- [ ] `MAILGUN_*` for email tests
- [ ] FlowOps running for compile API (Stage 1)
- [ ] API: `uv run uvicorn ...` on :8000
- [ ] Web: `npm run dev` in `web/` on :3000
- [ ] Worker: `uv run python -m aunix.worker` for scheduled tests

## Stage 0 exit criteria

- [x] Golden test matrix reviewed and approved by you
- [x] Pre-Confirm checklist approved
- [x] No FlowOps or DW product code required to complete Stage 0

**Stage 0 signed off** — Stage 1 implementation in progress.

---

# Stage 1 — Full Mastra compile + DW UI integration

**Duration:** ~2–3 weeks  
**Where:** Primarily `Newapproches/flowops` (Mastra agent) + `aunix-digital-worker/web` (UI wiring)

## Purpose

Replace single-shot Python `compile_intent` with a **full Mastra digital worker agent** (same quality bar as FlowOps Automation planner). DW web remains the test UI; Python remains runtime.

## 1.1 — Mastra `digitalWorkerAgent` (FlowOps)

**Location:** `flowops/src/mastra/`

| Task | Detail |
|------|--------|
| Add agent | `digitalWorkerAgent` in `agents.ts` |
| Tools | Reuse planner tools: `list_connections`, `search_tools`, `get_tool_schema`, `execute_composio_tool`, `get_connect_link`, `ask_user_question` |
| New tool | `submit_agent_spec` → outputs DW `AgentSpec` JSON (Zod schema matching `aunix/spec.py`) |
| Skills | New `skills/digital-worker-planner/` (monitoring vs analysis, L1–L4, notifications, Composio source rules) |
| Prompt | DW-specific system prompt (not graph builder — no `add_node`, `validate_graph`) |
| Loops | `maxSteps` + `runDigitalWorkerCompileWithContinuations` (port from `run-master-agent.ts`) |
| Gates | `execute_composio_tool` → existing `exec-approval` flow |
| Judge | New `judge_agent_spec` structured call after deterministic validation |

**Reuse from FlowOps (do not reimplement):**

- `lib/composio/operations.ts`
- `lib/composio/validate-tool-arguments.ts`
- `lib/composio/exec-approval.ts`
- `lib/plan/tool-search-coverage.ts`
- `lib/plan/query-tool-policy.ts`

## 1.2 — Compile API routes (FlowOps)

| Route | Purpose |
|-------|---------|
| `POST /api/digital-worker/compile` | Start compile session (SSE stream) |
| `POST /api/digital-worker/compile/continue` | User confirmed probe / answered question |
| `POST /api/digital-worker/compile/message` | Revise description while awaiting confirmation |
| Reuse `POST /api/workflow/composio-exec` | Probe approval (or alias with `studio=digital_worker`) |

**Response shape** (for DW web):

```typescript
{
  status: CompileSessionStatus;
  spec: AgentSpec | null;
  questions: ClarifyingQuestion[];
  validation_report: { passed: boolean; errors: string[]; warnings: string[] };
  composio_context: { connections; tool_search; probe_rows? };
  judge: { verdict: 'pass' | 'fail' | 'revise'; issues: string[] };
}
```

## 1.3 — Deterministic validation (shared)

Run **before** judge and **before** enabling Confirm:

1. `analyzeToolSearchCoverage` — tool matches user intent
2. `getMissingRequiredSchemaFields` — args complete per Composio schema
3. `validateToolArgumentsAgainstSchema` — types/required
4. `validateSpecConditionsAgainstProbeRows` — condition fields exist in sample rows
5. `normalizeAgentSpec` — coerce LLM shorthand (port `normalize-plan.ts` patterns)

**Block Confirm** if any hard error.

## 1.4 — DW web changes

**Location:** `aunix-digital-worker/web/`

| Task | Detail |
|------|--------|
| Env | `NEXT_PUBLIC_FLOWOPS_COMPILE_URL` (or proxy via DW API) |
| `api.ts` | `compileStart`, `compileContinue`, `compileMessage` → FlowOps SSE or REST |
| `/create` | Show validation checklist, probe approval card, judge issues |
| `PlanSummary` | Already shows Composio tool — extend with validation status |
| Confirm | Disabled until `validation_report.passed && judge.verdict === 'pass'` |
| Probe preview | Table of first N probe rows |
| CORS | FlowOps allows `localhost:3000` |

**Optional:** DW Python API proxies compile to FlowOps (keeps single `NEXT_PUBLIC_API_URL`) — your choice at implementation time.

## 1.5 — Python runtime (minimal changes)

**Keep as-is unless golden tests fail:**

- `ComposioConnector` + `interpolate.py` (date placeholders only)
- `runner.py` + `worker.py`
- L3/L4 `gate.py`, approvals API
- **No** runtime arg defaults

Fix only bugs found during G1–G8 testing.

## 1.6 — Testing strategy

| Layer | Tests |
|-------|-------|
| FlowOps unit | Port patterns from `lib/plan/__tests__`, `lib/composio/__tests__` for DW validators |
| Mastra harness | `digitalWorkerAgent` tool binding tests |
| DW pytest | Existing 164+ tests stay green |
| Manual | Run golden matrix G1–G8 in DW UI |

## Stage 1 exit criteria

- [ ] All **Stage 0 golden tests G1–G8** pass in DW UI
- [ ] No agent activatable when **required** Composio schema fields are missing
- [ ] Probe approval works for live Composio calls at compile time
- [ ] Manual Run now + worker schedule both produce expected findings
- [ ] L3 approve/reject and L4 policy paths verified (G4, G5)
- [ ] You sign off: “DWA is ready to merge into FlowOps umbrella”

---

# What comes after Stage 1 (not required for DW UI testing)

| Stage | What | When |
|-------|------|------|
| **Stage 2** | Digital Worker Studio inside FlowOps UI | After your sign-off |
| **Stage 3** | Retire standalone DW web; two studios one platform | After Stage 2 |
| **Stage 4** | Optional runtime unification | Long-term |

---

# Review checklist (for you)

Before approving this plan, confirm:

- [ ] Golden tests G1–G8 match what you care about
- [ ] Mastra compile agent lives in **FlowOps** (not a second duplicate service)
- [ ] DW web stays the test UI until Stage 2
- [ ] Python worker is in scope for G8 (scheduled runs)
- [ ] Email tests (G2) require Mailgun in `.env`

---

# Summary timeline

| Week | Focus |
|------|-------|
| **Week 1** | Stage 0: test matrix, checklists, review sign-off |
| **Week 2** | Stage 1a: `digitalWorkerAgent` + tools + skills + API routes |
| **Week 3** | Stage 1b: DW web wiring + validation UI + judge |
| **Week 4** | Stage 1c: Golden path testing G1–G8, fixes, sign-off |

---

**Document owner:** Engineering  
**Next step after approval:** Implement Stage 0 deliverables (0.1 golden matrix customization with your Salesforce/QB/Gmail scenarios).
