// API client for the EchoBrief backend.
//
// All requests are same-origin and go through Nginx, which proxies /api/* to
// FastAPI. Using a relative base means the app works regardless of the host
// port Nginx is published on (80, 8081, ...).
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.length > 0
    ? process.env.NEXT_PUBLIC_API_URL
    : "/api";

export type BriefStatus =
  | "received"
  | "queued"
  | "transcribing"
  | "drafting"
  | "ready"
  | "failed";

export type IngestType = "transcript" | "audio_url" | "audio_file";

export interface TimelineEntry {
  time: string;
  event: string;
}

export interface StructuredNoteData {
  incident_title: string;
  severity: "P1" | "P2" | "P3" | "P4";
  affected_systems: string[];
  timeline: TimelineEntry[];
  root_cause: string;
  action_items: string[];
  on_call_engineer: string;
  resolution_status: "Resolved" | "Ongoing" | "Monitoring";
}

export interface BriefListItem {
  id: string;
  title: string;
  engineer_name: string;
  status: BriefStatus;
  created_at: string | null;
  completed_at: string | null;
}

export interface BriefDetail {
  id: string;
  title: string;
  engineer_name: string;
  ingest_type: IngestType;
  status: BriefStatus;
  error_message: string | null;
  created_at: string | null;
  queued_at: string | null;
  transcribed_at: string | null;
  drafted_at: string | null;
  completed_at: string | null;
  transcript: string | null;
  structured_note: StructuredNoteData | null;
}

export interface CreateBriefInput {
  title: string;
  engineer_name: string;
  ingest_type: IngestType;
  transcript?: string | null;
  audio_url?: string | null;
}

export interface CreateBriefResponse {
  id: string;
  title: string;
  status: BriefStatus;
  created_at: string | null;
}

export interface HealthResponse {
  status: string;
  db: string;
  kafka: string;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return handle<HealthResponse>(res);
}

export async function createBrief(
  input: CreateBriefInput
): Promise<CreateBriefResponse> {
  const res = await fetch(`${API_BASE}/briefs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handle<CreateBriefResponse>(res);
}

export async function listBriefs(params?: {
  status?: BriefStatus;
  limit?: number;
  offset?: number;
}): Promise<BriefListItem[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  q.set("limit", String(params?.limit ?? 20));
  q.set("offset", String(params?.offset ?? 0));
  const res = await fetch(`${API_BASE}/briefs?${q.toString()}`, {
    cache: "no-store",
  });
  return handle<BriefListItem[]>(res);
}

export async function getBrief(id: string): Promise<BriefDetail> {
  const res = await fetch(`${API_BASE}/briefs/${id}`, { cache: "no-store" });
  return handle<BriefDetail>(res);
}
