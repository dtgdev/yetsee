from typing import Any

from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Signal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "signals"

    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detector: Mapped[str] = mapped_column(String(120), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
