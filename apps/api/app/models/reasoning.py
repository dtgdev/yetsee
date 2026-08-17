from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class ReasoningRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reasoning_runs"

    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    reasoner_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    reasoner_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="running")
    triggered_by: Mapped[str] = mapped_column(String(80), default="human", nullable=False)
    command_id: Mapped[str | None] = mapped_column(String(36), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    input_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReasoningResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reasoning_results"

    run_id: Mapped[str] = mapped_column(ForeignKey("reasoning_runs.id"), unique=True, index=True, nullable=False)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    reasoner_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    support_level: Mapped[str] = mapped_column(String(40), nullable=False)
    supporting_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    contradicting_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recommended_evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
