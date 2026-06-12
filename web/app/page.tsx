"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AgentOut } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, ButtonLink, ErrorNote, PageTitle, Panel, SkeletonRows } from "@/components/ui";

function scheduleLabel(s: AgentOut["spec"]["schedule"]): string {
  if (s.mode === "interval") return `every ${s.interval_minutes}m`;
  if (s.mode === "daily") return `daily ${s.daily_time}`;
  return "on demand";
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);

  const refresh = useCallback(() => {
    api.listAgents().then(setAgents).catch((e) => setError(String(e)));
  }, []);
  useEffect(refresh, [refresh]);

  async function act(id: number, fn: () => Promise<unknown>) {
    setPending(id);
    setError(null);
    try {
      await fn();
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageTitle>Agents</PageTitle>
        <ButtonLink href="/create" variant="primary">
          <span className="text-base leading-none">+</span> New agent
        </ButtonLink>
      </div>

      {error && <ErrorNote message={error} />}

      {!agents ? (
        <SkeletonRows />
      ) : agents.length === 0 ? (
        <Panel className="px-6 py-14 text-center">
          <p className="text-ink">No digital workers yet.</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
            Describe what to watch or analyze in plain language, and Aunix compiles it into an
            autonomous agent that runs on a schedule.
          </p>
          <ButtonLink href="/create" variant="primary" className="mt-5">
            Create your first agent
          </ButtonLink>
        </Panel>
      ) : (
        <Panel className="divide-y divide-line overflow-hidden">
          {agents.map((a, i) => (
            <div
              key={a.id}
              className="rise flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-raise/60 sm:flex-row sm:items-center sm:gap-4"
              style={{ animationDelay: `${i * 45}ms` }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2.5">
                  <Link
                    href={`/agents/${a.id}`}
                    className="font-medium text-ink transition-colors hover:text-accent"
                  >
                    {a.spec.name}
                  </Link>
                  <StatusBadge value={a.status} />
                </div>
                <p className="mt-0.5 truncate text-sm text-muted">{a.spec.objective}</p>
                <p className="mt-1.5 font-mono text-xs tracking-[-0.005em] text-faint">
                  {a.spec.task_type} · {a.spec.data_sources.join(" + ")} ·{" "}
                  {scheduleLabel(a.spec.schedule)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {a.status === "active" ? (
                  <Button
                    onClick={() => act(a.id, () => api.pause(a.id))}
                    disabled={pending === a.id}
                  >
                    Pause
                  </Button>
                ) : (
                  <Button
                    onClick={() => act(a.id, () => api.activate(a.id))}
                    disabled={pending === a.id}
                  >
                    Activate
                  </Button>
                )}
                <Button
                  variant="primary"
                  onClick={() => act(a.id, () => api.runNow(a.id))}
                  disabled={pending === a.id}
                >
                  Run now
                </Button>
              </div>
            </div>
          ))}
        </Panel>
      )}
    </div>
  );
}
