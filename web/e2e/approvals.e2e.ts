import { execSync } from "node:child_process";
import path from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";

/**
 * End-to-end for L3 "execute with approval", driving the real UI against the
 * live FastAPI backend (which must run with AUNIX_ACTIONS_ENABLED=true).
 *
 * beforeAll triggers a procurement breach in the simulated ERP, then creates +
 * activates + runs an L3 agent (a `resolve` action — internal, no external API)
 * so exactly one action is queued for approval. The test then drives the
 * Approvals inbox in the browser: review the proposal and approve it, and
 * confirms via the API that the action executed and the queue is empty.
 */

const API = process.env.E2E_API_URL ?? "http://localhost:8000";
const REPO = path.resolve(__dirname, "..", "..");

const SPEC = {
  name: "po-resolver",
  objective: "Watch active POs and resolve handled delays",
  task_type: "monitoring",
  data_sources: ["simship"],
  record_key: "po_number",
  conditions: {
    mode: "any",
    conditions: [{ field: "delivery_date", operator: "gt", value: "expected_date" }],
  },
  schedule: { mode: "interval", interval_minutes: 30 },
  notifications: { channels: ["feed"] },
  autonomy_level: 3,
  actions: [{ type: "resolve" }],
  top_n: 5,
};

let agentId: number;

test.beforeAll(async ({ request }: { request: APIRequestContext }) => {
  // 1. trigger a delivery slip in the simulated ERP the backend reads
  execSync(
    `uv run python -c "from aunix.connectors.simship import SimShip; ` +
      `SimShip('data/simship.json').slip_delivery('PO-4567', days=2)"`,
    { cwd: REPO, stdio: "inherit" },
  );

  // 2. create + activate + run the L3 agent → one pending action
  const agent = await (await request.post(`${API}/agents`, { data: { owner: "e2e", spec: SPEC } })).json();
  agentId = agent.id;
  await request.post(`${API}/agents/${agentId}/activate`);
  const run = await (await request.post(`${API}/agents/${agentId}/run`)).json();
  expect(run.status).toBe("succeeded");
  expect(run.trace.actions.proposed).toBeGreaterThan(0);
});

test("review and approve a proposed action in the inbox", async ({ page, request }) => {
  const before = await (await request.get(`${API}/actions?status=pending`)).json();
  expect(before.length).toBeGreaterThan(0);

  await page.goto("/approvals");

  // the proposal is visible with its finding context and an Approve control
  await expect(page.getByText("Resolve finding").first()).toBeVisible();
  await expect(page.getByText(/PO-4567/).first()).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).first().click();

  // approving removes exactly one proposal from the pending queue, and it executes
  await expect
    .poll(async () => (await (await request.get(`${API}/actions?status=pending`)).json()).length)
    .toBe(before.length - 1);
  const executed = await (await request.get(`${API}/actions?status=executed`)).json();
  expect(executed.some((a: { type: string }) => a.type === "resolve")).toBe(true);

  await page.screenshot({ path: "/tmp/e2e-approvals.png", fullPage: true });
});
