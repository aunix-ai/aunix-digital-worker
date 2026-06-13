import { defineConfig, devices } from "@playwright/test";

// E2E runs against a live stack (FastAPI on :8000, Next dev on E2E_BASE_URL).
// Start both before running: see web/e2e/README.md.
export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  timeout: 120_000,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3001",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
