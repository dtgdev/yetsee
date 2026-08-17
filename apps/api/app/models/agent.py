from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class AgentTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_tasks"

    task_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(80), index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), index=True)
    requested_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class AgentRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    permissions_used: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)


class AgentFinding(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_findings"

    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(80), index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(24), default="info", index=True, nullable=False)
    stance: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
