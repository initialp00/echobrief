"""Pydantic request/response schemas + the structured-note contract."""
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class IngestType(str, Enum):
    transcript = "transcript"
    audio_url = "audio_url"
    audio_file = "audio_file"


class BriefStatus(str, Enum):
    received = "received"
    queued = "queued"
    transcribing = "transcribing"
    drafting = "drafting"
    ready = "ready"
    failed = "failed"


# --------------------------------------------------------------------------- #
# Structured note (worker output contract)
# --------------------------------------------------------------------------- #
class TimelineEntry(BaseModel):
    time: str = Field(..., description="Timestamp, e.g. '14:32 UTC'")
    event: str = Field(..., description="What happened")


class StructuredNoteData(BaseModel):
    """Validated shape of the LLM/structurer output."""

    incident_title: str
    severity: Literal["P1", "P2", "P3", "P4"]
    affected_systems: list[str] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    root_cause: str
    action_items: list[str] = Field(default_factory=list)
    on_call_engineer: str
    resolution_status: Literal["Resolved", "Ongoing", "Monitoring"]


# --------------------------------------------------------------------------- #
# API request / response models
# --------------------------------------------------------------------------- #
class BriefCreate(BaseModel):
    title: str = Field(..., examples=["API gateway 5xx spike"])
    engineer_name: str = Field(..., examples=["Nishil"])
    ingest_type: IngestType
    transcript: str | None = Field(
        default=None, description="Required when ingest_type = transcript"
    )
    audio_url: str | None = Field(
        default=None, description="Required when ingest_type = audio_url"
    )

    @model_validator(mode="after")
    def _validate_payload(self) -> "BriefCreate":
        if self.ingest_type == IngestType.transcript and not self.transcript:
            raise ValueError("transcript is required when ingest_type = 'transcript'")
        if self.ingest_type == IngestType.audio_url and not self.audio_url:
            raise ValueError("audio_url is required when ingest_type = 'audio_url'")
        return self


class BriefCreateResponse(BaseModel):
    id: UUID
    title: str
    status: BriefStatus
    created_at: datetime | None


class BriefListItem(BaseModel):
    id: UUID
    title: str
    engineer_name: str
    status: BriefStatus
    created_at: datetime | None
    completed_at: datetime | None


class BriefDetail(BaseModel):
    id: UUID
    title: str
    engineer_name: str
    ingest_type: IngestType
    status: BriefStatus
    error_message: str | None = None
    created_at: datetime | None
    queued_at: datetime | None
    transcribed_at: datetime | None
    drafted_at: datetime | None
    completed_at: datetime | None
    transcript: str | None = None
    structured_note: StructuredNoteData | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
    kafka: str
