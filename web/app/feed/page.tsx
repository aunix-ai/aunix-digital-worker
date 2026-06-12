"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { FeedItem } from "@/lib/types";
import { FeedCard } from "@/components/FeedCard";
import { ErrorNote, PageTitle, Panel, SkeletonRows } from "@/components/ui";

export default function FeedPage() {
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () => api.feed().then(setItems).catch((e) => setError(String(e)));
    load();
    const t = setInterval(() => api.feed().then(setItems).catch(() => {}), 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageTitle>Activity</PageTitle>
        {items && items.length > 0 && (
          <span className="font-mono text-xs text-faint">
            {items.length} alert{items.length === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {error && <ErrorNote message={error} />}

      {!items ? (
        <SkeletonRows count={4} />
      ) : items.length === 0 ? (
        <Panel className="px-6 py-14 text-center">
          <p className="text-ink">All quiet.</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
            Your agents haven&rsquo;t found anything that needs attention. Alerts land here the
            moment a condition is breached — exactly once per issue.
          </p>
        </Panel>
      ) : (
        <div className="space-y-3">
          {items.map((item, i) => (
            <div key={item.id} className="rise" style={{ animationDelay: `${i * 50}ms` }}>
              <FeedCard item={item} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
