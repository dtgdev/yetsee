from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class InvestigationMission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investigation_missions"

    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
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
    __table_args__ = (UniqueConstraint("mission_id", "sequence", name="uq_mission_step_sequence"),)

    mission_id: Mapped[str] = mapped_column(ForeignKey("investigation_missions.id"), index=True, nullable=False)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    command_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    error: Mapped[str | None] = mapped_column(Text)


class ScientificDecision(UUIDMixin, TimestampMixin, Base):
    """Immutable scientific recommendation derived from one persisted synthesis."""

    __tablename__ = "scientific_decisions"
    __table_args__ = (UniqueConstraint("synthesis_finding_id", name="uq_scientific_decision_synthesis_finding"),)

    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    mission_id: Mapped[str] = mapped_column(ForeignKey("investigation_missions.id"), index=True, nullable=False)
    synthesis_finding_id: Mapped[str] = mapped_column(ForeignKey("agent_findings.id"), index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="medium", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_objective: Mapped[str] = mapped_column(Text, nullable=False)
    source_agent_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    basis_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    next_mission_id: Mapped[str | None] = mapped_column(ForeignKey("investigation_missions.id"), index=True)
    command_id: Mapped[str | None] = mapped_column(String(36), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)


class ScientificResolution(UUIDMixin, TimestampMixin, Base):
    """Deterministic before/after assessment for a decision-driven follow-up mission."""

    __tablename__ = "scientific_resolutions"
    __table_args__ = (UniqueConstraint("decision_id", name="uq_scientific_resolution_decision"),)

    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    decision_id: Mapped[str] = mapped_column(ForeignKey("scientific_decisions.id"), index=True, nullable=False)
    parent_mission_id: Mapped[str] = mapped_column(ForeignKey("investigation_missions.id"), index=True, nullable=False)
    followup_mission_id: Mapped[str] = mapped_column(ForeignKey("investigation_missions.id"), index=True, nullable=False)
    parent_synthesis_finding_id: Mapped[str] = mapped_column(ForeignKey("agent_findings.id"), index=True, nullable=False)
    followup_synthesis_finding_id: Mapped[str] = mapped_column(ForeignKey("agent_findings.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    objective_satisfied: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolution_score: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    before_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    after_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    delta_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_added_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_removed_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
