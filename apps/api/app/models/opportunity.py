from typing import Any

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Opportunity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"

    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="early", nullable=False)
    reasoning: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
