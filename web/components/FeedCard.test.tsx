import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FeedCard } from "./FeedCard";
import type { FeedItem } from "@/lib/types";

const ITEM: FeedItem = {
  id: 1,
  channel: "feed",
  status: "sent",
  created_at: "2026-06-11T12:00:00+00:00",
  finding: {
    id: 7,
    agent_id: 1,
    run_id: 3,
    severity: "warning",
    state: "new",
    summary: "PO-4567 delayed 2 days due to customs hold",
    recommendation: "Contact Acme to confirm revised ETA",
    source_ref: "simship://PO-4567",
  },
};

describe("FeedCard", () => {
  it("shows summary, recommendation, severity, and a why-link to the run trace", () => {
    render(<FeedCard item={ITEM} />);
    expect(screen.getByText(/customs hold/)).toBeInTheDocument();
    expect(screen.getByText(/Contact Acme/)).toBeInTheDocument();
    expect(screen.getByText("warning")).toBeInTheDocument();
    const why = screen.getByRole("link", { name: /why did I get this/i });
    expect(why).toHaveAttribute("href", "/runs/3");
  });
});
