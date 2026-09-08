import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { cn, formatTime } from "@/lib/utils";
import type { BriefDetail } from "@/lib/api";

interface Step {
  key: string;
  label: string;
  at: string | null;
}

export function StatusTimeline({ brief }: { brief: BriefDetail }) {
  const steps: Step[] = [
    { key: "received", label: "received", at: brief.created_at },
    { key: "queued", label: "queued", at: brief.queued_at },
    { key: "transcribing", label: "transcribing", at: brief.transcribed_at },
    { key: "drafting", label: "drafting", at: brief.drafted_at },
    { key: "ready", label: "ready", at: brief.completed_at },
  ];

  const failed = brief.status === "failed";
  // First step without a timestamp is where we currently are.
  const currentIdx = steps.findIndex((s) => !s.at);

  return (
    <ol className="space-y-1">
      {steps.map((step, idx) => {
        const done = Boolean(step.at);
        const isCurrent = idx === currentIdx;
        const isFailedHere = failed && isCurrent;

        let icon;
        if (done) {
          icon = <CheckCircle2 className="h-5 w-5 text-green-600" />;
        } else if (isFailedHere) {
          icon = <XCircle className="h-5 w-5 text-red-600" />;
        } else if (isCurrent && !failed) {
          icon = <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
        } else {
          icon = <Circle className="h-5 w-5 text-slate-300" />;
        }

        return (
          <li key={step.key} className="flex items-center gap-3 py-1.5">
            {icon}
            <span
              className={cn(
                "w-32 text-sm font-medium capitalize",
                done
                  ? "text-foreground"
                  : isFailedHere
                    ? "text-red-600"
                    : isCurrent
                      ? "text-blue-600"
                      : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
            <span className="font-mono text-xs text-muted-foreground">
              {done ? formatTime(step.at) : isFailedHere ? "failed" : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
