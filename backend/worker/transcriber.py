"""Transcription stage.

- transcript ingest: use the supplied text as-is
- audio ingest: download (or open local file) → OpenRouter speech-to-text

Requires OPENROUTER_API_KEY. Uses OPENROUTER_STT_MODEL (default openai/whisper-1).
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger("echobrief.transcriber")

_SUPPORTED_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".webm", ".aac", ".mp4"}


def _require_api_key() -> None:
    if not settings.llm_enabled:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for audio transcription "
            "(OpenRouter speech-to-text). Set it in .env and restart."
        )


def _extension_from_url_or_name(source: str) -> str:
    path = urlparse(source).path if "://" in source else source
    ext = Path(path).suffix.lower()
    if ext in _SUPPORTED_EXTS:
        return ext
    return ".wav"


def _format_from_path(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    if ext == "mp4":
        return "m4a"
    if ext in {"wav", "mp3", "flac", "m4a", "ogg", "webm", "aac"}:
        return ext
    return "wav"


async def _download_audio(audio_url: str) -> str:
    """Download audio to the uploads dir; returns local path with a real extension."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = _extension_from_url_or_name(audio_url)
    dest = os.path.join(settings.upload_dir, f"{uuid.uuid4()}{ext}")
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(audio_url)
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        guessed = mimetypes.guess_extension(ctype) if ctype.startswith("audio/") else None
        if (
            guessed
            and Path(dest).suffix.lower() == ".wav"
            and guessed.lower() in _SUPPORTED_EXTS
        ):
            dest = os.path.splitext(dest)[0] + guessed.lower()
        with open(dest, "wb") as fh:
            fh.write(resp.content)
    logger.info(
        "Downloaded audio from %s -> %s (%s bytes)",
        audio_url,
        dest,
        os.path.getsize(dest),
    )
    return dest


def _transcribe_file_openrouter(path: str) -> str:
    """POST base64 audio to OpenRouter /api/v1/audio/transcriptions."""
    _require_api_key()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Audio file not found: {path}")
    if os.path.getsize(path) == 0:
        raise ValueError(f"Audio file is empty: {path}")

    fmt = _format_from_path(path)
    with open(path, "rb") as fh:
        audio_b64 = base64.b64encode(fh.read()).decode("ascii")

    url = settings.openrouter_base_url.rstrip("/") + "/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/echobrief",
        "X-Title": "EchoBrief",
    }
    payload = {
        "model": settings.openrouter_stt_model,
        "input_audio": {"data": audio_b64, "format": fmt},
        "language": "en",
    }
    logger.info(
        "OpenRouter STT model=%s file=%s format=%s bytes=%s",
        settings.openrouter_stt_model,
        path,
        fmt,
        os.path.getsize(path),
    )
    with httpx.Client(timeout=120) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter STT failed ({resp.status_code}): {resp.text[:500]}"
            )
        data = resp.json()

    text = (data.get("text") or "").strip()
    if not text:
        raise RuntimeError(f"OpenRouter STT returned empty transcript: {data!r}")
    logger.info("OpenRouter STT ok (%s chars)", len(text))
    return text


def _resolve_local_audio(path_or_name: str) -> str:
    """Resolve audio_file ingest to a path under the shared uploads volume."""
    if os.path.isabs(path_or_name) and os.path.isfile(path_or_name):
        return path_or_name
    candidate = os.path.join(settings.upload_dir, path_or_name)
    if os.path.isfile(candidate):
        return candidate
    raise FileNotFoundError(
        f"audio_file not found under uploads: {path_or_name!r} "
        f"(looked in {settings.upload_dir})"
    )


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
        path = await _download_audio(audio_url)
        return _transcribe_file_openrouter(path)

    if ingest_type == "audio_file":
        if not audio_url:
            raise ValueError("ingest_type=audio_file but no file path provided")
        path = _resolve_local_audio(audio_url)
        return _transcribe_file_openrouter(path)

    raise ValueError(f"Unknown ingest_type: {ingest_type}")
