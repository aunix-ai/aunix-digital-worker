type Tone = "ok" | "warn" | "crit" | "accent" | "muted";

// Status string → semantic tone. Covers agent lifecycle, run status, and finding state.
const TONE: Record<string, Tone> = {
  active: "ok",
  paused: "warn",
  draft: "muted",
  succeeded: "ok",
  running: "accent",
  failed: "crit",
  new: "accent",
  ongoing: "warn",
  resolved: "muted",
};

const STYLE: Record<Tone, { chip: string; dot: string }> = {
  ok: { chip: "bg-ok/12 text-ok", dot: "bg-ok" },
  warn: { chip: "bg-warn/12 text-warn", dot: "bg-warn" },
  crit: { chip: "bg-crit/15 text-crit", dot: "bg-crit" },
  accent: { chip: "bg-accent/12 text-accent", dot: "bg-accent" },
  muted: { chip: "bg-raise text-muted", dot: "bg-faint" },
};

export function StatusBadge({ value }: { value: string }) {
  const tone = TONE[value] ?? "muted";
  const s = STYLE[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.chip}`}
    >
      <span
        className={`size-1.5 rounded-full text-current ${s.dot} ${value === "active" ? "pulse-ring" : ""}`}
      />
      {value}
    </span>
  );
}
