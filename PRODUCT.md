# Product

## Register

product

## Users

Enterprise operators — buyers, sales reps, ops managers, finance analysts — who delegate
repetitive monitoring and report-analysis to autonomous "digital worker" agents. They are
in a watching/triage workflow: scanning for what changed, why it matters, and what to do.
Often this surface is left open through the workday like a console.

## Product Purpose

Aunix turns standing operational vigilance into autonomous agents. An operator describes an
intent in plain language; the system compiles it to a structured agent that monitors data
sources on a schedule, evaluates conditions deterministically, narrates findings with an LLM,
and alerts exactly once per issue. The UI is the operator's command surface: create agents,
watch the activity feed, and answer "why did I get this alert?" by drilling into the run trace.

## Brand Personality

Vigilant, precise, calm under load. The voice of a competent operations teammate, not a
chatbot. Three words: **instrument-grade, trustworthy, unhurried.** It should feel like a
serious monitoring console you'd trust to watch your operations overnight.

## Anti-references

- Generic SaaS-cream / warm-editorial AI aesthetic (cream bg, serif display, terracotta).
- Bouncy, playful, over-animated dashboards. This watches money and shipments.
- Loud full-saturation status fills that turn the screen into a stoplight.
- Chatbot framing (speech bubbles, avatars, "Hi! I'm your AI assistant").

## Design Principles

1. **Data is the hero.** IDs, timestamps, thresholds, and traces are first-class — set in
   mono, never buried. The interface recedes; the operational facts come forward.
2. **Earned familiarity.** Behave like Linear/Stripe/Grafana: standard affordances, no
   invented controls. The operator should trust it on sight.
3. **Signal over decoration.** Color means state (severity, active, focus), never garnish.
   One accent carries actions and attention.
4. **Explain every alert.** Transparency is the product. Every finding links to the run that
   produced it and the data it evaluated.
5. **Quiet by default, sharp on event.** A healthy system is calm; a breach is unmissable.

## Accessibility & Inclusion

WCAG 2.1 AA. Body text ≥4.5:1 on the dark surface; severity never encoded by color alone
(always paired with a label/dot and text). Full keyboard operability, visible focus rings,
and a `prefers-reduced-motion` path for every animation.
