import type {
  AgentSpec,
  ClarifyingQuestion,
  CompileResult,
  CompileSessionStatus,
  JudgeVerdict,
  ValidationReport,
} from "./types";

const FLOWOPS_BASE =
  process.env.NEXT_PUBLIC_FLOWOPS_COMPILE_URL ?? "http://localhost:3999";

export interface ComposioExecApprovalPayload {
  approvalId: string;
  sessionId: string;
  toolSlug: string;
  arguments: Record<string, unknown>;
  reason: string;
}

export interface UserQuestionPayload {
  questionId: string;
  sessionId: string;
  question: string;
  options: string[];
  context?: string;
}

export interface CompileStreamHandlers {
  onSession?: (sessionId: string) => void;
  onStatus?: (status: CompileSessionStatus) => void;
  onToolCall?: (tool: string) => void;
  onComposioApproval?: (payload: ComposioExecApprovalPayload) => void;
  onUserQuestion?: (payload: UserQuestionPayload) => void;
}

async function readSseCompile(
  response: Response,
  handlers: CompileStreamHandlers,
): Promise<CompileResult & { sessionId?: string }> {
  if (!response.body) {
    throw new Error("No response body from compile stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sessionId: string | undefined;
  let result: CompileResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      let event = "message";
      let dataLine = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        if (line.startsWith("data: ")) dataLine = line.slice(6);
      }
      if (!dataLine || dataLine === "[DONE]") continue;

      let data: Record<string, unknown>;
      try {
        data = JSON.parse(dataLine) as Record<string, unknown>;
      } catch {
        continue;
      }

      if (event === "session" && typeof data.sessionId === "string") {
        sessionId = data.sessionId;
        handlers.onSession?.(sessionId);
      }
      if (event === "status-change" && typeof data.status === "string") {
        handlers.onStatus?.(data.status as CompileSessionStatus);
      }
      if (event === "tool-call" && typeof data.tool === "string") {
        handlers.onToolCall?.(data.tool);
      }
      if (event === "composio-exec-approval") {
        handlers.onComposioApproval?.(data as unknown as ComposioExecApprovalPayload);
      }
      if (event === "user-question") {
        handlers.onUserQuestion?.(data as unknown as UserQuestionPayload);
      }
      if (event === "compile-result") {
        result = data as unknown as CompileResult;
      }
      if (event === "error") {
        throw new Error(String(data.message ?? "Compile stream error"));
      }
    }
  }

  if (!result) {
    throw new Error("Compile finished without a result");
  }

  return { ...result, sessionId };
}

export const flowopsCompile = {
  baseUrl: FLOWOPS_BASE,

  async start(text: string, handlers: CompileStreamHandlers = {}) {
    const resp = await fetch(`${FLOWOPS_BASE}/api/digital-worker/compile`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) {
      throw new Error(`${resp.status} ${await resp.text()}`);
    }
    return readSseCompile(resp, handlers);
  },

  async continue(sessionId: string, handlers: CompileStreamHandlers = {}) {
    const resp = await fetch(`${FLOWOPS_BASE}/api/digital-worker/compile/continue`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sessionId }),
    });
    if (!resp.ok) {
      throw new Error(`${resp.status} ${await resp.text()}`);
    }
    return readSseCompile(resp, handlers);
  },

  async message(sessionId: string, text: string, handlers: CompileStreamHandlers = {}) {
    const resp = await fetch(`${FLOWOPS_BASE}/api/digital-worker/compile/message`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sessionId, text }),
    });
    if (!resp.ok) {
      throw new Error(`${resp.status} ${await resp.text()}`);
    }
    return readSseCompile(resp, handlers);
  },

  async approveComposioExec(sessionId: string, approvalId: string, approved: boolean) {
    const resp = await fetch(`${FLOWOPS_BASE}/api/digital-worker/composio-exec`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sessionId, approvalId, approved }),
    });
    if (!resp.ok) {
      throw new Error(`${resp.status} ${await resp.text()}`);
    }
    return resp.json();
  },

  async answerUserQuestion(
    sessionId: string,
    questionId: string,
    answer: { selectedOption?: string | null; customAnswer?: string | null },
  ) {
    const resp = await fetch(`${FLOWOPS_BASE}/api/digital-worker/user-question`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sessionId, questionId, ...answer }),
    });
    if (!resp.ok) {
      throw new Error(`${resp.status} ${await resp.text()}`);
    }
    return resp.json();
  },
};

export type { ValidationReport, JudgeVerdict };
