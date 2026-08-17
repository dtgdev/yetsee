from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class KernelEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "kernel_events"

    event_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    aggregate_id: Mapped[str | None] = mapped_column(String(36), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )


class KernelCommandLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "kernel_command_log"

    command_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    command_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(160), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    aggregate_id: Mapped[str | None] = mapped_column(String(36), index=True)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InvestigationRevision(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investigation_revisions"

    investigation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    author_type: Mapped[str] = mapped_column(String(40), default="system", nullable=False)
    author_id: Mapped[str | None] = mapped_column(String(120))


class WorkflowRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="running")
    target_type: Mapped[str | None] = mapped_column(String(80), index=True)
    target_id: Mapped[str | None] = mapped_column(String(36), index=True)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PluginRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "plugin_records"

    plugin_id: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    plugin_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", index=True, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
