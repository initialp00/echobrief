"""Health endpoint: reports DB + Kafka connectivity."""
import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.schemas import HealthResponse
from app.services.producer import check_kafka

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    # DB probe
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:  # noqa: BLE001
        db_status = "disconnected"

    # Kafka probe (sync client) — run off the event loop.
    kafka_ok = await asyncio.to_thread(check_kafka)
    kafka_status = "connected" if kafka_ok else "disconnected"

    overall = "ok" if db_status == "connected" and kafka_status == "connected" else "degraded"
    return HealthResponse(status=overall, db=db_status, kafka=kafka_status)
