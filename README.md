# EchoBrief

**Async voice brief → structured incident notes.**

An on-call engineer records (or submits) a 30–90s incident brief. EchoBrief
transcribes it, then uses an LLM to turn it into a standardised **structured
incident note** (JSON with explicit fields — not a blob of prose). Everything
happens **asynchronously** through a real message bus (Kafka), with the status
machine persisted in Postgres so the client can poll for progress.

> Domain: **On-call engineering incident briefs.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        EchoBrief                             │
│                                                             │
│  Engineer                                                   │
│     │  POST /briefs (transcript | audio_url | audio_file)   │
│     ▼                                                       │
│  ┌──────────────┐                                          │
│  │  FastAPI     │ ── INSERT brief (status=received) ─────►  │
│  │  (API)       │                          PostgreSQL       │
│  └──────┬───────┘                                          │
│         │ publish echobrief.transcribe                     │
│         │ UPDATE status=queued (queued_at)                 │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │    Kafka     │   topic: echobrief.transcribe            │
│  │ (Message Bus)│   topic: echobrief.structure             │
│  └──────┬───────┘                                          │
│         │ consume echobrief.transcribe                     │
│         ▼                                                   │
│  ┌──────────────┐  UPDATE status=transcribing              │
│  │   Worker     │  mock / real (Whisper) transcription     │
│  │  (Consumer)  │  UPDATE transcript, transcribed_at       │
│  │              │  publish echobrief.structure ───────────►│
│  │              │                                          │
│  │              │  consume echobrief.structure             │
│  │              │  UPDATE status=drafting (drafted_at)     │
│  │              │  OpenRouter claude-sonnet → JSON note     │
│  │              │  validate (Pydantic) → INSERT note       │
│  │              │  UPDATE status=ready (completed_at) ─────►│
│  └──────────────┘                          PostgreSQL       │
│                                                             │
│  Engineer polls GET /briefs/{id} → structured note when    │
│  status = ready.                                           │
└─────────────────────────────────────────────────────────────┘
```

### Components
| Component | Tech | Role |
|---|---|---|
| API | FastAPI (async) | Create/list/fetch briefs, health, enqueue work |
| Message bus | Apache Kafka (+ Zookeeper) | Real async handoff, two-stage pipeline |
| Worker | Python consumer (separate process) | transcribe → structure → update DB |
| DB | PostgreSQL 16 | Briefs + structured notes, persisted status machine |
| LLM | claude-sonnet via OpenRouter | Structures transcript into JSON note |

### Status machine
```
received ─(API publishes echobrief.transcribe)─► queued
   ─(worker consumes)─► transcribing
   ─(worker publishes echobrief.structure)─► drafting
   ─(worker structures + persists)─► ready
        └─ any stage error ─► failed  (error_message stored)
