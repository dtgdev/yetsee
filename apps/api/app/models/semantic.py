from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class SemanticRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "semantic_runs"

    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observation_count: Mapped[int] = mapped_column(default=0, nullable=False)
    concept_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class SemanticConcept(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "semantic_concepts"
    __table_args__ = (
        UniqueConstraint("observation_id", "canonical_key", "extractor_version", name="uq_semantic_concept_observation_key_version"),
    )

    observation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    mention_text: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(40), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
