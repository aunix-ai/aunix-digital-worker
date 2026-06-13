"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ActionItem } from "@/lib/types";
import { ApprovalCard } from "@/components/ApprovalCard";
import { ErrorNote, PageTitle, Panel, SkeletonRows } from "@/components/ui";

export default function ApprovalsPage() {
  const [items, setItems] = useState<ActionItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const refresh = useCallback(() => {
    api.listActions("pending").then(setItems).catch((e) => setError(String(e)));
  }, []);
  useEffect(refresh, [refresh]);

  async function act(id: number, fn: () => Promise<unknown>) {
    setBusy(id); setError(null);
    try { await fn(); refresh(); } catch (e) { setError(String(e)); } finally { setBusy(null); }
  }

  return (
    <div className="space-y-6">
      <PageTitle>Approvals</PageTitle>
      {error && <ErrorNote message={error} />}
      {!items ? (
        <SkeletonRows count={3} />
      ) : items.length === 0 ? (
        <Panel className="px-6 py-14 text-center">
          <p className="text-ink">Nothing awaiting approval.</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
            When an L3 agent proposes an action, it lands here for you to review before it runs.
          </p>
        </Panel>
      ) : (
        <div className="space-y-3">
          {items.map((a) => (
            <ApprovalCard key={a.id} action={a} busy={busy === a.id}
                          onApprove={(params) => act(a.id, async () => {
                            const result = await api.approveAction(a.id, params);
                            if (result.status === "failed") {
                              setError(`Action failed: ${result.error ?? "unknown error"}`);
                            }
                          })}
                          onReject={() => act(a.id, () => api.rejectAction(a.id))} />
          ))}
        </div>
      )}
    </div>
  );
}
