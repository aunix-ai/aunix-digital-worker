"use client";
import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AgentOut, RunOut } from "@/lib/types";
import { PlanSummary } from "@/components/PlanSummary";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, ErrorNote, Panel, SectionLabel, SkeletonRows } from "@/components/ui";

export default function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const agentId = Number(id);
  const [agent, setAgent] = useState<AgentOut | null>(null);
  const [runs, setRuns] = useState<RunOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(() => {
    api.getAgent(agentId).then(setAgent).catch((e) => setError(String(e)));
    api.listRuns(agentId).then(setRuns).catch(() => {});
  }, [agentId]);
  useEffect(refresh, [refresh]);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !agent) return <ErrorNote message={error} />;
  if (!agent) return <SkeletonRows count={2} />;

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/"
          className="text-xs text-faint transition-colors hover:text-muted"
        >
          ← Agents
        </Link>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <h1 className="flex flex-wrap items-center gap-x-3 gap-y-2 text-2xl font-semibold tracking-[-0.01em] text-ink">
            {agent.spec.name}
            <StatusBadge value={agent.status} />
          </h1>
          <div className="flex shrink-0 gap-2">
            {agent.status === "active" ? (
              <Button onClick={() => act(() => api.pause(agentId))} disabled={busy}>
                Pause
              </Button>
            ) : (
              <Button onClick={() => act(() => api.activate(agentId))} disabled={busy}>
                Activate
              </Button>
            )}
            <Button variant="primary" onClick={() => act(() => api.runNow(agentId))} disabled={busy}>
              Run now
            </Button>
          </div>
        </div>
      </div>

      {error && <ErrorNote message={error} />}

      <PlanSummary spec={agent.spec} />

      <section className="space-y-3">
        <SectionLabel>Run history</SectionLabel>
        {runs.length === 0 ? (
          <Panel className="px-5 py-8 text-center text-sm text-muted">
            No runs yet. Use{" "}
            <span className="text-ink">Run now</span> to execute this agent on demand.
          </Panel>
        ) : (
          <Panel className="divide-y divide-line overflow-hidden">
            {runs.map((r) => (
              <Link
                key={r.id}
                href={`/runs/${r.id}`}
                className="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-5 py-3.5 text-sm transition-colors hover:bg-raise/60"
              >
                <span className="whitespace-nowrap font-mono text-ink">run #{r.id}</span>
                <span className="text-faint">{r.trigger}</span>
                {r.started_at && (
                  <span className="hidden text-faint sm:inline">
                    {new Date(r.started_at).toLocaleString()}
                  </span>
                )}
                <span className="ml-auto flex items-center gap-3">
                  {r.trace.findings && (
                    <span className="font-mono text-xs text-faint">
                      {r.trace.findings.new} new / {r.trace.findings.ongoing} ongoing
                    </span>
                  )}
                  <StatusBadge value={r.status} />
                </span>
              </Link>
            ))}
          </Panel>
        )}
      </section>
    </div>
  );
}
