import type { ActionItem, AgentOut, AgentSpec, CompileResult, FeedItem, RunOut } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${resp.status} ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  compile: (text: string) =>
    request<CompileResult>("/agents/compile", { method: "POST", body: JSON.stringify({ text }) }),
  createAgent: (owner: string, spec: AgentSpec) =>
    request<AgentOut>("/agents", { method: "POST", body: JSON.stringify({ owner, spec }) }),
  listAgents: () => request<AgentOut[]>("/agents"),
  getAgent: (id: number) => request<AgentOut>(`/agents/${id}`),
  activate: (id: number) => request<AgentOut>(`/agents/${id}/activate`, { method: "POST" }),
  pause: (id: number) => request<AgentOut>(`/agents/${id}/pause`, { method: "POST" }),
  runNow: (id: number) => request<RunOut>(`/agents/${id}/run`, { method: "POST" }),
  listRuns: (id: number) => request<RunOut[]>(`/agents/${id}/runs`),
  getRun: (id: number) => request<RunOut>(`/runs/${id}`),
  feed: () => request<FeedItem[]>("/feed"),
  listActions: (status?: string) =>
    request<ActionItem[]>(`/actions${status ? `?status=${status}` : ""}`),
  approveAction: (id: number, params?: Record<string, unknown>) =>
    request<ActionItem>(`/actions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(params ? { params } : {}),
    }),
  rejectAction: (id: number) =>
    request<ActionItem>(`/actions/${id}/reject`, { method: "POST" }),
};
