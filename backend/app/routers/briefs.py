"""Brief CRUD + async pipeline kickoff."""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.db import Brief
from app.models.schemas import (
    BriefCreate,
    BriefCreateResponse,
    BriefDetail,
    BriefListItem,
    BriefStatus,
    StructuredNoteData,
)
from app.services.producer import publish

logger = logging.getLogger("echobrief.api")
router = APIRouter(prefix="/briefs", tags=["briefs"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_detail(brief: Brief) -> BriefDetail:
    note = None
    if brief.note is not None:
        note = StructuredNoteData.model_validate(brief.note.raw_json)
    return BriefDetail(
        id=brief.id,
        title=brief.title,
        engineer_name=brief.engineer_name,
        ingest_type=brief.ingest_type,
        status=brief.status,
        error_message=brief.error_message,
        created_at=brief.created_at,
        queued_at=brief.queued_at,
        transcribed_at=brief.transcribed_at,
        drafted_at=brief.drafted_at,
        completed_at=brief.completed_at,
        transcript=brief.transcript,
        structured_note=note,
    )


@router.post("", response_model=BriefCreateResponse, status_code=201)
async def create_brief(
    payload: BriefCreate, session: AsyncSession = Depends(get_session)
) -> BriefCreateResponse:
    brief = Brief(
        title=payload.title,
        engineer_name=payload.engineer_name,
        ingest_type=payload.ingest_type.value,
        transcript=payload.transcript,
        audio_url=payload.audio_url,
        status=BriefStatus.received.value,
    )
    session.add(brief)
    await session.commit()
    await session.refresh(brief)

    message = {
        "brief_id": str(brief.id),
        "ingest_type": brief.ingest_type,
        "audio_url": brief.audio_url,
        "transcript": brief.transcript,
    }

    try:
        # Kafka client is synchronous; keep the event loop free.
        await asyncio.to_thread(
            publish, settings.kafka_topic_transcribe, message, str(brief.id)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to publish brief %s to Kafka", brief.id)
        brief.status = BriefStatus.failed.value
        brief.error_message = f"Failed to enqueue: {exc}"
        await session.commit()
        raise HTTPException(status_code=503, detail="Message bus unavailable") from exc

    brief.status = BriefStatus.queued.value
    brief.queued_at = _now()
    await session.commit()
    await session.refresh(brief)

    return BriefCreateResponse(
        id=brief.id,
        title=brief.title,
        status=BriefStatus.queued,
        created_at=brief.created_at,
    )


@router.get("", response_model=list[BriefListItem])
async def list_briefs(
    status: BriefStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[BriefListItem]:
    stmt = select(Brief).order_by(Brief.created_at.desc()).limit(limit).offset(offset)
    if status is not None:
        stmt = stmt.where(Brief.status == status.value)
    result = await session.execute(stmt)
    briefs = result.scalars().all()
    return [
        BriefListItem(
            id=b.id,
            title=b.title,
            engineer_name=b.engineer_name,
            status=b.status,
            created_at=b.created_at,
            completed_at=b.completed_at,
        )
        for b in briefs
    ]


@router.get("/{brief_id}", response_model=BriefDetail)
async def get_brief(
    brief_id: UUID, session: AsyncSession = Depends(get_session)
) -> BriefDetail:
    brief = await session.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return _to_detail(brief)


@router.get("/{brief_id}/note")
async def get_note(
    brief_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    brief = await session.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    if brief.status != BriefStatus.ready.value or brief.note is None:
        raise HTTPException(
            status_code=409,
            detail=f"Note not ready (current status: {brief.status})",
        )
    return brief.note.raw_json
