import { cn } from "@/lib/utils";
import type { BriefStatus } from "@/lib/api";

const STATUS_STYLES: Record<BriefStatus, string> = {
  received: "bg-slate-200 text-black",
  queued: "bg-sky-300 text-black",
  transcribing: "bg-yellow-300 text-black",
  drafting: "bg-orange-400 text-black",
  ready: "bg-lime-400 text-black",
  failed: "bg-red-400 text-black",
};

export function StatusBadge({
  status,
  className,
}: {
  status: BriefStatus;
  className?: string;
}) {
  const pulse = status !== "ready" && status !== "failed";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border-2 border-black px-2.5 py-0.5 text-xs font-bold uppercase tracking-tight shadow-brutal-sm",
        STATUS_STYLES[status],
        className
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full bg-current",
          pulse && "animate-pulse"
        )}
      />
      {status}
    </span>
  );
}
