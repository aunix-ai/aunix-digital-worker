import Link from "next/link";
import type { FeedItem } from "@/lib/types";

const SEVERITY: Record<string, { dot: string; text: string }> = {
  critical: { dot: "bg-crit", text: "text-crit" },
  warning: { dot: "bg-warn", text: "text-warn" },
  info: { dot: "bg-accent", text: "text-accent" },
};

function recordId(sourceRef: string): string {
  const tail = sourceRef.split("://").pop();
  return tail && tail.length ? tail : sourceRef;
}

export function FeedCard({ item }: { item: FeedItem }) {
  const f = item.finding;
  const sev = SEVERITY[f.severity] ?? { dot: "bg-faint", text: "text-muted" };
  return (
    <div className="rounded-[var(--radius-panel)] border border-line bg-surface p-5 transition-colors hover:border-line2">
      <div className="flex items-start gap-3">
        <span
          className={`mt-1.5 size-2 shrink-0 rounded-full ${sev.dot}`}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-[0.8125rem] font-medium text-ink">
              {recordId(f.source_ref)}
            </span>
            <span
              className={`text-[0.6875rem] font-semibold uppercase tracking-[0.06em] ${sev.text}`}
            >
              {f.severity}
            </span>
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-ink text-pretty">{f.summary}</p>
          <p className="mt-2 text-sm leading-relaxed text-muted text-pretty">
            <span className="font-medium text-ink/80">Recommended.</span> {f.recommendation}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-faint">
            <span className="font-mono">{f.source_ref}</span>
            <span aria-hidden>·</span>
            <span>via {item.channel}</span>
            {item.created_at && (
              <>
                <span aria-hidden>·</span>
                <time dateTime={item.created_at}>
                  {new Date(item.created_at).toLocaleString()}
                </time>
              </>
            )}
            <Link
              href={`/runs/${f.run_id}`}
              className="ml-auto font-medium text-accent transition-colors hover:text-accent-hi"
            >
              Why did I get this? →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