```
Every transition is persisted with a timestamp: `created_at`, `queued_at`,
`transcribed_at`, `drafted_at`, `completed_at`.

---

## Run locally

**Prereqs:** Docker + Docker Compose.

```bash
git clone <repo>
cd echobrief
cp .env.example .env        # Windows: copy .env.example .env
# (optional) add your OPENROUTER_API_KEY to .env
docker compose up --build
```

- API:        http://localhost:8000
- Swagger UI:  http://localhost:8000/docs
- Health:      http://localhost:8000/health

> **No API key?** No problem. If `OPENROUTER_API_KEY` is missing/placeholder,
> the worker uses a deterministic **offline structurer** so the *entire async
> pipeline still runs end-to-end*. Add a key to get real claude-sonnet output.

The API container applies the schema on startup (`init_db.py`, idempotent and
retrying), so the first `docker compose up` is all you need.

---

## Data model

Two tables (full DDL in [`backend/schema.sql`](backend/schema.sql)):

- **`briefs`** — one row per submission; holds ingest data + the status machine
  and per-stage timestamps.
- **`structured_notes`** — 1:1 with a brief; the structured JSON note with
  explicit columns (`incident_title`, `severity`, `affected_systems`,
  `timeline`, `root_cause`, `action_items`, …) plus the full `raw_json`.

Statuses: `received → queued → transcribing → drafting → ready | failed`.

---

## API

| Method | Path | Description |
|---|---|---|
| `GET`  | `/health` | DB + Kafka connectivity |
| `POST` | `/briefs` | Create a brief (enqueues async processing) |
| `GET`  | `/briefs` | List briefs (`?status=&limit=&offset=`) |
| `GET`  | `/briefs/{id}` | Full brief incl. structured note when ready |
| `GET`  | `/briefs/{id}/note` | Structured note JSON (409 until ready) |

### Examples

```bash
# 1) Create a brief from a transcript
curl -X POST http://localhost:8000/briefs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API gateway 5xx spike",
    "engineer_name": "Nishil",
    "ingest_type": "transcript",
    "transcript": "At 14:32 UTC we started seeing elevated 5xx errors on the API gateway. Error rate peaked at 23 percent around 14:38. Root cause was Redis connection pool exhaustion after a config change deployed at 14:15. We rolled back at 14:47 and error rates normalised by 14:52. Action items: increase connection pool size, add monitoring alert, add config freeze window."
  }'
# -> { "id": "...", "title": "...", "status": "queued", "created_at": "..." }

# 2) Create a brief from an audio URL (mock-transcribed for the demo)
curl -X POST http://localhost:8000/briefs \
  -H "Content-Type: application/json" \
  -d '{"title":"Auth timeouts","engineer_name":"Priya","ingest_type":"audio_url","audio_url":"https://example.com/brief.wav"}'

# 3) Poll the brief (watch status: queued → transcribing → drafting → ready)
curl http://localhost:8000/briefs/<id>

# 4) Get just the structured note (once ready)
curl http://localhost:8000/briefs/<id>/note

# 5) List ready briefs
curl "http://localhost:8000/briefs?status=ready&limit=20"

# 6) Health
curl http://localhost:8000/health
# -> { "status": "ok", "db": "connected", "kafka": "connected" }
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
   If the worker crashes mid-processing, the message isn't lost (we use manual
   offset commits → at-least-once). Redis pub/sub would drop messages with no
   live consumer.

2. **Two-topic pipeline (`transcribe` + `structure`)** — separating stages lets
   transcription (CPU-heavy, e.g. Whisper) and structuring (I/O-heavy LLM call)
   scale independently, and makes each stage individually retryable.

3. **Mock transcription for the demo** — real Whisper adds a heavy dependency
   (model download + CPU/GPU inference). Mocking demonstrates the async pipeline
   correctly; production path is documented (`faster-whisper`).

4. **Status machine in the DB** — every transition is persisted with a
   timestamp, giving a full audit trail and letting clients show accurate
   progress without touching Kafka.

5. **Polling vs WebSockets** — clients poll `GET /briefs/{id}`. A production
   improvement is SSE/WebSocket push for real-time updates.

6. **LLM fallback** — a deterministic offline structurer keeps the pipeline
   runnable without an API key or network, while real claude-sonnet is used
   whenever a key is present.

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
│   ├── worker/
│   │   ├── consumer.py        # Kafka consumer + status machine
│   │   └── transcriber.py     # mock + documented real Whisper path
│   ├── schema.sql             # documented DDL
│   ├── init_db.py             # idempotent schema apply (with retries)
│   ├── Dockerfile             # API image
│   ├── Dockerfile.worker      # Worker image
│   └── requirements.txt
├── docker-compose.yml         # postgres + zookeeper + kafka + api + worker
├── .env.example
└── README.md
```

---

## Local dev without Docker (optional)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Point env at local services (Postgres + Kafka must be running):
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/echobrief
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
python init_db.py
uvicorn app.main:app --reload          # terminal 1: API
python -m worker.consumer              # terminal 2: worker
```
