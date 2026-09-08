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


def _mock_transcribe(source: str) -> str:
    logger.info("Mock-transcribing %s -> canned incident transcript.", source)
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
            local_path = await _download_audio(audio_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Audio download failed (%s); using mock transcript.", exc)
            local_path = audio_url
        return _mock_transcribe(local_path)  # swap for _real_transcribe(local_path)

    if ingest_type == "audio_file":
        # File is expected to already exist under the shared uploads volume.
        return _mock_transcribe(audio_url or "uploaded-file")

    raise ValueError(f"Unknown ingest_type: {ingest_type}")
