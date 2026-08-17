from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class DetectorRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "detector_runs"

    detector_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    detector_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class DiscoveryCandidate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "discovery_candidates"

    canonical_key: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="candidate", index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detector_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    detector_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
