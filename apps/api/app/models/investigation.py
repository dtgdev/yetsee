from typing import Any

from sqlalchemy import Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Investigation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investigations"

    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="emerging", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    counter_thesis: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
