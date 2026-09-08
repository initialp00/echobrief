"""EchoBrief worker: consumes the two-stage Kafka pipeline and drives the
status machine in Postgres.

    echobrief.transcribe  -->  transcribe  -->  echobrief.structure
    echobrief.structure   -->  structure   -->  status = ready

Run:  python -m worker.consumer
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from kafka import KafkaConsumer
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.db import Brief, StructuredNote
from app.services.producer import close_producer, publish
from app.services.structured_note import structure_note
from worker.transcriber import transcribe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("echobrief.worker")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _set_failed(brief_id: UUID, error: str) -> None:
    async with SessionLocal() as session:
        brief = await session.get(Brief, brief_id)
        if brief is not None:
            brief.status = "failed"
            brief.error_message = error[:2000]
            await session.commit()
    logger.error("Brief %s marked failed: %s", brief_id, error)


# --------------------------------------------------------------------------- #
# Stage 1: transcribe
# --------------------------------------------------------------------------- #
async def handle_transcribe(payload: dict) -> None:
    brief_id = UUID(payload["brief_id"])
    logger.info("[transcribe] brief=%s", brief_id)

    async with SessionLocal() as session:
        brief = await session.get(Brief, brief_id)
        if brief is None:
            logger.warning("Brief %s not found; skipping.", brief_id)
            return
        brief.status = "transcribing"
        await session.commit()

    transcript = await transcribe(
        payload.get("ingest_type"),
        payload.get("audio_url"),
        payload.get("transcript"),
    )

    async with SessionLocal() as session:
        brief = await session.get(Brief, brief_id)
        brief.transcript = transcript
        brief.transcribed_at = _now()
        await session.commit()

    # Hand off to the structuring stage.
    await asyncio.to_thread(
        publish,
        settings.kafka_topic_structure,
        {"brief_id": str(brief_id), "transcript": transcript},
        str(brief_id),
    )
    logger.info("[transcribe] brief=%s -> published to structure", brief_id)


# --------------------------------------------------------------------------- #
# Stage 2: structure
# --------------------------------------------------------------------------- #
async def handle_structure(payload: dict) -> None:
    brief_id = UUID(payload["brief_id"])
    transcript = payload["transcript"]
    logger.info("[structure] brief=%s", brief_id)

    async with SessionLocal() as session:
        brief = await session.get(Brief, brief_id)
        if brief is None:
            logger.warning("Brief %s not found; skipping.", brief_id)
            return
        brief.status = "drafting"
        brief.drafted_at = _now()
        engineer_name = brief.engineer_name
        await session.commit()

    # LLM (or offline fallback) — blocking, so run off the loop.
    note_data = await asyncio.to_thread(structure_note, transcript, engineer_name)
    raw = note_data.model_dump()

    async with SessionLocal() as session:
        # Upsert-ish: remove any prior note (unique brief_id) then insert.
        existing = await session.execute(
            select(StructuredNote).where(StructuredNote.brief_id == brief_id)
        )
        prior = existing.scalar_one_or_none()
        if prior is not None:
            await session.delete(prior)
            await session.flush()

        session.add(
            StructuredNote(
                brief_id=brief_id,
                incident_title=note_data.incident_title,
                severity=note_data.severity,
                affected_systems=note_data.affected_systems,
                timeline=raw["timeline"],
                root_cause=note_data.root_cause,
                action_items=note_data.action_items,
                on_call_engineer=note_data.on_call_engineer,
                resolution_status=note_data.resolution_status,
                raw_json=raw,
            )
        )
        brief = await session.get(Brief, brief_id)
        brief.status = "ready"
        brief.completed_at = _now()
        await session.commit()

    logger.info("[structure] brief=%s -> ready", brief_id)


# --------------------------------------------------------------------------- #
# Dispatch + main loop
# --------------------------------------------------------------------------- #
async def dispatch(topic: str, payload: dict) -> None:
    brief_id = payload.get("brief_id", "unknown")
    try:
        if topic == settings.kafka_topic_transcribe:
            await handle_transcribe(payload)
        elif topic == settings.kafka_topic_structure:
            await handle_structure(payload)
        else:
            logger.warning("Unknown topic: %s", topic)
    except Exception as exc:  # noqa: BLE001 - any stage failure -> failed status
        logger.exception("Error processing %s for brief %s", topic, brief_id)
        try:
            await _set_failed(UUID(str(brief_id)), f"{topic}: {exc}")
        except Exception:  # noqa: BLE001
            logger.exception("Could not persist failed status for %s", brief_id)


def _build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        settings.kafka_topic_transcribe,
        settings.kafka_topic_structure,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        group_id=settings.kafka_consumer_group,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        max_poll_records=10,
    )


async def run() -> None:
    consumer: KafkaConsumer | None = None
    # Kafka may still be electing a leader when the worker starts.
    for attempt in range(1, 31):
        try:
            consumer = _build_consumer()
            break
        except Exception as exc:  # noqa: BLE001
            logger.info("Kafka not ready (attempt %s/30): %s", attempt, exc)
            await asyncio.sleep(2)
    if consumer is None:
        raise RuntimeError("Could not connect to Kafka after 30 attempts")

    logger.info(
        "Worker consuming from [%s, %s] group=%s",
        settings.kafka_topic_transcribe,
        settings.kafka_topic_structure,
        settings.kafka_consumer_group,
    )
    loop = asyncio.get_running_loop()
    try:
        while True:
            batches = await loop.run_in_executor(
                None, lambda: consumer.poll(timeout_ms=1000)
            )
            if not batches:
                continue
            for _tp, messages in batches.items():
                for message in messages:
                    await dispatch(message.topic, message.value)
            # Manual commit -> at-least-once processing.
            await loop.run_in_executor(None, consumer.commit)
    finally:
        consumer.close()
        close_producer()


if __name__ == "__main__":
    asyncio.run(run())
