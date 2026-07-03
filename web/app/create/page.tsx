"use client";
import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { bffApi, isBffEnabled } from "@/lib/bff-api";
import {
  flowopsCompile,
  type ComposioExecApprovalPayload,
  type UserQuestionPayload,
} from "@/lib/flowops-compile";
import type {
  AgentSpec,
  CompileResult,
  CompileSessionStatus,
  JudgeVerdict,
  ValidationReport,
} from "@/lib/types";
import { PlanSummary } from "@/components/PlanSummary";
import { Button, ErrorNote, PageTitle, Panel } from "@/components/ui";

const EXAMPLES = [
  "Watch all my active POs and alert me if delivery slips or tracking is silent for 48 hours.",
  "Analyze the daily sales report and send me the top 5 leads over $1M every morning at 8am.",
];

const STATUS_LABEL: Record<CompileSessionStatus, string> = {
  interpreting: "Interpreting your request…",
  validating: "Validating plan…",
  awaiting_probe_approval: "Waiting for probe approval…",
  probing: "Running sample fetch…",
  judging: "Reviewing plan quality…",
  awaiting_confirmation: "Ready to confirm",
  failed: "Plan needs revision",
};

function ValidationChecklist({
  validation,
  judge,
}: {
  validation?: ValidationReport;
  judge?: JudgeVerdict;
}) {
  if (!validation && !judge) return null;
  return (
    <Panel className="px-5 py-4 text-sm">
      <p className="font-medium text-ink">Pre-confirm checklist</p>
      <ul className="mt-2 space-y-1 text-xs">
        <li className={validation?.passed ? "text-accent" : "text-warn"}>
          {validation?.passed ? "✓" : "✗"} Schema validation
          {validation?.errors?.length ? ` — ${validation.errors.join("; ")}` : ""}
        </li>
        {validation?.warnings?.map((w) => (
          <li key={w} className="text-muted">
            ⚠ {w}
          </li>
        ))}
        <li
          className={
            judge?.verdict === "pass" ? "text-accent" : judge ? "text-warn" : "text-faint"
          }
        >
          {judge?.verdict === "pass" ? "✓" : judge ? "✗" : "…"} LLM judge
          {judge?.issues?.length ? ` — ${judge.issues.join("; ")}` : ""}
        </li>
      </ul>
    </Panel>
  );
}

