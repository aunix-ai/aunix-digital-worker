"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AgentSpec, ClarifyingQuestion } from "@/lib/types";
import { PlanSummary } from "@/components/PlanSummary";
import { Button, ErrorNote, PageTitle, Panel } from "@/components/ui";

const EXAMPLES = [
  "Watch all my active POs and alert me if delivery slips or tracking is silent for 48 hours.",
  "Analyze the daily sales report and send me the top 5 leads over $1M every morning at 8am.",
];

export default function CreatePage() {
  const router = useRouter();
  const [text, setText] = useState("");
  // answer lines accumulated across clarifying rounds, folded back into the prompt
  const [history, setHistory] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [spec, setSpec] = useState<AgentSpec | null>(null);
  const [questions, setQuestions] = useState<ClarifyingQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function interpret(baseHistory: string[], extraLines: string[]) {
    setBusy(true);
    setError(null);
    setSpec(null);
    setQuestions([]);
    const all = [...baseHistory, ...extraLines];
    const prompt = all.length ? `${text}\n\nAdditional details:\n${all.join("\n")}` : text;
    try {
      const result = await api.compile(prompt);
      setHistory(all);
      setSpec(result.spec);
      setQuestions(result.questions);
      setAnswers({});
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function answerLines(): string[] {
    return questions
      .map((q) => {
        const a = answers[q.text]?.trim();
        return a ? `- ${q.text} ${a}` : null;
      })
      .filter((x): x is string => x !== null);
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

  const answeredCount = answerLines().length;

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
          <Button
            onClick={() => interpret([], [])}
            variant="primary"
            disabled={busy || text.trim().length === 0}
          >
            {busy ? "Interpreting…" : "Interpret"}
          </Button>
          {!spec && questions.length === 0 && !busy && (
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
        <Panel className="rise overflow-hidden">
          <div className="flex items-center gap-2 border-b border-line px-5 py-3.5">
            <span className="size-1.5 rounded-full bg-warn" />
            <p className="text-sm font-medium text-ink">A few details to pin down</p>
          </div>
          <div className="divide-y divide-line">
            {questions.map((q) => (
              <fieldset key={q.text} className="px-5 py-4">
                <legend className="text-sm text-ink">{q.text}</legend>
                <div className="mt-2.5">
                  {q.choices.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {q.choices.map((choice) => {
                        const selected = answers[q.text] === choice;
                        return (
                          <button
                            key={choice}
                            type="button"
                            aria-pressed={selected}
                            onClick={() =>
                              setAnswers((a) => ({ ...a, [q.text]: choice }))
                            }
                            className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                              selected
                                ? "border-accent bg-accent/12 text-accent"
                                : "border-line text-muted hover:border-line2 hover:text-ink"
                            }`}
                          >
                            {choice}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <input
                      type={q.kind === "email" ? "email" : "text"}
                      value={answers[q.text] ?? ""}
                      onChange={(e) =>
                        setAnswers((a) => ({ ...a, [q.text]: e.target.value }))
                      }
                      placeholder={q.kind === "email" ? "name@company.com" : "Your answer"}
                      className="w-full max-w-md rounded-md border border-line bg-bg px-3 py-2 text-sm text-ink placeholder:text-faint transition-colors focus:border-line2"
                    />
                  )}
                </div>
              </fieldset>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-line px-5 py-4">
            <Button onClick={() => interpret(history, answerLines())} variant="primary" disabled={busy}>
              {busy ? "Interpreting…" : "Interpret with answers"}
            </Button>
            <span className="text-xs text-faint">
              {answeredCount > 0
                ? `${answeredCount} of ${questions.length} answered`
                : "Answer what you can — Aunix fills sensible defaults for the rest."}
            </span>
          </div>
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
