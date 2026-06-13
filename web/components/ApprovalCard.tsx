"use client";
import { useState } from "react";
import type { ActionItem } from "@/lib/types";
import { Button, Panel } from "@/components/ui";
import { StatusBadge } from "@/components/StatusBadge";

const TYPE_LABEL: Record<string, string> = {
  email: "Send email", hubspot: "Write to HubSpot", task: "Create task", resolve: "Resolve finding",
};

export function ApprovalCard({
  action, onApprove, onReject, busy,
}: {
  action: ActionItem;
  onApprove: (params: Record<string, unknown>) => void;
  onReject: () => void;
  busy?: boolean;
}) {
  const [params, setParams] = useState<Record<string, unknown>>(action.params);
  const set = (k: string, v: string) => setParams((p) => ({ ...p, [k]: v }));
  const field = (k: string) => (params[k] as string) ?? "";

  return (
    <Panel className="p-5">
      <div className="flex items-center justify-between">
        <p className="font-medium text-ink">
          {TYPE_LABEL[action.type] ?? action.type}
          {action.finding && (
            <span className="ml-2 font-mono text-xs text-faint">{action.finding.source_ref}</span>
          )}
        </p>
        <StatusBadge value={action.status} />
      </div>
      {action.finding && (
        <p className="mt-1 text-sm text-muted">{action.finding.summary}</p>
      )}

      <div className="mt-3 space-y-2">
        {action.type === "email" && (
          <>
            <input className="w-full rounded-md border border-line bg-bg px-3 py-2 text-sm text-ink"
                   value={field("to")} onChange={(e) => set("to", e.target.value)} placeholder="recipient" />
            <input className="w-full rounded-md border border-line bg-bg px-3 py-2 text-sm text-ink"
                   value={field("subject")} onChange={(e) => set("subject", e.target.value)} placeholder="subject" />
            <textarea className="w-full rounded-md border border-line bg-bg px-3 py-2 text-sm text-ink"
                      rows={4} value={field("body")} onChange={(e) => set("body", e.target.value)} />
          </>
        )}
        {action.type === "hubspot" && (
          <textarea className="w-full rounded-md border border-line bg-bg px-3 py-2 text-sm text-ink"
                    rows={3} value={field("note")} onChange={(e) => set("note", e.target.value)} />
        )}
        {action.type === "task" && (
          <input className="w-full rounded-md border border-line bg-bg px-3 py-2 text-sm text-ink"
                 value={field("title")} onChange={(e) => set("title", e.target.value)} />
        )}
        {action.type === "resolve" && (
          <p className="text-sm text-muted">Marks the finding resolved. No content to edit.</p>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Button variant="primary" disabled={busy} onClick={() => onApprove(params)}>Approve</Button>
        <Button disabled={busy} onClick={onReject}>Reject</Button>
        {action.expires_at && (
          <span className="ml-auto text-xs text-faint">
            expires {new Date(action.expires_at).toLocaleString()}
          </span>
        )}
      </div>
    </Panel>
  );
}