export default function CreatePage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [isCompiling, setIsCompiling] = useState(false);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [status, setStatus] = useState<CompileSessionStatus | null>(null);
  const [lastTool, setLastTool] = useState<string | null>(null);
  const [spec, setSpec] = useState<AgentSpec | null>(null);
  const [compileMeta, setCompileMeta] = useState<CompileResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingProbe, setPendingProbe] = useState<ComposioExecApprovalPayload | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<UserQuestionPayload | null>(null);
  const [questionAnswer, setQuestionAnswer] = useState("");
  const sessionIdRef = useRef<string | null>(null);

  const canConfirm =
    Boolean(spec) &&
    compileMeta?.validation_report?.passed === true &&
    compileMeta?.judge?.verdict === "pass" &&
    compileMeta?.status === "awaiting_confirmation";

  const runCompile = useCallback(async (prompt: string) => {
    setIsCompiling(true);
    setError(null);
    setSpec(null);
    setCompileMeta(null);
    setPendingProbe(null);
    setPendingQuestion(null);
    setStatus("interpreting");

    try {
      const result = await flowopsCompile.start(prompt, {
        onSession: (id) => {
          sessionIdRef.current = id;
        },
        onStatus: setStatus,
        onToolCall: setLastTool,
        onComposioApproval: (payload) => {
          setStatus("awaiting_probe_approval");
          setPendingProbe(payload);
        },
        onUserQuestion: setPendingQuestion,
      });

      setCompileMeta(result);
      setSpec(result.spec);
      setStatus(result.status ?? null);
    } catch (e) {
      setError(String(e));
      setStatus("failed");
    } finally {
      setIsCompiling(false);
      setPendingProbe(null);
      setPendingQuestion(null);
    }
  }, []);

  async function respondProbe(approved: boolean) {
    if (!pendingProbe || approvalBusy) return;
    setApprovalBusy(true);
    setError(null);
    try {
      await flowopsCompile.approveComposioExec(
        pendingProbe.sessionId,
        pendingProbe.approvalId,
        approved,
      );
      setPendingProbe(null);
      if (approved) setStatus("probing");
    } catch (e) {
      setError(String(e));
    } finally {
      setApprovalBusy(false);
    }
  }

  async function respondQuestion() {
    if (!pendingQuestion || !questionAnswer.trim() || approvalBusy) return;
    setApprovalBusy(true);
    setError(null);
    try {
      const isOption = pendingQuestion.options.includes(questionAnswer.trim());
      await flowopsCompile.answerUserQuestion(pendingQuestion.sessionId, pendingQuestion.questionId, {
        selectedOption: isOption ? questionAnswer.trim() : null,
        customAnswer: isOption ? null : questionAnswer.trim(),
      });
      setPendingQuestion(null);
      setQuestionAnswer("");
    } catch (e) {
      setError(String(e));
    } finally {
      setApprovalBusy(false);
    }
  }

  async function confirm() {
    if (!spec || !canConfirm) return;
    setIsCompiling(true);
    try {
      if (isBffEnabled()) {
        const agent = await bffApi.createAgent("flowops-demo-user", spec);
        await bffApi.activate(agent.id);
      } else {
        const agent = await api.createAgent("me", spec);
        await api.activate(agent.id);
      }
      router.push("/");
    } catch (e) {
      setError(String(e));
      setIsCompiling(false);
    }
  }

  async function revise() {
    const sessionId = sessionIdRef.current;
    if (!sessionId) {
      setError("No compile session — click Interpret again to start a new compile.");
      return;
    }

    const validationHints = compileMeta?.validation_report?.errors ?? [];
    const judgeHints = compileMeta?.judge?.issues ?? [];
    const hints = [...validationHints, ...judgeHints];
    const probeFields =
      compileMeta?.composio_context?.probe_rows &&
      Array.isArray(compileMeta.composio_context.probe_rows) &&
      compileMeta.composio_context.probe_rows[0] &&
      typeof compileMeta.composio_context.probe_rows[0] === "object"
        ? Object.keys(compileMeta.composio_context.probe_rows[0] as object)
            .filter((k) => k !== "attributes")
            .join(", ")
        : "Id, LastModifiedDate, Name";

    const defaultRevision =
      hints.length > 0
        ? [
            "Fix the plan based on validation failures:",
            ...hints.map((h) => `- ${h}`),
            "",
            `Use exact probe row field names: ${probeFields}.`,
            'If SOQL already filters by LastModifiedDate / date window, set condition to: Id ne "".',
            "Do NOT use stale_hours or row_mapping aliases like last_modified_date.",
          ].join("\n")
        : text.trim();

    // When validation failed, always send fix hints — not the original prompt again.
    const revisionMessage = hints.length > 0 ? defaultRevision : text.trim() || defaultRevision;

    if (!revisionMessage) {
      setError("Add revision notes in the text box, or edit your prompt, then click Revise.");
      return;
    }

    setIsCompiling(true);
    setError(null);
    setSpec(null);
    setCompileMeta(null);
    try {
      const result = await flowopsCompile.message(sessionId, revisionMessage, {
        onStatus: setStatus,
        onToolCall: setLastTool,
        onComposioApproval: (payload) => {
          setStatus("awaiting_probe_approval");
          setPendingProbe(payload);
        },
        onUserQuestion: setPendingQuestion,
      });
      setCompileMeta(result);
      setSpec(result.spec);
      setStatus(result.status ?? null);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsCompiling(false);
      setPendingProbe(null);
      setPendingQuestion(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <PageTitle>New digital worker</PageTitle>
        <p className="mt-1.5 max-w-prose text-sm text-muted">
          Describe what to watch or analyze. FlowOps compiles a validated plan before activation.
        </p>
      </div>

      <div className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          spellCheck={false}
          className="w-full resize-y rounded-[var(--radius-panel)] border border-line bg-surface px-4 py-3 text-sm text-ink placeholder:text-faint transition-colors focus:border-line2"
          placeholder="e.g. Watch Salesforce opportunities updated in the last 5 days…"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button
            onClick={() => runCompile(text)}
            variant="primary"
            disabled={isCompiling || text.trim().length === 0}
          >
            {isCompiling ? "Compiling…" : "Interpret"}
          </Button>
          {!spec && !isCompiling && (
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

      {(status || lastTool) && (isCompiling || pendingProbe || pendingQuestion) && (
        <Panel className="px-5 py-3 text-sm text-muted">
          {status ? STATUS_LABEL[status] : "Working…"}
          {lastTool ? <span className="ml-2 font-mono text-xs text-faint">({lastTool})</span> : null}
        </Panel>
      )}

      {pendingProbe && (
        <Panel className="space-y-3 px-5 py-4">
          <p className="text-sm font-medium text-ink">Approve live data probe</p>
          <p className="text-xs text-muted">{pendingProbe.reason}</p>
          <p className="font-mono text-xs text-ink">{pendingProbe.toolSlug}</p>
          <pre className="overflow-x-auto rounded-md bg-bg p-3 font-mono text-[0.7rem] text-faint">
            {JSON.stringify(pendingProbe.arguments, null, 2)}
          </pre>
          <div className="flex gap-2">
            <Button
              onClick={() => respondProbe(true)}
              variant="primary"
              disabled={approvalBusy}
            >
              {approvalBusy ? "Sending…" : "Accept probe"}
            </Button>
            <Button onClick={() => respondProbe(false)} disabled={approvalBusy}>
              Reject
            </Button>
          </div>
        </Panel>
      )}

      {pendingQuestion && (
        <Panel className="space-y-3 px-5 py-4">
          <p className="text-sm font-medium text-ink">{pendingQuestion.question}</p>
          {pendingQuestion.context ? (
            <p className="text-xs text-muted">{pendingQuestion.context}</p>
          ) : null}
          <div className="flex flex-wrap gap-1.5">
            {pendingQuestion.options.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setQuestionAnswer(opt)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  questionAnswer === opt
                    ? "border-accent bg-accent/12 text-accent"
                    : "border-line text-muted"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
          <input
            value={questionAnswer}
            onChange={(e) => setQuestionAnswer(e.target.value)}
            placeholder="Or type a custom answer"
            className="w-full max-w-md rounded-md border border-line bg-bg px-3 py-2 text-sm"
          />
          <Button onClick={respondQuestion} variant="primary" disabled={approvalBusy || !questionAnswer.trim()}>
            {approvalBusy ? "Sending…" : "Submit answer"}
          </Button>
        </Panel>
      )}

      {error && <ErrorNote message={error} />}

      {spec && (
        <div className="rise space-y-4">
          <ValidationChecklist
            validation={compileMeta?.validation_report}
            judge={compileMeta?.judge}
          />
          <PlanSummary
            spec={spec}
            probeRows={compileMeta?.composio_context?.probe_rows}
            validation={compileMeta?.validation_report}
          />
          <div className="flex gap-2">
            <Button onClick={confirm} variant="primary" disabled={isCompiling || !canConfirm}>
              {isCompiling ? "Activating…" : "Confirm & activate"}
            </Button>
            <Button onClick={revise} disabled={isCompiling || !sessionIdRef.current}>
              {isCompiling ? "Recompiling…" : "Revise & recompile"}
            </Button>
          </div>
          {!canConfirm && spec && (
            <p className="text-xs text-warn">
              Confirm is disabled until validation passes and the judge approves the plan.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
