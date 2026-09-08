"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { getBrief, type BriefDetail } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { StatusTimeline } from "@/components/StatusTimeline";
import { StructuredNote } from "@/components/StructuredNote";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const POLL_MS = 2000;

export default function BriefDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [brief, setBrief] = useState<BriefDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function load() {
      try {
        const data = await getBrief(id);
        if (!active) return;
        setBrief(data);
        setError(null);
        // Keep polling until the pipeline reaches a terminal state.
        if (data.status !== "ready" && data.status !== "failed") {
          timer = setTimeout(load, POLL_MS);
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load brief");
        timer = setTimeout(load, POLL_MS);
      }
    }
    load();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to dashboard
      </Link>

      {error && !brief && (
        <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}

      {brief && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold">{brief.title}</h1>
              <p className="text-sm text-muted-foreground">
                {brief.engineer_name} · {brief.ingest_type}
              </p>
            </div>
            <StatusBadge status={brief.status} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Pipeline status</CardTitle>
            </CardHeader>
            <CardContent>
              <StatusTimeline brief={brief} />
            </CardContent>
          </Card>

          {brief.status === "failed" && (
            <Card className="border-red-200">
              <CardContent className="flex gap-2 pt-6 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{brief.error_message ?? "Processing failed."}</span>
              </CardContent>
            </Card>
          )}

          {brief.transcript && (
            <Card>
              <CardHeader>
                <CardTitle>Transcript</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                  {brief.transcript}
                </p>
              </CardContent>
            </Card>
          )}

          {brief.status === "ready" && brief.structured_note && (
            <Card>
              <CardHeader>
                <CardTitle>Structured note</CardTitle>
              </CardHeader>
              <CardContent>
                <StructuredNote note={brief.structured_note} />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
