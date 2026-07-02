import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PlanSummary } from "./PlanSummary";
import type { AgentSpec } from "@/lib/types";

const SPEC: AgentSpec = {
  name: "po-watcher",
  objective: "Watch active POs and alert on delays",
  task_type: "monitoring",
  data_sources: ["simship"],
  record_key: "po_number",
  conditions: {
    mode: "any",
    conditions: [
      { field: "delivery_date", operator: "gt", value: "expected_date" },
      { field: "last_tracking_update", operator: "stale_hours", value: 48 },
    ],
  },
  schedule: { mode: "interval", interval_minutes: 30 },
  notifications: { channels: ["feed", "email"], email_to: "david@example.com" },
  autonomy_level: 1,
  top_n: 5,
};

describe("PlanSummary", () => {
  it("renders the interpreted plan in plain language", () => {
    render(<PlanSummary spec={SPEC} />);
    expect(screen.getByText("po-watcher")).toBeInTheDocument();
    expect(screen.getByText(/every 30 minutes/i)).toBeInTheDocument();
    expect(screen.getByText(/delivery_date gt expected_date/)).toBeInTheDocument();
    expect(screen.getByText(/last_tracking_update stale_hours 48/)).toBeInTheDocument();
    expect(screen.getByText(/feed, email/)).toBeInTheDocument();
    expect(screen.getByText(/notify only/i)).toBeInTheDocument();
  });

  it("renders composio sources with toolkit and tool slug", () => {
    render(
      <PlanSummary
        spec={{
          ...SPEC,
          data_sources: [
            {
              type: "composio",
              toolkit: "salesforce",
              tool_slug: "SALESFORCE_QUERY_OPPORTUNITIES",
              arguments: { limit: 50 },
              record_key: "Id",
            },
          ],
        }}
      />,
    );
    expect(screen.getByText(/salesforce → SALESFORCE_QUERY_OPPORTUNITIES/i)).toBeInTheDocument();
    expect(screen.getByText(/arguments: \{"limit":50\}/)).toBeInTheDocument();
    expect(screen.queryByText(/\[object Object\]/i)).not.toBeInTheDocument();
  });

  it("describes analysis agents by ranking instead of conditions", () => {
    render(
      <PlanSummary
        spec={{ ...SPEC, task_type: "analysis", conditions: null, rank_by: "deal_size", top_n: 5,
                schedule: { mode: "daily", daily_time: "08:00" } }}
      />,
    );
    expect(screen.getByText(/top 5 by deal_size/i)).toBeInTheDocument();
    expect(screen.getByText(/daily at 08:00/i)).toBeInTheDocument();
  });
});
