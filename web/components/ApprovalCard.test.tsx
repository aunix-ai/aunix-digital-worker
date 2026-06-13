import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApprovalCard } from "./ApprovalCard";
import type { ActionItem } from "@/lib/types";

const ACTION: ActionItem = {
  id: 1, agent_id: 1, run_id: 3, finding_id: 7, type: "email",
  params: { to: "orders@acme.com", subject: "Re PO-4567", body: "Hi" },
  status: "pending", origin: "L3", result: {}, error: null,
  created_at: "2026-06-12T12:00:00+00:00", expires_at: "2026-06-13T12:00:00+00:00",
  finding: { id: 7, summary: "PO-4567 delayed 2 days", recommendation: "Contact supplier",
             source_ref: "simship://PO-4567", severity: "warning" },
};

describe("ApprovalCard", () => {
  it("shows the finding, drafted action, and approve/reject", () => {
    render(<ApprovalCard action={ACTION} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByText(/PO-4567 delayed/)).toBeInTheDocument();
    expect(screen.getByDisplayValue("orders@acme.com")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Re PO-4567")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
  });
});
