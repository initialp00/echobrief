import { AlertTriangle, CheckSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StructuredNoteData } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const SEVERITY_STYLES: Record<string, string> = {
  P1: "bg-red-600 text-white",
  P2: "bg-orange-500 text-white",
  P3: "bg-yellow-500 text-white",
  P4: "bg-slate-400 text-white",
};

const RESOLUTION_STYLES: Record<string, string> = {
  Resolved: "bg-green-100 text-green-700",
  Monitoring: "bg-blue-100 text-blue-700",
  Ongoing: "bg-orange-100 text-orange-700",
};

export function StructuredNote({ note }: { note: StructuredNoteData }) {
  return (
    <div className="space-y-6">
      {/* Header: title + severity + resolution */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-xl font-semibold leading-snug">
          {note.incident_title}
        </h2>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "rounded-md px-2.5 py-1 text-sm font-bold",
              SEVERITY_STYLES[note.severity] ?? "bg-slate-400 text-white"
            )}
          >
            {note.severity}
          </span>
          <span
            className={cn(
              "rounded-md px-2.5 py-1 text-sm font-medium",
              RESOLUTION_STYLES[note.resolution_status] ??
                "bg-slate-100 text-slate-700"
            )}
          >
            {note.resolution_status}
          </span>
        </div>
      </div>

      {/* Affected systems */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
          Affected systems
        </h3>
        <div className="flex flex-wrap gap-2">
          {note.affected_systems.length ? (
            note.affected_systems.map((s) => (
              <Badge key={s} variant="secondary">
                {s}
              </Badge>
            ))
          ) : (
            <span className="text-sm text-muted-foreground">—</span>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
          Timeline
        </h3>
        <ol className="space-y-2 border-l-2 border-slate-200 pl-4">
          {note.timeline.map((t, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-slate-400" />
              <span className="font-mono text-xs text-muted-foreground">
                {t.time}
              </span>
              <p className="text-sm">{t.event}</p>
            </li>
          ))}
        </ol>
      </div>

      {/* Root cause */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
          Root cause
        </h3>
        <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{note.root_cause}</span>
        </div>
      </div>

      {/* Action items */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
          Action items
        </h3>
        <ul className="space-y-1.5">
          {note.action_items.map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <CheckSquare className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
              <span>{a}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="text-xs text-muted-foreground">
        On-call engineer: {note.on_call_engineer}
      </div>
    </div>
  );
}
