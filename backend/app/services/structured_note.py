"""Turn a raw transcript into a validated StructuredNoteData object.

Primary path : OpenRouter claude-sonnet (OpenAI-compatible chat completions).
Fallback path: a deterministic offline structurer so the pipeline runs end-to-end
               without an API key (useful for demos / evaluation without network).
"""
import json
import logging
import re

from openai import OpenAI

from app.config import settings
from app.models.schemas import StructuredNoteData

logger = logging.getLogger("echobrief.structurer")

SYSTEM_PROMPT = """
You are an incident note structuring assistant for on-call engineers.
Extract structured information from incident briefs and return ONLY
valid JSON matching this exact schema. No prose, no markdown, just JSON.

Schema:
{
    "incident_title": "string - concise title of the incident",
    "severity": "P1 | P2 | P3 | P4",
    "affected_systems": ["list of affected system names"],
    "timeline": [
        {"time": "HH:MM UTC", "event": "what happened"}
    ],
    "root_cause": "string - what caused the incident",
    "action_items": ["list of follow-up action items"],
    "on_call_engineer": "string - name of engineer",
    "resolution_status": "Resolved | Ongoing | Monitoring"
}

Severity guide:
P1 = complete outage or data loss
P2 = major degradation affecting many users
P3 = partial degradation or limited impact
P4 = minor issue or cosmetic
""".strip()


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response (handles code fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]!r}")
    return json.loads(candidate[start : end + 1])


def _structure_with_llm(transcript: str, engineer_name: str) -> StructuredNoteData:
    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
    user_prompt = (
        f"On-call engineer: {engineer_name}\n\n"
        f"Structure this incident brief into the JSON schema:\n\n{transcript}"
    )
    resp = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        extra_headers={
            "HTTP-Referer": "https://github.com/echobrief",
            "X-Title": "EchoBrief",
        },
    )
    content = resp.choices[0].message.content or ""
    data = _extract_json(content)
    data.setdefault("on_call_engineer", engineer_name)
    return StructuredNoteData.model_validate(data)


# --------------------------------------------------------------------------- #
# Offline deterministic fallback
# --------------------------------------------------------------------------- #
_TIME_RE = re.compile(r"\b(\d{1,2}[:.]\d{2})\s*(?:UTC)?\b", re.IGNORECASE)
_SYSTEM_HINTS = [
    "api gateway", "api-gateway", "auth service", "auth-service", "redis",
    "database", "postgres", "kafka", "load balancer", "cache", "cdn",
    "payment", "queue", "dns",
]


def _guess_severity(transcript: str) -> str:
    t = transcript.lower()
    if any(w in t for w in ("outage", "data loss", "down", "complete")):
        return "P1"
    if any(w in t for w in ("major", "spike", "peaked", "many users", "degradation")):
        return "P2"
    if any(w in t for w in ("partial", "limited", "some")):
        return "P3"
    return "P4"


def _structure_offline(transcript: str, engineer_name: str) -> StructuredNoteData:
    """Heuristic structurer — no network needed. Not as good as the LLM, but valid."""
    logger.info("Structuring note via offline fallback (no OpenRouter key).")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript) if s.strip()]

    timeline = []
    for sentence in sentences:
        m = _TIME_RE.search(sentence)
        if m:
            timeline.append({"time": f"{m.group(1).replace('.', ':')} UTC", "event": sentence})

    lower = transcript.lower()
    affected = sorted({h for h in _SYSTEM_HINTS if h in lower})

    root_cause = next(
        (s for s in sentences if "root cause" in s.lower() or "caused" in s.lower()),
        sentences[0] if sentences else "Unknown",
    )

    action_items: list[str] = []
    if "action item" in lower:
        tail = transcript[lower.index("action item"):]
        tail = re.sub(r"(?i)action items?:?", "", tail, count=1)
        action_items = [a.strip(" .") for a in re.split(r",|\band\b|\n", tail) if a.strip(" .")]
    action_items = action_items[:8]

    resolution = "Resolved" if any(
        w in lower for w in ("rolled back", "normalised", "normalized", "resolved", "recovered")
    ) else "Monitoring"

    title = sentences[0][:80] if sentences else "Incident brief"

    data = {
        "incident_title": title,
        "severity": _guess_severity(transcript),
        "affected_systems": affected or ["unknown"],
        "timeline": timeline or [{"time": "00:00 UTC", "event": title}],
        "root_cause": root_cause,
        "action_items": action_items or ["Review incident and file follow-ups"],
        "on_call_engineer": engineer_name,
        "resolution_status": resolution,
    }
    return StructuredNoteData.model_validate(data)


def structure_note(transcript: str, engineer_name: str) -> StructuredNoteData:
    """Public entry point used by the worker."""
    if settings.llm_enabled:
        try:
            return _structure_with_llm(transcript, engineer_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM structuring failed (%s); falling back to offline.", exc)
    return _structure_offline(transcript, engineer_name)
