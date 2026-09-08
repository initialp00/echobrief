"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

export function HealthIndicator() {
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    async function check() {
      try {
        const h = await getHealth();
        if (active) setOk(h.status === "ok");
      } catch {
        if (active) setOk(false);
      }
    }
    check();
    const id = setInterval(check, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const label = ok === null ? "checking" : ok ? "healthy" : "degraded";
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span
        className={cn(
          "h-2.5 w-2.5 rounded-full",
          ok === null
            ? "bg-slate-300"
            : ok
              ? "bg-green-500"
              : "bg-red-500"
        )}
      />
      <span>System {label}</span>
    </div>
  );
}
