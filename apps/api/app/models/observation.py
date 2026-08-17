from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Observation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "observations"

    source: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500))
    topic: Mapped[str | None] = mapped_column(String(255), index=True)
    metric: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
