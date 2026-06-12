# Design

## Theme

Operations console — dark, dense, instrument-grade. A deep blue-slate surface, hairline
borders, one cyan signal accent, and mono-set operational data. Calm when healthy; severity
colors are the only loud thing on the screen, and only when something is wrong.

## Color (OKLCH)

Defined as Tailwind v4 `@theme` tokens in `app/globals.css`.

| Role | Token | Value | Use |
|---|---|---|---|
| Base bg | `--color-bg` | `oklch(0.17 0.013 248)` | app background |
| Surface | `--color-surface` | `oklch(0.205 0.015 248)` | panels, cards |
| Raised | `--color-raise` | `oklch(0.245 0.016 248)` | hover, inputs |
| Line | `--color-line` | `oklch(0.32 0.016 248)` | hairline borders |
| Line strong | `--color-line2` | `oklch(0.40 0.018 248)` | emphasized borders |
| Ink | `--color-ink` | `oklch(0.97 0.004 248)` | primary text |
| Muted | `--color-muted` | `oklch(0.74 0.012 248)` | secondary text (≥4.5:1) |
| Faint | `--color-faint` | `oklch(0.60 0.012 248)` | tertiary, disabled |
| Accent | `--color-accent` | `oklch(0.80 0.125 200)` | actions, active, focus, links |
| Accent ink | `--color-accent-ink` | `oklch(0.20 0.02 220)` | text on accent fills |
| Warning | `--color-warn` | `oklch(0.83 0.13 78)` | severity: warning |
| Critical | `--color-crit` | `oklch(0.70 0.19 22)` | severity: critical / failed |
| Success | `--color-ok` | `oklch(0.80 0.14 158)` | severity: ok / succeeded |

Severity chips: a 15% tint of the severity hue as background, the full severity color as text.
Never a full-saturation fill. Status is always color **plus** a dot **plus** a text label.

Strategy: **Restrained** — tinted-neutral surfaces + one cyan accent. Severity is the only
committed color, and it appears only on events.

## Typography

One sans (Geist Sans) for all UI; one mono (Geist Mono) for operational data — record IDs,
keys, timestamps, thresholds, numeric values, and the trace JSON. The mono/sans split is the
console's signature: data is visibly data. Fixed rem scale, ratio ~1.2.

- Display / page title: 1.5rem, weight 600, tracking -0.01em
- Section heading: 0.8125rem, weight 600, uppercase, tracking 0.08em, muted (one deliberate
  system label — used for panel headers, not as a per-section eyebrow)
- Body: 0.875rem / 1.5
- Data / mono: 0.8125rem, `--font-mono`, tracking -0.005em
- Micro: 0.75rem muted (meta lines)

## Components

- **App shell**: sticky top bar, brand diamond mark + wordmark, nav links with an active
  underline indicator. Max-width 64rem content column on a subtle dotted-grid background.
- **Panel**: `--color-surface`, 1px `--color-line`, radius 0.625rem. No nested panels.
- **StatusBadge**: pill, leading dot, label. Color by status (active/paused/draft,
  succeeded/failed, new/ongoing/resolved). Active dot has a soft pulse (reduced-motion: none).
- **Button**: primary (cyan fill, dark ink), ghost (1px line, hover raises), danger (crit text).
  All have hover / focus-visible ring / active / disabled.
- **SeverityRow** (feed): leading severity dot, mono record id, summary; recommendation and a
  "why →" trace link below. No side-stripe borders.
- **Trace view**: definition grid for the run trace; findings as panels with a collapsible
  mono JSON "data evaluated" block.
- **Empty / loading**: empty states teach the next action; loading uses skeleton rows, not spinners.

## Motion

150–220 ms, ease-out. Hover/focus state transitions, list items fade-up with a small stagger
on first paint, active status dot pulses. `@media (prefers-reduced-motion: reduce)` removes the
stagger and pulse and keeps instant state changes. No page-load choreography.
