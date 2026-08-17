from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Float, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(String, index=True)
    topic: Mapped[str] = mapped_column(String, index=True)
    metric: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class Trend(Base):
    __tablename__ = "trends"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    stage: Mapped[str] = mapped_column(String, default="emerging")
    momentum: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    thesis: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    trend_id: Mapped[str | None] = mapped_column(ForeignKey("trends.id"), nullable=True)
    type: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    thesis: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    stage: Mapped[str] = mapped_column(String, default="early")
    reasoning: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    trend: Mapped[Trend | None] = relationship()


class OpportunityEvidence(Base):
    __tablename__ = "opportunity_evidence"
    __table_args__ = (UniqueConstraint("opportunity_id", "signal_id", name="uq_opportunity_signal"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("signals.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String, default="supporting")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    mode: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="running", index=True)
    connector_count: Mapped[int] = mapped_column(default=0)
    signal_count: Mapped[int] = mapped_column(default=0)
    trend_count: Mapped[int] = mapped_column(default=0)
    opportunity_count: Mapped[int] = mapped_column(default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
