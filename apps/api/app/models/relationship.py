from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Relationship(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "relationships"

    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
