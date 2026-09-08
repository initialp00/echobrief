import { cn } from "@/lib/utils";
import type { BriefStatus } from "@/lib/api";

const STATUS_STYLES: Record<BriefStatus, string> = {
  received: "bg-slate-200 text-slate-700",
  queued: "bg-blue-100 text-blue-700",
  transcribing: "bg-yellow-100 text-yellow-800",
  drafting: "bg-orange-100 text-orange-800",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
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
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize",
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
