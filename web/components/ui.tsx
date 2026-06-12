import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps, ReactNode } from "react";

type Variant = "primary" | "ghost" | "danger";

const BASE =
  "inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-[background-color,border-color,opacity] duration-150 disabled:pointer-events-none disabled:opacity-40";

const BTN: Record<Variant, string> = {
  primary: "bg-accent text-accent-ink hover:bg-accent-hi shadow-[0_1px_0_oklch(1_0_0/0.12)_inset]",
  ghost: "border border-line text-ink hover:bg-raise hover:border-line2",
  danger: "border border-line text-crit hover:bg-raise hover:border-crit/60",
};

export function Button({
  variant = "ghost",
  className = "",
  children,
  ...props
}: { variant?: Variant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button {...props} className={`${BASE} ${BTN[variant]} ${className}`}>
      {children}
    </button>
  );
}

export function ButtonLink({
  variant = "ghost",
  className = "",
  children,
  ...props
}: { variant?: Variant } & ComponentProps<typeof Link>) {
  return (
    <Link {...props} className={`${BASE} ${BTN[variant]} ${className}`}>
      {children}
    </Link>
  );
}

export function Panel({
  className = "",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-[var(--radius-panel)] border border-line bg-surface ${className}`}
    >
      {children}
    </div>
  );
}

/** One deliberate system label for panel/section headers (not a per-section eyebrow). */
export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-[0.8125rem] font-semibold uppercase tracking-[0.08em] text-muted">
      {children}
    </h2>
  );
}

export function PageTitle({ children }: { children: ReactNode }) {
  return (
    <h1 className="text-2xl font-semibold tracking-[-0.01em] text-ink text-balance">
      {children}
    </h1>
  );
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-[4.5rem] animate-pulse rounded-[var(--radius-panel)] border border-line bg-surface"
        />
      ))}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <Panel className="border-crit/40 p-4">
      <p className="text-sm text-crit">
        <span className="font-mono text-xs uppercase tracking-wide">error</span>{" "}
        <span className="text-ink/90">{message}</span>
      </p>
    </Panel>
  );
}
