"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunOut } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorNote, Panel, SectionLabel, SkeletonRows } from "@/components/ui";

function TraceRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-x-4 px-5 py-3">
      <dt className="text-xs font-medium uppercase tracking-[0.06em] text-faint">{label}</dt>
      <dd className="text-sm text-ink">{children}</dd>
    </div>
  );
}

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<RunOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRun(Number(id)).then(setRun).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <ErrorNote message={error} />;
  if (!run) return <SkeletonRows count={3} />;

  const breaches = run.trace.breaches ?? [];
  const fc = run.trace.findings;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <h1 className="font-mono text-xl font-semibold tracking-[-0.01em] text-ink">
            run #{run.id}
          </h1>
          <StatusBadge value={run.status} />
        </div>
        <p className="text-sm text-faint">
          {run.trigger} trigger
          {run.started_at && (
            <> · {new Date(run.started_at).toLocaleString()}</>
          )}{" "}
          ·{" "}
          <Link
            href={`/agents/${run.agent_id}`}
            className="text-accent transition-colors hover:text-accent-hi"
          >
            agent #{run.agent_id}
          </Link>
        </p>
      </div>

      {run.error && (
        <Panel className="border-crit/40 p-4">
          <p className="font-mono text-xs uppercase tracking-wide text-crit">run failed</p>
          <p className="mt-1 text-sm text-ink/90">{run.error}</p>
        </Panel>
      )}

      <section className="space-y-3">
        <SectionLabel>Decision trace</SectionLabel>
        <Panel className="divide-y divide-line">
          <TraceRow label="Rows evaluated">
            <span className="font-mono">{run.trace.rows_fetched ?? "—"}</span>
          </TraceRow>
          <TraceRow label="Breaches">
            {breaches.length ? (
              <span className="flex flex-wrap gap-1.5">
                {breaches.map((b) => (
                  <span
                    key={b}
                    className="rounded bg-raise px-1.5 py-0.5 font-mono text-xs text-warn"
                  >
                    {b}
                  </span>
                ))}
              </span>
            ) : (
              <span className="text-muted">none</span>
            )}
          </TraceRow>
          <TraceRow label="Findings">
            {fc ? (
              <span className="font-mono text-sm">
                <span className="text-accent">{fc.new} new</span>
                <span className="text-faint"> · </span>
                <span className="text-warn">{fc.ongoing} ongoing</span>
                <span className="text-faint"> · </span>
                <span className="text-muted">{fc.resolved} resolved</span>
              </span>
            ) : (
              "—"
            )}
          </TraceRow>
        </Panel>
      </section>

      {(run.findings ?? []).length > 0 && (
        <section className="space-y-3">
          <SectionLabel>Findings</SectionLabel>
          <div className="space-y-3">
            {(run.findings ?? []).map((f) => (
              <Panel key={f.id} className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm leading-relaxed text-ink text-pretty">{f.summary}</p>
                  <StatusBadge value={f.state} />
                </div>
                <p className="mt-2 text-sm text-muted text-pretty">{f.recommendation}</p>
                <p className="mt-2 font-mono text-xs text-faint">
                  {f.dedupe_key} · {f.source_ref}
                </p>
                {f.details && (
                  <details className="group mt-3">
                    <summary className="inline-flex cursor-pointer select-none items-center gap-1 text-xs text-muted transition-colors hover:text-ink">
                      <span className="transition-transform group-open:rotate-90">▸</span>
                      Data evaluated
                    </summary>
                    <pre className="mt-2 overflow-auto rounded-md border border-line bg-bg p-3 font-mono text-xs leading-relaxed text-muted">
                      {JSON.stringify(f.details, null, 2)}
                    </pre>
                  </details>
                )}
              </Panel>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
