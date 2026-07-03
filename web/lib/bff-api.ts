import type { AgentSpec } from "./types";

const BFF_BASE = process.env.NEXT_PUBLIC_BFF_URL ?? "";
const BFF_API_KEY = process.env.NEXT_PUBLIC_BFF_API_KEY ?? "";
const BFF_JWT = process.env.NEXT_PUBLIC_BFF_JWT ?? "";

export type BffAgentOut = {
  id: string;
  owner: string;
  status: string;
  spec: AgentSpec;
};

function headers(): HeadersInit {
  const h: Record<string, string> = { "content-type": "application/json" };
  if (BFF_API_KEY) h["x-api-key"] = BFF_API_KEY;
  if (BFF_JWT) h.authorization = `Bearer ${BFF_JWT}`;
  return h;
}

async function bffRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BFF_BASE}${path}`, { ...init, headers: headers() });
  if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

export function isBffEnabled(): boolean {
  return Boolean(BFF_BASE && BFF_API_KEY);
}

export const bffApi = {
  createAgent: (owner: string, spec: AgentSpec) =>
    bffRequest<BffAgentOut>("/digital-worker/agents", {
      method: "POST",
      body: JSON.stringify({ owner, spec }),
    }),
  activate: (id: string) =>
    bffRequest<BffAgentOut>(`/digital-worker/agents/${id}/activate`, { method: "POST" }),
  runNow: (id: string) =>
    bffRequest<Record<string, unknown>>(`/digital-worker/agents/${id}/run`, { method: "POST" }),
};
