import { AlertTriangle, CheckSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StructuredNoteData } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const SEVERITY_STYLES: Record<string, string> = {
  P1: "bg-red-500 text-black",
  P2: "bg-orange-400 text-black",
  P3: "bg-yellow-300 text-black",
  P4: "bg-slate-300 text-black",
};

const RESOLUTION_STYLES: Record<string, string> = {
  Resolved: "bg-lime-400 text-black",
  Monitoring: "bg-sky-300 text-black",
  Ongoing: "bg-orange-400 text-black",
};

const BADGE = "rounded-md border-2 border-black shadow-brutal-sm";

export function StructuredNote({ note }: { note: StructuredNoteData }) {
  return (
    <div className="space-y-6">
      {/* Header: title + severity + resolution */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-xl font-black leading-snug">
          {note.incident_title}
        </h2>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              BADGE,
              "px-2.5 py-1 text-sm font-black uppercase",
              SEVERITY_STYLES[note.severity] ?? "bg-slate-300 text-black"
            )}
          >
            {note.severity}
          </span>
          <span
            className={cn(
              BADGE,
              "px-2.5 py-1 text-sm font-bold uppercase",
              RESOLUTION_STYLES[note.resolution_status] ?? "bg-slate-200 text-black"
            )}
          >
            {note.resolution_status}
          </span>
        </div>
      </div>

      {/* Affected systems */}
      <div>
        <h3 className="mb-2 text-xs font-black uppercase tracking-wide">
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
        <h3 className="mb-2 text-xs font-black uppercase tracking-wide">
          Timeline
        </h3>
        <ol className="space-y-2 border-l-4 border-black pl-4">
          {note.timeline.map((t, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[23px] top-1.5 h-3 w-3 rounded-full border-2 border-black bg-primary" />
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
        <h3 className="mb-2 text-xs font-black uppercase tracking-wide">
          Root cause
        </h3>
        <div className="flex gap-2 rounded-md border-2 border-black bg-yellow-200 p-3 text-sm font-medium text-black shadow-brutal-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{note.root_cause}</span>
        </div>
      </div>

      {/* Action items */}
      <div>
        <h3 className="mb-2 text-xs font-black uppercase tracking-wide">
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
