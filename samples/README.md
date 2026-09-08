# EchoBrief — sample incident briefs

Ready-made incident briefs for exercising the pipeline. Each item has a spoken
**audio** file and its matching **transcript** text.

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

Open the dashboard (**http://localhost** — or the `WEB_PORT` you set, e.g.
http://localhost:8090) and submit a brief. There are two ingest paths:

### 1. Transcript path (fully real, recommended)
Copy the contents of any file in `transcripts/` into the **Transcript** box on
the dashboard (ingest type = `transcript`) and submit. The text is used verbatim
and structured by claude-sonnet — no transcription step involved.

### 2. Audio path (`audio_url`)
On the dashboard choose ingest type **`audio_url`** and paste a URL whose file
name matches a sample, e.g.:

```
http://demo/03-dns-resolution-outage.wav
```

> **How transcription works in the demo:** audio is **mock-transcribed** (per the
> spec — real Whisper is documented but not enabled). The mock recognises the
> sample file name in the URL and returns *that brief's* transcript, so you get a
> faithful note for the audio you picked. Unknown audio yields a generic incident
> transcript. The URL does **not** need to be reachable — download is best-effort.

### 2b. Audio path with a real, reachable URL (optional)
If you want the worker to actually **download** the file, serve this folder over
HTTP and use a `host.docker.internal` URL (reachable from inside the containers):

```powershell
# from the samples/ folder
python -m http.server 8055
```

Then submit `audio_url`:
```
http://host.docker.internal:8055/audio/03-dns-resolution-outage.wav
```
The file is downloaded, then mock-transcribed (matched by file name).

### Via curl
```bash
curl -X POST http://localhost:8090/api/briefs \
  -H "Content-Type: application/json" \
  -d '{"title":"DNS outage","engineer_name":"Marcus","ingest_type":"audio_url","audio_url":"http://demo/03-dns-resolution-outage.wav"}'
```

---

## Enabling real speech-to-text (production path)
The `.wav` files are genuine spoken audio, so they also work with real STT. To
transcribe them for real, install `faster-whisper` and swap `_mock_transcribe`
for `_real_transcribe` in [`backend/worker/transcriber.py`](../backend/worker/transcriber.py).

## Regenerating the audio
```powershell
powershell -ExecutionPolicy Bypass -File samples/generate_audio.ps1
```
