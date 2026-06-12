import type { AgentSpec } from "@/lib/types";

function scheduleText(s: AgentSpec["schedule"]): string {
  if (s.mode === "interval") return `every ${s.interval_minutes} minutes`;
  if (s.mode === "daily") return `daily at ${s.daily_time}`;
  return "on demand";
}

const AUTONOMY: Record<number, string> = {
  1: "L1 — notify only",
  2: "L2 — notify and recommend actions",
};

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7.5rem_1fr] gap-x-4 px-5 py-3">
      <dt className="text-xs font-medium uppercase tracking-[0.06em] text-faint">{label}</dt>
      <dd className="text-sm text-ink">{children}</dd>
    </div>
  );
}

export function PlanSummary({ spec }: { spec: AgentSpec }) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
      <div className="border-b border-line px-5 py-4">
        <h2 className="font-medium text-ink">{spec.name}</h2>
        <p className="mt-0.5 text-sm text-muted">{spec.objective}</p>
      </div>
      <dl className="divide-y divide-line">
        <Row label="Type">{spec.task_type}</Row>
        <Row label="Sources">
          <span className="font-mono text-[0.8125rem] text-ink">
            {spec.data_sources.join(" + ")}
          </span>
        </Row>
        <Row label="Schedule">{scheduleText(spec.schedule)}</Row>

        {spec.task_type === "monitoring" && spec.conditions && (
          <Row label="Alert when">
            <span className="text-xs text-faint">match {spec.conditions.mode}</span>
            <ul className="mt-1.5 space-y-1">
              {spec.conditions.conditions.map((c, i) => (
                <li
                  key={i}
                  className="font-mono text-[0.8125rem] tracking-[-0.005em] text-warn"
                >
                  {`${c.field} ${c.operator} ${c.value}`}
                </li>
              ))}
            </ul>
          </Row>
        )}

        {spec.task_type === "analysis" && (
          <Row label="Briefing">
            <span className="font-mono text-[0.8125rem] text-ink">
              {`top ${spec.top_n} by ${spec.rank_by ?? "relevance"}`}
            </span>
          </Row>
        )}

        <Row label="Notify via">
          {spec.notifications.channels.join(", ")}
          {spec.notifications.email_to ? (
            <span className="text-muted"> ({spec.notifications.email_to})</span>
          ) : null}
        </Row>
        <Row label="Autonomy">{AUTONOMY[spec.autonomy_level] ?? `L${spec.autonomy_level}`}</Row>
      </dl>
    </div>
  );
}
