import type { AgentSpec, ComposioSource, DataSourceRef, ValidationReport } from "@/lib/types";

function scheduleText(s: AgentSpec["schedule"]): string {
  if (s.mode === "interval") return `every ${s.interval_minutes} minutes`;
  if (s.mode === "daily") return `daily at ${s.daily_time}`;
  return "on demand";
}

const AUTONOMY: Record<number, string> = {
  1: "L1 — notify only",
  2: "L2 — notify and recommend actions",
  3: "L3 — execute with your approval",
  4: "L4 — autonomous within policy",
};

function isComposioSource(ref: DataSourceRef): ref is ComposioSource {
  return typeof ref === "object" && ref !== null && ref.type === "composio";
}

function formatArguments(args?: Record<string, unknown> | string): string {
  if (args == null) return "{}";
  if (typeof args === "string") return args.trim() || "{}";
  if (Object.keys(args).length === 0) return "{}";
  return JSON.stringify(args);
}

function formatSourceLabel(ref: DataSourceRef): string {
  if (typeof ref === "string") return ref;
  return `${ref.toolkit} → ${ref.tool_slug}`;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7.5rem_1fr] gap-x-4 px-5 py-3">
      <dt className="text-xs font-medium uppercase tracking-[0.06em] text-faint">{label}</dt>
      <dd className="text-sm text-ink">{children}</dd>
    </div>
  );
}

export function PlanSummary({
  spec,
  probeRows,
  validation,
}: {
  spec: AgentSpec;
  probeRows?: unknown[];
  validation?: ValidationReport;
}) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
      <div className="border-b border-line px-5 py-4">
        <h2 className="font-medium text-ink">{spec.name}</h2>
        <p className="mt-0.5 text-sm text-muted">{spec.objective}</p>
      </div>
      <dl className="divide-y divide-line">
        <Row label="Type">{spec.task_type}</Row>
        <Row label="Sources">
          <ul className="space-y-2">
            {spec.data_sources.map((source, index) => (
              <li key={index}>
                {isComposioSource(source) ? (
                  <div className="space-y-1">
                    <div className="font-mono text-[0.8125rem] text-accent">
                      {formatSourceLabel(source)}
                    </div>
                    <div className="text-xs text-muted">
                      Composio tool · record key: {source.record_key ?? "id"}
                    </div>
                    <div className="font-mono text-[0.75rem] text-faint">
                      arguments: {formatArguments(source.arguments)}
                    </div>
                  </div>
                ) : (
                  <span className="font-mono text-[0.8125rem] text-ink">{source}</span>
                )}
              </li>
            ))}
          </ul>
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
          ) : spec.notifications.channels.includes("email") ? (
            <span className="text-warn"> (email address missing)</span>
          ) : null}
        </Row>
        <Row label="Autonomy">{AUTONOMY[spec.autonomy_level] ?? `L${spec.autonomy_level}`}</Row>

        {spec.actions && spec.actions.length > 0 && (
          <Row label="Actions">
            <ul className="space-y-1 font-mono text-[0.8125rem]">
              {spec.actions.map((a, i) => (
                <li key={i}>{a.type}{a.tool_slug ? ` → ${a.tool_slug}` : ""}</li>
              ))}
            </ul>
          </Row>
        )}

        {spec.policy && (
          <Row label="L4 policy">
            <span className="font-mono text-[0.75rem] text-faint">
              {JSON.stringify(spec.policy)}
            </span>
          </Row>
        )}

        {validation && !validation.passed && validation.errors.length > 0 && (
          <Row label="Validation">
            <ul className="space-y-1 text-xs text-warn">
              {validation.errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </Row>
        )}

        {probeRows && probeRows.length > 0 && (
          <Row label="Probe sample">
            <pre className="max-h-40 overflow-auto font-mono text-[0.7rem] text-faint">
              {JSON.stringify(probeRows.slice(0, 3), null, 2)}
            </pre>
          </Row>
        )}
      </dl>
    </div>
  );
}
