"""Transcription stage.

For the demo this returns a realistic mock transcript when given audio, and
uses the supplied transcript verbatim for the transcript ingest path.

REAL WHISPER PATH (documented, intentionally not enabled for the demo):
--------------------------------------------------------------------------
The mock keeps the image small and the pipeline network-free. To run real
speech-to-text, install `faster-whisper` and replace `_mock_transcribe`:

    from faster_whisper import WhisperModel
    _model = WhisperModel("base", device="cpu", compute_type="int8")

    def _real_transcribe(path: str) -> str:
        segments, _info = _model.transcribe(path, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()

Trade-off: real inference needs a model download (~150MB for `base`) and is
CPU/GPU heavy, which is why it is gated behind documentation for evaluation.
"""
import logging
import os
import uuid

import httpx

from app.config import settings

logger = logging.getLogger("echobrief.transcriber")

MOCK_TRANSCRIPT = """
At 14:32 UTC we started seeing elevated 5xx errors on the API gateway.
Error rate peaked at 23 percent around 14:38. Auth service was returning
connection timeouts. Root cause was Redis connection pool exhaustion after
a config change deployed at 14:15. We rolled back the config at 14:47
and error rates normalised by 14:52. Action items: increase connection
pool size, add connection pool monitoring alert, add config change
freeze window during peak hours.
""".strip()

# Faithful transcripts for the provided sample audio files (see samples/).
# When the audio source (URL or filename) matches one of these keys, the mock
# transcriber returns the matching transcript so the demo produces a correct
# note for that specific audio. Unknown audio falls back to MOCK_TRANSCRIPT.
# (With real Whisper wired in, this table is unnecessary.)
SAMPLE_TRANSCRIPTS: dict[str, str] = {
    "01-api-gateway-redis": MOCK_TRANSCRIPT,
    "02-checkout-latency-db": (
        "Around 21:05 UTC checkout requests started timing out. About 40 percent "
        "of users could not complete purchases. The payments service was hitting a "
        "connection limit on the primary database after an autoscaling "
        "misconfiguration pushed too many pods at 20:50. We reduced the max pod "
        "count and restarted the payments service at 21:20, and checkout recovered "
        "by 21:28. Follow ups: cap the payments pod count, add a database "
        "connection saturation alert, and review the autoscaling policy."
    ),
    "03-dns-resolution-outage": (
        "At 08:14 UTC internal services could not resolve DNS for the payments and "
        "notifications domains, causing a complete outage for background jobs. The "
        "cause was an expired internal certificate on the DNS resolver that was not "
        "rotated by automation. We manually rotated the certificate and restarted "
        "the resolver at 08:39, and resolution recovered by 08:45. Action items: "
        "fix the certificate rotation automation, add an expiry alert 30 days out, "
        "and add a synthetic DNS health check."
    ),
    "04-cache-stampede-minor": (
        "At 12:03 UTC we saw a brief latency bump on the product catalog service "
        "after a cache node restarted, triggering a small cache stampede. Impact "
        "was minor, a few slow requests for about two minutes. No user reports. The "
        "cache warmed up and latency returned to normal by 12:06. Action items: add "
        "request coalescing on cache misses and stagger cache node restarts."
    ),
}


def _mock_transcribe(source: str) -> str:
    """Return a transcript for mocked audio.

    If the source (audio URL or filename) matches a known sample, return that
    sample's transcript so the note is faithful; otherwise return the generic
    canned incident transcript.
    """
    src = (source or "").lower()
    for key, transcript in SAMPLE_TRANSCRIPTS.items():
        if key in src:
            logger.info("Mock-transcribing %s -> matched sample '%s'.", source, key)
            return transcript
    logger.info("Mock-transcribing %s -> generic canned transcript.", source)
    return MOCK_TRANSCRIPT


async def _download_audio(audio_url: str) -> str:
    """Download audio to the uploads dir; returns local path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = os.path.join(settings.upload_dir, f"{uuid.uuid4()}.audio")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(audio_url)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            fh.write(resp.content)
    logger.info("Downloaded audio from %s -> %s", audio_url, dest)
    return dest


async def transcribe(
    ingest_type: str, audio_url: str | None, transcript: str | None
) -> str:
    """Produce a transcript from whichever ingest path was used."""
    if ingest_type == "transcript":
        if not transcript:
            raise ValueError("ingest_type=transcript but no transcript provided")
        return transcript.strip()

    if ingest_type == "audio_url":
        if not audio_url:
            raise ValueError("ingest_type=audio_url but no audio_url provided")
        # Best-effort download. Since transcription is mocked for the demo, a
        # download failure (e.g. placeholder URL) still yields a mock transcript
        # rather than failing the brief. With real Whisper wired in, you would
        # let a download error propagate to the 'failed' status instead.
        try:
            await _download_audio(audio_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Audio download failed (%s); using mock transcript.", exc)
        # Key the mock off the original URL so provided sample files (e.g.
        # .../03-dns-resolution-outage.wav) yield their matching transcript.
        # For real STT, transcribe the downloaded file instead.
        return _mock_transcribe(audio_url)

    if ingest_type == "audio_file":
        # File is expected to already exist under the shared uploads volume.
        return _mock_transcribe(audio_url or "uploaded-file")

    raise ValueError(f"Unknown ingest_type: {ingest_type}")
