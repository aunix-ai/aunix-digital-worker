# Stage 0 — Golden test matrix (G1–G8)

**Purpose:** Manual tests you will run in the DW UI **after Stage 1** is built.  
**Stage 0 task:** Review each scenario. Edit prompts/pass criteria to match your org. Mark approved.

**Tester email:** `pothamsetti.ganesh@aunix.ai`  
**Composio user:** `flowops-demo-user` (from `.env`)

---

## G1 — L1 · Salesforce · feed only


| Field       | Value            |
| ----------- | ---------------- |
| **Level**   | L1 (notify only) |
| **Toolkit** | Salesforce       |


**Prompt to paste in** `/create`**:**

> Watch my Salesforce opportunities that have been updated in the last 5 days. Alert [pothamsetti.ganesh@aunix.ai](mailto:pothamsetti.ganesh@aunix.ai) in the feed only when you find any. Check every 5 minutes.

**Pass criteria:**

- [ ] Plan shows Composio source: `salesforce` + a concrete `tool_slug`
- [ ] Arguments include `sobject`, `start`, `end` (not empty `{}`)
- [ ] `record_key` is `Id` (or matches probe rows)
- [ ] Notify via: **feed** only (no email unless you added it)
- [ ] Autonomy: **L1**
- [ ] After Confirm + **Run now** → **Activity** shows at least one finding (if SF has updated opps in window)
- [ ] Run trace shows `rows_fetched` > 0 and `breaches` > 0 when data exists

**Approved:** ☐  
**Notes:**

---



## G2 — L1 · QuickBooks · feed + email


| Field       | Value      |
| ----------- | ---------- |
| **Level**   | L1         |
| **Toolkit** | QuickBooks |


**Prompt:**

> Every morning at 8am, list QuickBooks invoices overdue by more than 30 days. Alert me via feed and email at [pothamsetti.ganesh@aunix.ai](mailto:pothamsetti.ganesh@aunix.ai).

**Pass criteria:**

- [ ] Plan shows `quickbooks` Composio tool
- [ ] Schedule: daily 8am (or acceptable alternative you approve)
- [ ] Notifications: feed + email to your address
- [ ] Run now → finding in Activity + email received (check spam)

**Approved:** ☐  
**Notes:**

---



## G3 — L2 · Salesforce · recommendation text


| Field       | Value                   |
| ----------- | ----------------------- |
| **Level**   | L2 (notify + recommend) |
| **Toolkit** | Salesforce              |


**Prompt:**

> Monitor Salesforce opportunities that have not been updated in 14 days. Recommend a specific next step for each stale opportunity. Alert me in the feed. Check every 30 minutes.

**Pass criteria:**

- [ ] Autonomy: **L2**
- [ ] Finding `recommendation` field is non-empty and actionable (not generic placeholder)

**Approved:** ☐  
**Notes:**

---



## G4 — L3 · Salesforce + Gmail · approval required


| Field        | Value                             |
| ------------ | --------------------------------- |
| **Level**    | L3 (execute with approval)        |
| **Toolkits** | Salesforce (read) + Gmail (write) |


**Prompt:**

> Monitor Salesforce opportunities in Negotiation stage for more than 7 days. When you find one, queue approval to send a Gmail email to [pothamsetti.ganesh@aunix.ai](mailto:pothamsetti.ganesh@aunix.ai) with a short follow-up reminder.

**Pass criteria:**

- [ ] Autonomy: **L3**
- [ ] Actions include email or composio (Gmail)
- [ ] After run → **Approvals** page shows pending action
- [ ] **Approve** → action status executed (or clear error you can share)
- [ ] **Reject** → action rejected, not executed

**Approved:** ☐  
**Notes:**

---



## G5 — L4 · Composio write · policy whitelist


| Field       | Value                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| **Level**   | L4 (autonomous within policy)                                               |
| **Toolkit** | Pick one you can safely test (e.g. Salesforce note or HubSpot via Composio) |


**Prompt (example — customize):**

> When a Salesforce opportunity is stale for 7+ days, automatically add an internal note via Composio. Only auto-execute notes; anything else should require approval.

**Pass criteria:**

- [ ] Autonomy: **L4** with `policy` in plan
- [ ] Whitelisted tool slug auto-executes
- [ ] Non-whitelisted action would queue to Approvals (optional negative test)

**Approved:** ☐  
**Notes:**

---



## G6 — Compile validation · required args only (schema-based)

| Field | Value |
|-------|--------|
| **Type** | Stage 1 compile gate (not autonomy) |

**Rule:** Validation is **per tool schema**, not “arguments must be non-empty.”

| Tool schema | `{}` arguments | What happens |
|-------------|----------------|--------------|
| **Required fields** (e.g. SF updated: `sobject`, `start`, `end`) | Missing | **Confirm blocked** — UI lists missing fields |
| **All optional / none required** | `{}` is valid | **Confirm allowed** (if judge + other checks pass) |
| **Partial** — some required, some optional | Only required must be present | Optional can be omitted |

**How to test (after Stage 1):**

1. **Negative:** Compile an agent whose tool **requires** args but LLM leaves them empty → Confirm disabled, errors like `missing required: start, end`.
2. **Positive (if you have such a tool):** Tool with no required params → `{}` is OK to confirm.

**Pass criteria:**

- [ ] Cannot activate when **required** schema fields are missing
- [ ] **Can** activate when schema has no required fields and `{}` is valid
- [ ] UI shows **which** fields are missing (not a generic “empty arguments” error)

**Approved:** ☐  

---



## G7 — Probe approval


| Field    | Value                |
| -------- | -------------------- |
| **Type** | Stage 1 compile gate |


**How to test:** During Interpret, when agent wants a live Composio call, you see Accept/Reject before it runs.

**Pass criteria:**

- [ ] Probe card appears
- [ ] Reject → no probe run / clear message
- [ ] Accept → sample rows shown in plan review

**Approved:** ☐  

---



## G8 — Scheduled run (worker)


| Field    | Value          |
| -------- | -------------- |
| **Type** | Infrastructure |


**Setup:** Worker terminal running. Agent with 5-minute interval, active.

**Pass criteria:**

- [ ] New run appears in agent history within ~5–10 min **without** clicking Run now
- [ ] `trigger` is not `manual` in run history

**Approved:** ☐  

---



## Sign-off summary


| Test | Approved | Notes |
| ---- | -------- | ----- |
| G1   | ☐        |       |
| G2   | ☐        |       |
| G3   | ☐        |       |
| G4   | ☐        |       |
| G5   | ☐        |       |
| G6   | ☐        |       |
| G7   | ☐        |       |
| G8   | ☐        |       |


**All approved → Stage 0 golden matrix complete.**