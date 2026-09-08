"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { createBrief, type IngestType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const EXAMPLE_TRANSCRIPT =
  "At 14:32 UTC we started seeing elevated 5xx errors on the API gateway. " +
  "Error rate peaked at 23 percent around 14:38. Auth service was returning " +
  "connection timeouts. Root cause was Redis connection pool exhaustion after " +
  "a config change deployed at 14:15. We rolled back the config at 14:47 and " +
  "error rates normalised by 14:52. Action items: increase connection pool " +
  "size, add connection pool monitoring alert, add config change freeze window.";

export function BriefForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [engineerName, setEngineerName] = useState("");
  const [ingestType, setIngestType] = useState<IngestType>("transcript");
  const [transcript, setTranscript] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await createBrief({
        title,
        engineer_name: engineerName,
        ingest_type: ingestType,
        transcript: ingestType === "transcript" ? transcript : null,
        audio_url: ingestType === "audio_url" ? audioUrl : null,
      });
      router.push(`/briefs/${res.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit brief");
      setSubmitting(false);
    }
  }

  function loadExample() {
    setTitle("API gateway 5xx spike");
    setEngineerName("Nishil");
    setIngestType("transcript");
    setTranscript(EXAMPLE_TRANSCRIPT);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="API gateway 5xx spike"
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="engineer">Engineer name</Label>
        <Input
          id="engineer"
          value={engineerName}
          onChange={(e) => setEngineerName(e.target.value)}
          placeholder="Nishil"
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ingest">Ingest type</Label>
        <Select
          id="ingest"
          value={ingestType}
          onChange={(e) => setIngestType(e.target.value as IngestType)}
        >
          <option value="transcript">transcript</option>
          <option value="audio_url">audio_url</option>
        </Select>
      </div>

      {ingestType === "transcript" ? (
        <div className="space-y-1.5">
          <Label htmlFor="transcript">Transcript</Label>
          <Textarea
            id="transcript"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="What happened during the incident..."
            required
          />
        </div>
      ) : (
        <div className="space-y-1.5">
          <Label htmlFor="audioUrl">Audio URL</Label>
          <Input
            id="audioUrl"
            value={audioUrl}
            onChange={(e) => setAudioUrl(e.target.value)}
            placeholder="https://example.com/brief.wav"
            required
          />
          <p className="text-xs text-muted-foreground">
            Demo uses mock transcription for audio; the transcript path is real.
          </p>
        </div>
      )}

      {error && (
        <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>
      )}

      <div className="flex items-center gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          {submitting ? "Submitting..." : "Submit brief"}
        </Button>
        <Button type="button" variant="outline" onClick={loadExample}>
          Load example
        </Button>
      </div>
    </form>
  );
}
