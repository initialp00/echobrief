"""SQLAlchemy ORM models mapping onto the DDL in schema.sql."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    engineer_name: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    ingest_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="received")
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transcribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    drafted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    note: Mapped["StructuredNote | None"] = relationship(
        back_populates="brief",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "ingest_type IN ('audio_url', 'audio_file', 'transcript')",
            name="briefs_ingest_type_check",
        ),
        CheckConstraint(
            "status IN ('received', 'queued', 'transcribing', 'drafting', 'ready', 'failed')",
            name="briefs_status_check",
        ),
        Index("idx_briefs_status", "status"),
        Index("idx_briefs_created_at", "created_at"),
    )


class StructuredNote(Base):
    __tablename__ = "structured_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("briefs.id", ondelete="CASCADE"), unique=True
    )
    incident_title: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    affected_systems: Mapped[list | None] = mapped_column(JSONB)
    timeline: Mapped[list | None] = mapped_column(JSONB)
    root_cause: Mapped[str | None] = mapped_column(Text)
    action_items: Mapped[list | None] = mapped_column(JSONB)
    on_call_engineer: Mapped[str | None] = mapped_column(Text)
    resolution_status: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    brief: Mapped[Brief] = relationship(back_populates="note")

    __table_args__ = (
        CheckConstraint(
            "severity IN ('P1', 'P2', 'P3', 'P4')", name="notes_severity_check"
        ),
    )
