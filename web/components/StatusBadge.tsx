const COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  paused: "bg-amber-100 text-amber-800",
  draft: "bg-slate-100 text-slate-600",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  new: "bg-red-100 text-red-800",
  ongoing: "bg-amber-100 text-amber-800",
  resolved: "bg-slate-100 text-slate-600",
};

export function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${COLORS[value] ?? "bg-slate-100 text-slate-600"}`}>
      {value}
    </span>
  );
}
