from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Feature(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "features"

    subject: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    feature_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    vector: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    window: Mapped[str | None] = mapped_column(String(40), index=True)
    extractor_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)


class FeatureRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "feature_runs"

    extractor_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
