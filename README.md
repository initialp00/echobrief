# EchoBrief

**Async voice brief → structured incident notes, with a real-time dashboard.**

An on-call engineer submits a 30–90s incident brief (transcript or audio). EchoBrief
transcribes it, then uses an LLM to turn it into a standardised **structured incident
note** (JSON with explicit fields — not a blob of prose). Everything happens
**asynchronously** through a real message bus (Kafka), the status machine is persisted
in Postgres, and a **Next.js dashboard** lets you watch each brief move through
`received → queued → transcribing → drafting → ready` in real time.

> Domain: **On-call engineering incident briefs.**

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                            EchoBrief                               │
│                                                                   │
│  Browser ── http://localhost (Nginx :80) ─────────────────────►   │
│                    │                                              │
│            ┌───────┴────────┐                                    │
│            │     Nginx      │ ── /            ─► Next.js (:3000)  │
│            │ (reverse proxy)│ ── /api/*       ─► FastAPI (:8000)  │
│            │                │ ── /docs        ─► Swagger          │
│            └───────┬────────┘                                    │
│                    │ POST /api/briefs                            │
│                    ▼                                              │
│            ┌──────────────┐  INSERT brief (received)             │
│            │   FastAPI    │  publish echobrief.transcribe        │
│            │    (API)     │  UPDATE status=queued ───────────►   │
│            └──────┬───────┘                     PostgreSQL        │
│                   │                                              │
│                   ▼                                              │
│            ┌──────────────┐  topics:                            │
│            │    Kafka     │   echobrief.transcribe              │
│            │ (message bus)│   echobrief.structure               │
│            └──────┬───────┘                                     │
│                   │ consume echobrief.transcribe                │
│                   ▼                                             │
│            ┌──────────────┐ UPDATE transcribing                │
│            │    Worker    │ mock / real (Whisper) transcription │
│            │  (consumer)  │ publish echobrief.structure ──────► │
│            │              │ consume echobrief.structure         │
│            │              │ UPDATE drafting                     │
│            │              │ OpenRouter claude-sonnet → JSON     │
│            │              │ validate (Pydantic) → INSERT note   │
│            │              │ UPDATE ready ─────────────────────► │
│            └──────────────┘                     PostgreSQL       │
│                                                                  │
│  Dashboard polls GET /api/briefs (3s) and /api/briefs/{id} (2s) │
│  and renders the structured note when status = ready.           │
└───────────────────────────────────────────────────────────────────┘
```

### Components
| Component | Tech | Role |
|---|---|---|
| Reverse proxy | Nginx | Single entry point (`:80`); routes `/` → UI, `/api/*` → API, `/docs` |
| Frontend | Next.js 14 (App Router) + TS + Tailwind + shadcn-style UI | Submit briefs, live status dashboard, structured-note viewer |
| API | FastAPI (async) | Create/list/fetch briefs, health, enqueue work |
| Message bus | Apache Kafka (+ Zookeeper) | Real async handoff, two-stage pipeline |
| Worker | Python consumer (separate process) | transcribe → structure → update DB |
| DB | PostgreSQL 16 | Briefs + structured notes, persisted status machine |
| LLM | claude-sonnet via OpenRouter | Structures transcript into JSON note (offline fallback if no key) |

### Status machine
```
received ─(API publishes echobrief.transcribe)─► queued
   ─(worker consumes)─► transcribing
   ─(worker publishes echobrief.structure)─► drafting
   ─(worker structures + persists)─► ready
        └─ any stage error ─► failed  (error_message stored + shown in UI)
```
Every transition is persisted with a timestamp: `created_at`, `queued_at`,
`transcribed_at`, `drafted_at`, `completed_at`.

---

## Run locally

**Prereqs:** Docker + Docker Compose. One command:

```bash
git clone <repo>
cd echobrief
cp .env.example .env        # Windows: copy .env.example .env
# (optional) add your OPENROUTER_API_KEY to .env
docker compose up --build
```

Then open:
- **Dashboard:** http://localhost
- **Swagger UI:** http://localhost/docs
- **Health:**    http://localhost/api/health

> **Port 80 already in use?** Expose the app on another host port:
> `WEB_PORT=8090 docker compose up --build` → open http://localhost:8090
> (Everything is same-origin behind Nginx, so the UI just works on any port.)

> **No API key?** No problem. If `OPENROUTER_API_KEY` is missing/placeholder,
> the worker uses a deterministic **offline structurer** so the *entire async
> pipeline still runs end-to-end*. Add a key to get real claude-sonnet output.

The API container applies the schema on startup (`init_db.py`, idempotent and
retrying), so the first `docker compose up` is all you need.

---

## Using the dashboard

1. **Submit a brief** (left card): title, engineer name, ingest type
   (`transcript` or `audio_url`), and the transcript text. Hit **Load example**
   to prefill a realistic incident, then **Submit brief**.
2. You're redirected to the **brief detail page**, which auto-polls every 2s and
   shows a **status timeline** with real DB timestamps as the brief moves
   `received → queued → transcribing → drafting → ready`.
3. When `ready`, the **structured note** renders: severity badge, affected
   systems as tags, timeline, root cause, and an action-items checklist.
4. The **Recent briefs** list (right card) auto-refreshes every 3s; the top bar
   shows a live **system health** dot (green when `/api/health` is `ok`).

The UI is self-explanatory — an evaluator can drive the whole flow without a terminal.

---

## Data model

Two tables (full DDL in [`backend/schema.sql`](backend/schema.sql)):

- **`briefs`** — one row per submission; holds ingest data + the status machine
  and per-stage timestamps.
- **`structured_notes`** — 1:1 with a brief; structured JSON note with explicit
  columns (`incident_title`, `severity`, `affected_systems`, `timeline`,
  `root_cause`, `action_items`, …) plus the full `raw_json`.

Statuses: `received → queued → transcribing → drafting → ready | failed`.

---

## API

All API routes are served under `/api/*` via Nginx (which strips the prefix
before proxying to FastAPI).

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| `GET`  | `/api/health` | DB + Kafka connectivity | `200` | — |
| `POST` | `/api/briefs` | Create a brief (enqueues async processing) | `201` | `422` invalid body, `503` bus down |
| `GET`  | `/api/briefs` | List briefs (`?status=&limit=&offset=`) | `200` | `422` bad query |
| `GET`  | `/api/briefs/{id}` | Full brief incl. structured note when ready | `200` | `404` not found |
| `GET`  | `/api/briefs/{id}/note` | Structured note JSON | `200` | `404` not found, `409` not ready |

> Swagger UI (interactive) is at **`/docs`**, and the OpenAPI spec at **`/openapi.json`**.

### Endpoint reference

**`GET /api/health`** — liveness of dependencies.
```json
{ "status": "ok", "db": "connected", "kafka": "connected" }
```

**`POST /api/briefs`** — create a brief and start the async pipeline.
Request body:
```jsonc
{
  "title": "API gateway 5xx spike",       // required
  "engineer_name": "Nishil",              // required
  "ingest_type": "transcript",            // required: "transcript" | "audio_url" | "audio_file"
  "transcript": "At 14:32 UTC ...",       // required when ingest_type = "transcript"
  "audio_url": "https://.../brief.wav"    // required when ingest_type = "audio_url"
}
```
Response `201`:
```json
{ "id": "uuid", "title": "API gateway 5xx spike", "status": "queued", "created_at": "2026-09-08T14:32:01Z" }
```

**`GET /api/briefs`** — list briefs, newest first.
Query params: `status` (optional filter), `limit` (1–100, default 20), `offset` (default 0).
Response `200`:
```json
[
  { "id": "uuid", "title": "...", "engineer_name": "Nishil",
    "status": "ready", "created_at": "...", "completed_at": "..." }
]
```

**`GET /api/briefs/{id}`** — full brief with per-stage timestamps + note when ready.
Response `200`:
```json
{
  "id": "uuid", "title": "...", "engineer_name": "Nishil", "ingest_type": "transcript",
  "status": "ready", "error_message": null,
  "created_at": "...", "queued_at": "...", "transcribed_at": "...",
  "drafted_at": "...", "completed_at": "...",
  "transcript": "At 14:32 UTC ...",
  "structured_note": { "...": "see below, or null until ready" }
}
```

**`GET /api/briefs/{id}/note`** — just the structured note JSON. Returns `409`
with the current status until the brief is `ready`.

### Examples

```bash
# Create a brief from a transcript
curl -X POST http://localhost/api/briefs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API gateway 5xx spike",
    "engineer_name": "Nishil",
    "ingest_type": "transcript",
    "transcript": "At 14:32 UTC we saw elevated 5xx errors on the API gateway. Root cause was Redis connection pool exhaustion after a config change at 14:15. Rolled back at 14:47, normalised by 14:52. Action items: increase pool size, add monitoring alert, add config freeze window."
  }'
# -> { "id": "...", "title": "...", "status": "queued", "created_at": "..." }

curl http://localhost/api/briefs/<id>          # poll status
curl http://localhost/api/briefs/<id>/note     # structured note (once ready)
curl "http://localhost/api/briefs?status=ready&limit=20"
curl http://localhost/api/health               # {"status":"ok","db":"connected","kafka":"connected"}
```

### Structured note output (example)
```json
{
    "incident_title": "API Gateway 5xx Spike - Redis Connection Pool Exhaustion",
    "severity": "P1",
    "affected_systems": ["api-gateway", "auth-service", "redis"],
    "timeline": [
        {"time": "14:15 UTC", "event": "Config change deployed"},
        {"time": "14:32 UTC", "event": "Elevated 5xx errors detected on API gateway"},
        {"time": "14:38 UTC", "event": "Error rate peaked at 23%"},
        {"time": "14:47 UTC", "event": "Config rollback initiated"},
        {"time": "14:52 UTC", "event": "Error rates normalised"}
    ],
    "root_cause": "Redis connection pool exhaustion following a misconfigured deployment at 14:15 UTC",
    "action_items": [
        "Increase Redis connection pool size",
        "Add connection pool monitoring alert",
        "Implement config change freeze window during peak hours"
    ],
    "on_call_engineer": "Nishil",
    "resolution_status": "Resolved"
}
```

---

## Kafka topics

| Topic | Producer | Consumer | Payload |
|---|---|---|---|
| `echobrief.transcribe` | API on brief creation | Worker transcribe handler | `{brief_id, ingest_type, audio_url, transcript}` |
| `echobrief.structure`  | Worker after transcription | Worker structure handler | `{brief_id, transcript}` |

---

## Transcription: mock vs real

The demo uses **mock transcription** for audio paths (returns a realistic
incident transcript) so the image stays small and the pipeline is network-free.
The **transcript** ingest path is fully real (uses the supplied text verbatim).

To enable real speech-to-text, install `faster-whisper` and swap
`_mock_transcribe` for the documented `_real_transcribe` in
[`backend/worker/transcriber.py`](backend/worker/transcriber.py).

---

## Design trade-offs

1. **Kafka over Redis pub/sub** — Kafka persists messages and supports replay.
   If the worker crashes mid-processing, the message isn't lost (manual offset
   commits → at-least-once). Redis pub/sub would drop messages with no live consumer.

2. **Two-topic pipeline (`transcribe` + `structure`)** — separating stages lets
   transcription (CPU-heavy, e.g. Whisper) and structuring (I/O-heavy LLM call)
   scale independently, and makes each stage individually retryable.

3. **Mock transcription for the demo** — real Whisper adds a heavy dependency
   (model download + CPU/GPU inference). Mocking demonstrates the async pipeline
   correctly; production path is documented (`faster-whisper`).

4. **Status machine in the DB** — every transition is persisted with a timestamp,
   giving a full audit trail and powering the UI status timeline without extra queries.

5. **Polling vs WebSockets** — the dashboard polls (`/api/briefs` 3s, detail 2s).
   Chosen for simplicity/reliability; a production improvement is SSE/WebSocket push.

6. **Nginx single entry point** — one origin (`:80`) serves the UI, the API
   (`/api/*`), and Swagger (`/docs`). This avoids CORS entirely and lets the
   frontend use relative, same-origin API calls (works on any published port).

7. **UI beyond the minimum** — a REST API + Swagger is technically sufficient,
   but the async pipeline is invisible without a UI. Watching a brief flow through
   the status machine in real time demonstrates the architecture far better than curl.

8. **LLM fallback** — a deterministic offline structurer keeps the pipeline runnable
   without an API key or network; real claude-sonnet is used whenever a key is present.

---

## Repo layout

```
echobrief/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # env-driven settings
│   │   ├── database.py        # async SQLAlchemy engine/session
│   │   ├── routers/           # briefs.py, health.py
│   │   ├── models/            # db.py (ORM), schemas.py (Pydantic)
│   │   └── services/          # producer.py (Kafka), structured_note.py (LLM)
│   ├── worker/                # consumer.py (status machine), transcriber.py
│   ├── schema.sql             # documented DDL
│   ├── init_db.py             # idempotent schema apply (with retries)
│   ├── Dockerfile / Dockerfile.worker / requirements.txt
├── frontend/                  # Next.js 14 + TS + Tailwind (shadcn-style UI)
│   ├── app/                   # layout, dashboard (page.tsx), briefs/[id]
│   ├── components/            # BriefForm, BriefList, StatusBadge,
│   │   ├── ui/                #   StatusTimeline, StructuredNote, + ui primitives
│   ├── lib/                   # api.ts (client), utils.ts
│   └── Dockerfile
├── nginx/nginx.conf           # reverse proxy (/ -> UI, /api -> API, /docs)
├── docker-compose.yml         # postgres + zookeeper + kafka + api + worker + frontend + nginx
├── .env.example
└── README.md
```

---

## Local dev without Docker (optional)

```bash
# Backend (needs local Postgres + Kafka)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/echobrief
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
python init_db.py
uvicorn app.main:app --reload           # terminal 1: API (:8000)
python -m worker.consumer               # terminal 2: worker

# Frontend
cd frontend
npm install
# point the UI at the API directly (no Nginx in dev):
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```
