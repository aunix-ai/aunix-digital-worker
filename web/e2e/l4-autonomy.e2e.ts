import { execSync } from "node:child_process";
import path from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";

/**
 * End-to-end for L4 "autonomous within policy", driving the real UI against the
 * live FastAPI backend (which must run with AUNIX_ACTIONS_ENABLED=true).
 *
 * beforeAll triggers a procurement breach, then creates + activates + runs an L4
 * agent whose policy whitelists the `resolve` action. Unlike L3, the action must
 * auto-execute under policy WITHOUT ever entering the approval inbox. The test
 * confirms this on the run page (the action shows origin L4, a "policy auto"
 * badge, decided by policy, executed) and via the API.
 */

const API = process.env.E2E_API_URL ?? "http://localhost:8000";
const REPO = path.resolve(__dirname, "..", "..");

const SPEC = {
  name: "po-auto-resolver",
  objective: "Auto-resolve handled PO delays within policy",
  task_type: "monitoring",
  data_sources: ["simship"],
  record_key: "po_number",
  conditions: {
    mode: "any",
    conditions: [{ field: "delivery_date", operator: "gt", value: "expected_date" }],
  },
  schedule: { mode: "interval", interval_minutes: 30 },
  notifications: { channels: ["feed"] },
  autonomy_level: 4,
  actions: [{ type: "resolve" }],
  policy: { resolve_auto: true, per_run: 3, per_day: 20 },
  top_n: 5,
};

let runId: number;

test.beforeAll(async ({ request }: { request: APIRequestContext }) => {
  // 1. trigger a delivery slip in the simulated ERP the backend reads
  execSync(
    `uv run python -c "from aunix.connectors.simship import SimShip; ` +
      `SimShip('data/simship.json').slip_delivery('PO-4567', days=2)"`,
    { cwd: REPO, stdio: "inherit" },
  );

  // 2. create + activate + run the L4 agent → one auto-executed action
  const agent = await (await request.post(`${API}/agents`, { data: { owner: "e2e-l4", spec: SPEC } })).json();
  await request.post(`${API}/agents/${agent.id}/activate`);
  const run = await (await request.post(`${API}/agents/${agent.id}/run`)).json();
  expect(run.status).toBe("succeeded");
  expect(run.trace.actions.auto_executed).toBeGreaterThan(0);
  expect(run.trace.actions.queued).toBe(0); // nothing needed a human
  runId = run.id;
});

test("L4 auto-executes a policy-whitelisted action without human approval", async ({ page, request }) => {
  // it never entered the approval inbox — the policy gate auto-approved it
  await page.goto(`/runs/${runId}`);
  await expect(page.getByText(/policy\s+auto/i).first()).toBeVisible();
  await expect(page.getByText("decided by policy").first()).toBeVisible();

  // and the API agrees: an L4 resolve action executed under policy
  const executed = await (await request.get(`${API}/actions?status=executed`)).json();
  expect(
    executed.some(
      (a: { type: string; origin: string; policy_decision: string; decided_by: string }) =>
        a.type === "resolve" && a.origin === "L4" && a.policy_decision === "auto" && a.decided_by === "policy",
    ),
  ).toBe(true);

  await page.screenshot({ path: "/tmp/e2e-l4.png", fullPage: true });
});
