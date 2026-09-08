"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listBriefs, type BriefListItem } from "@/lib/api";
import { formatTime } from "@/lib/utils";
import { StatusBadge } from "@/components/StatusBadge";

const REFRESH_MS = 3000;

export function BriefList() {
  const [briefs, setBriefs] = useState<BriefListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await listBriefs({ limit: 20 });
        if (active) {
          setBriefs(data);
          setError(null);
          setLoaded(true);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed");
      }
    }
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Auto-refreshing every {REFRESH_MS / 1000}s
        </p>
        <span className="flex h-2 w-2 rounded-full bg-green-500" />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {loaded && briefs.length === 0 && (
        <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          No briefs yet. Submit one to see the pipeline in action.
        </p>
      )}

      <ul className="space-y-2">
        {briefs.map((b) => (
          <li key={b.id}>
            <Link
              href={`/briefs/${b.id}`}
              className="flex items-center justify-between rounded-lg border bg-card p-3 transition-colors hover:bg-accent"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{b.title}</p>
                <p className="text-xs text-muted-foreground">
                  {b.engineer_name} · {formatTime(b.created_at)}
                </p>
              </div>
              <StatusBadge status={b.status} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
