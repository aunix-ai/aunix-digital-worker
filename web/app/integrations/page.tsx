"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { IntegrationConnection } from "@/lib/types";

export default function IntegrationsPage() {
  const [connections, setConnections] = useState<IntegrationConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.integrationStatus();
      setConnections(data.connections);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load integrations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const connect = async (toolkit: string) => {
    setConnecting(toolkit);
    setError(null);
    try {
      const { redirect_url } = await api.integrationConnect(toolkit);
      const popup = window.open(redirect_url, "composio-oauth", "width=600,height=700");
      const timer = setInterval(() => {
        if (popup?.closed) {
          clearInterval(timer);
          setConnecting(null);
          load();
        }
      }, 500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connect failed");
      setConnecting(null);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-5 py-8">
      <h1 className="text-xl font-semibold tracking-tight">Integrations</h1>
      <p className="mt-2 text-sm text-muted">
        Connect external systems via Composio. Connected toolkits can be used when creating agents.
      </p>
      {error && (
        <p className="mt-4 rounded-md border border-sev-critical/30 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
          {error}
        </p>
      )}
      {loading ? (
        <p className="mt-6 text-sm text-muted">Loading connections…</p>
      ) : (
        <ul className="mt-6 space-y-3">
          {connections.map((c) => (
            <li key={c.slug} className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3">
              <div className="flex items-center gap-3">
                {c.logo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.logo} alt="" className="size-8 rounded-md bg-bg object-contain" />
                ) : (
                  <span className="grid size-8 place-items-center rounded-md bg-bg text-xs font-semibold uppercase">
                    {c.slug.slice(0, 2)}
                  </span>
                )}
                <div>
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-muted">{c.is_connected ? c.status : "Not connected"}</div>
                </div>
              </div>
              <button
                type="button"
                disabled={c.is_connected || connecting === c.slug}
                onClick={() => connect(c.slug)}
                className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-ink disabled:opacity-50"
              >
                {c.is_connected ? "Connected" : connecting === c.slug ? "Connecting…" : "Connect"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
