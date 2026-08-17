from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class GraphRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "graph_runs"

    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relationship_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
