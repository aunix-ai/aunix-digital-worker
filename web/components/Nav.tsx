"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Agents" },
  { href: "/create", label: "New agent" },
  { href: "/feed", label: "Activity" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/agents");
  return pathname.startsWith(href);
}

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-4xl items-center gap-7 px-5">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid size-5 rotate-45 place-items-center rounded-[5px] bg-accent">
            <span className="size-1.5 -rotate-45 rounded-full bg-accent-ink" />
          </span>
          <span className="text-[0.95rem] font-semibold tracking-[-0.01em]">aunix</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {LINKS.map((l) => {
            const active = isActive(pathname, l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`relative px-2.5 py-1.5 transition-colors ${
                  active ? "text-ink" : "text-muted hover:text-ink"
                }`}
              >
                {l.label}
                {active && (
                  <span className="absolute inset-x-2.5 -bottom-[1.05rem] h-px bg-accent" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
