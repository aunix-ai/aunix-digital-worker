"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AgentOut } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.listAgents().then(setAgents).catch((e) => setError(String(e)));
  }, []);
  useEffect(refresh, [refresh]);

  async function act(fn: () => Promise<unknown>) {
    try {
      await fn();
      refresh();
    } catch (e) {
      setError(String(e));
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!agents) return <p>Loading…</p>;
  if (agents.length === 0)
    return (
      <p className="text-slate-600">
        No agents yet. <Link href="/create" className="text-blue-600 underline">Create your first digital worker.</Link>
      </p>
    );

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Agents</h1>
      {agents.map((a) => (
        <div key={a.id} className="flex items-center justify-between rounded border bg-white p-4">
          <div>
            <Link href={`/agents/${a.id}`} className="font-medium hover:underline">{a.spec.name}</Link>
            <p className="text-sm text-slate-600">{a.spec.objective}</p>
            <p className="text-xs text-slate-500">
              {a.spec.task_type} · {a.spec.data_sources.join(", ")} · {a.spec.schedule.mode}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge value={a.status} />
            {a.status === "active" ? (
              <button onClick={() => act(() => api.pause(a.id))} className="rounded border px-2 py-1 text-sm">Pause</button>
            ) : (
              <button onClick={() => act(() => api.activate(a.id))} className="rounded border px-2 py-1 text-sm">Activate</button>
            )}
            <button onClick={() => act(() => api.runNow(a.id))} className="rounded bg-slate-900 px-2 py-1 text-sm text-white">Run now</button>
          </div>
        </div>
      ))}
    </div>
  );
}
