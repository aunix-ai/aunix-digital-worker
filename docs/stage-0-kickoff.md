# Stage 0 Kickoff — Your action checklist

**Status:** Stage 1a implemented — Mastra compile agent + DW web wiring (golden tests G1–G8 next)  
**Owner:** You (review + sign-off)  
**Engineering:** Implements Stage 1 only after this is approved

Stage 0 has **no product code**. Your job is to review, customize, and sign off.

---

## What you do today (≈30–60 min)

### Step 1 — Verify your test environment

Run these **four** terminals when testing Stage 1:

```bash
# Terminal 1 — FlowOps compile API (NEW — port 3999)
cd ~/Desktop/Aunix/Newapproches/flowops
npm install   # if needed after pull
npm run dev

# Terminal 2 — DW Python API
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
cd ~/Desktop/Aunix/Newapproches/aunix-digital-worker
uv run uvicorn "aunix.api:create_default_app" --factory --reload

# Terminal 3 — DW Web
cd ~/Desktop/Aunix/Newapproches/aunix-digital-worker/web
npm run dev

# Terminal 4 — Worker (G8 scheduled runs)
cd ~/Desktop/Aunix/Newapproches/aunix-digital-worker
uv run python -m aunix.worker
```

Optional web env (`web/.env.local`):

```
NEXT_PUBLIC_FLOWOPS_COMPILE_URL=http://localhost:3999
```

**Check integrations:** open http://localhost:3000/integrations

| Toolkit | Required for | Your status (fill in) |
|---------|--------------|------------------------|
| Salesforce | G1, G3, G4 | ☐ Connected |
| QuickBooks | G2 | ☐ Connected |
| Gmail | G4 | ☐ Connected |
| HubSpot | Optional | ☐ |

**Check `.env` in `aunix-digital-worker`:**

| Variable | Required for | ☐ |
|----------|--------------|---|
| `COMPOSIO_API_KEY` | All Composio tests | |
| `COMPOSIO_USER_ID` | All Composio tests | |
| `OPENAI_API_KEY` | Compile / interpret | |
| `MAILGUN_API_KEY` + `MAILGUN_DOMAIN` | G2 email | |
| `AUNIX_API_CORS_ORIGINS` includes `http://localhost:3000` | Web → API | |

---

### Step 2 — Review golden tests (G1–G8)

Open **[stage-0-golden-tests.md](./stage-0-golden-tests.md)**.

For each test G1–G5:

1. Read the **prompt** you will paste in `/create`
2. Confirm it matches **your real data** (objects you can change in SF/QB)
3. Edit pass criteria if needed (e.g. your email address)
4. Mark ☐ → ☑ when the scenario description is approved

G6–G8 are **compile/infra** tests — approve as-is unless you want changes.

---

### Step 3 — Review “good plan” checklist

Open the plan doc section **0.2** in [stage-0-1-implementation-plan.md](./stage-0-1-implementation-plan.md).

Ask yourself: *Before I click Confirm, what must I see?*

Default list is fine for most teams. Add anything you care about, e.g.:

- [ ] Schedule matches what I asked (5 min vs 10 min)
- [ ] Email recipient is correct
- [ ] Autonomy level matches (L1 vs L3)

Reply with additions or write **“checklist approved”**.

---

### Step 4 — Sign off Stage 0

When Steps 1–3 are done, reply with:

```text
Stage 0 sign-off:
- Environment: OK / issues: ...
- Golden tests G1–G8: approved (with edits in stage-0-golden-tests.md)
- Pre-Confirm checklist: approved
- Ready for Stage 1: yes
```

That unlocks Stage 1 implementation (Mastra `digitalWorkerAgent` + DW web wiring).

---

## What you do NOT need to do in Stage 0

- ❌ Write code
- ❌ Run FlowOps
- ❌ Fix compile bugs (that’s Stage 1)
- ❌ Pass G1–G8 yet (those are **Stage 1 exit** tests)

You *may* try current `/create` + Run now to see baseline — expect compile gaps; that’s why Stage 1 exists.

---

## Optional: baseline smoke (5 min)

See where things stand **before** Stage 1:

1. http://localhost:3000/create  
2. Paste G1 prompt from golden tests  
3. Click Interpret → note what plan shows (tool, args, errors)  
4. Do **not** need this to pass for Stage 0 sign-off

---

## Timeline

| Day | You |
|-----|-----|
| **Today** | Steps 1–2 (env + review golden tests) |
| **Tomorrow** | Step 3–4 (checklist + sign-off) |
| **After sign-off** | Engineering starts Stage 1 |
