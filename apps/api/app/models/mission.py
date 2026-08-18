from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class InvestigationMission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investigation_missions"

    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True, nullable=False
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(100), default="human", nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    command_id: Mapped[str | None] = mapped_column(String(36), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    error: Mapped[str | None] = mapped_column(Text)


class InvestigationMissionStep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investigation_mission_steps"
    __table_args__ = (
        UniqueConstraint("mission_id", "sequence", name="uq_mission_step_sequence"),
    )

    mission_id: Mapped[str] = mapped_column(
        ForeignKey("investigation_missions.id"), index=True, nullable=False
    )
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    error: Mapped[str | None] = mapped_column(Text)
