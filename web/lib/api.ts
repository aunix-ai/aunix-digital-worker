import type { ActionItem, AgentOut, AgentSpec, CompileResult, FeedItem, IntegrationConnection, RunOut } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${resp.status} ${await resp.text()}`);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  return resp.json() as Promise<T>;
}

export interface IntegrationConnection {
  slug: string;
  name: string;
  logo: string;
  is_connected: boolean;
  status: string;
  connected_account_id?: string | null;
  requires_auth_config?: boolean;
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
  deleteAgent: (id: number) => request<void>(`/agents/${id}`, { method: "DELETE" }),
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
  integrationStatus: () => request<{ connections: IntegrationConnection[] }>("/integrations/status"),
  integrationConnect: (toolkit: string) =>
    request<{ redirect_url: string; connection_request_id?: string }>("/integrations/connect", {
      method: "POST",
      body: JSON.stringify({ toolkit }),
    }),
  integrationSearch: (query: string, toolkits?: string[]) =>
    request<Record<string, unknown>>("/integrations/search", {
      method: "POST",
      body: JSON.stringify({ query, toolkits }),
    }),
  integrationProbe: (tool_slug: string, arguments_?: Record<string, unknown>, row_mapping?: Record<string, string>) =>
    request<{ raw: unknown; rows: Record<string, unknown>[]; row_count: number }>("/integrations/probe", {
      method: "POST",
      body: JSON.stringify({ tool_slug, arguments: arguments_ ?? {}, row_mapping: row_mapping ?? {} }),
    }),
};
