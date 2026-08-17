from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Hypothesis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hypotheses"

    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True, nullable=False)
    prior_confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    created_by_type: Mapped[str] = mapped_column(String(40), default="human", nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(String(120))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("hypotheses.id"), index=True)


class HypothesisEvidenceLink(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hypothesis_evidence_links"

    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("hypotheses.id"), index=True, nullable=False)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), index=True, nullable=False)
    stance: Mapped[str] = mapped_column(String(24), default="supporting", index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)


class HypothesisConfidenceHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hypothesis_confidence_history"

    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("hypotheses.id"), index=True, nullable=False)
    old_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    new_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    prior_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    supporting_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    contradicting_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    neutral_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str] = mapped_column(String(80), default="manual", index=True, nullable=False)
    observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"), index=True)
