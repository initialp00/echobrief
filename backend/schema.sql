-- EchoBrief database schema (documented DDL)
-- Applied idempotently by backend/init_db.py on startup.

-- Enable UUID generation (gen_random_uuid)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- briefs: one row per submitted voice brief. Carries the status machine.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    engineer_name TEXT NOT NULL,
    audio_url TEXT,
    transcript TEXT,
    ingest_type TEXT NOT NULL CHECK (ingest_type IN ('audio_url', 'audio_file', 'transcript')),
    status TEXT NOT NULL DEFAULT 'received' CHECK (
        status IN ('received', 'queued', 'transcribing', 'drafting', 'ready', 'failed')
    ),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    queued_at TIMESTAMPTZ,
    transcribed_at TIMESTAMPTZ,
    drafted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- structured_notes: the structured JSON note produced from a brief (1:1).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS structured_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id UUID UNIQUE REFERENCES briefs(id) ON DELETE CASCADE,
    incident_title TEXT,
    severity TEXT CHECK (severity IN ('P1', 'P2', 'P3', 'P4')),
    affected_systems JSONB,
    timeline JSONB,
    root_cause TEXT,
    action_items JSONB,
    on_call_engineer TEXT,
    resolution_status TEXT,
    raw_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for listing briefs by status and recency.
CREATE INDEX IF NOT EXISTS idx_briefs_status ON briefs(status);
CREATE INDEX IF NOT EXISTS idx_briefs_created_at ON briefs(created_at DESC);
