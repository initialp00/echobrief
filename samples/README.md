# EchoBrief — sample incident briefs

Ready-made incident briefs for exercising the **live** pipeline. Each item has a
spoken **audio** file and its matching **transcript** text.

```
samples/
├── audio/          # spoken incident briefs (.wav, 22 kHz mono, ~38–50s each)
├── transcripts/    # matching transcript text (.txt)
└── generate_audio.ps1   # regenerates the audio from text (Windows TTS)
```

| # | Scenario | Severity | Duration |
|---|---|---|---|
| 01 | API gateway 5xx spike — Redis connection pool exhaustion | P1/P2 | ~43s |
| 02 | Checkout timeouts — DB connection limit from bad autoscaling | P2 | ~50s |
| 03 | DNS resolution outage — expired resolver certificate | P1 | ~40s |
| 04 | Cache stampede — minor catalog latency blip | P4 | ~38s |

---

## How to use them

Open the dashboard (**http://localhost** — or the `WEB_PORT` you set) and submit
a brief. Set a real `OPENROUTER_API_KEY` in `.env` first.

### 1. Transcript path
Copy any file in `transcripts/` into the **Transcript** box (`ingest_type=transcript`).
Text is used as-is → Claude Sonnet structures the note via OpenRouter.

### 2. Audio path (live OpenRouter Whisper)
Serve the samples so Docker can download them:

```powershell
# from the samples/ folder
python -m http.server 8055
```

On the dashboard choose **`audio_url`** and paste:

```
http://host.docker.internal:8055/audio/01-api-gateway-redis.wav
```

Flow: worker downloads the `.wav` → OpenRouter STT (`openai/whisper-1` by default)
→ Claude structures the real transcript. No mock text.

### Via curl
```bash
curl -X POST http://localhost/api/briefs \
  -H "Content-Type: application/json" \
  -d '{"title":"DNS outage","engineer_name":"Marcus","ingest_type":"audio_url","audio_url":"http://host.docker.internal:8055/audio/03-dns-resolution-outage.wav"}'
```

---

## Regenerating the audio
```powershell
powershell -ExecutionPolicy Bypass -File samples/generate_audio.ps1
```
