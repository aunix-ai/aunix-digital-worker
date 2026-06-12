"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AgentSpec } from "@/lib/types";
import { PlanSummary } from "@/components/PlanSummary";
import { Button, ErrorNote, PageTitle, Panel } from "@/components/ui";

const EXAMPLES = [
  "Watch all my active POs and alert me if delivery slips or tracking is silent for 48 hours.",
  "Analyze the daily sales report and send me the top 5 leads over $1M every morning at 8am.",
];

export default function CreatePage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [spec, setSpec] = useState<AgentSpec | null>(null);
  const [questions, setQuestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function compile() {
    setBusy(true);
    setError(null);
    setSpec(null);
    setQuestions([]);
    try {
      const result = await api.compile(text);
      setSpec(result.spec);
      setQuestions(result.questions);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!spec) return;
    setBusy(true);
    try {
      const agent = await api.createAgent("me", spec);
      await api.activate(agent.id);
      router.push("/");
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <PageTitle>New digital worker</PageTitle>
        <p className="mt-1.5 max-w-prose text-sm text-muted">
          Describe what to watch or analyze. Aunix interprets it into a structured agent and
          shows you the plan before anything runs.
        </p>
      </div>

      <div className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          spellCheck={false}
          className="w-full resize-y rounded-[var(--radius-panel)] border border-line bg-surface px-4 py-3 text-sm text-ink placeholder:text-faint transition-colors focus:border-line2"
          placeholder="e.g. Watch my active POs and alert me when a delivery date slips…"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={compile} variant="primary" disabled={busy || text.trim().length === 0}>
            {busy && !spec ? "Interpreting…" : "Interpret"}
          </Button>
          {!spec && !busy && (
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLES.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setText(ex)}
                  className="rounded-full border border-line px-3 py-1 text-xs text-muted transition-colors hover:border-line2 hover:text-ink"
                >
                  {i === 0 ? "Procurement example" : "Sales example"}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <ErrorNote message={error} />}

      {questions.length > 0 && (
        <Panel className="rise border-warn/35 p-5">
          <p className="text-sm font-medium text-warn">A bit more detail needed</p>
          <p className="mt-0.5 text-sm text-muted">
            Add these to your description and interpret again:
          </p>
          <ul className="mt-3 space-y-1.5">
            {questions.map((q, i) => (
              <li key={i} className="flex gap-2.5 text-sm text-ink">
                <span className="mt-2 size-1 shrink-0 rounded-full bg-warn" />
                {q}
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {spec && (
        <div className="rise space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted">
            <span className="size-1.5 rounded-full bg-accent" />
            Here&rsquo;s how Aunix understood it.
          </div>
          <PlanSummary spec={spec} />
          <div className="flex gap-2">
            <Button onClick={confirm} variant="primary" disabled={busy}>
              {busy ? "Activating…" : "Confirm & activate"}
            </Button>
            <Button onClick={() => setSpec(null)} disabled={busy}>
              Revise description
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
