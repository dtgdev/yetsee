from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class ConnectorRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "connector_runs"

    connector_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    connector_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cursor_before: Mapped[str | None] = mapped_column(Text)
    cursor_after: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ConnectorState(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "connector_states"

    connector_id: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    cursor: Mapped[str | None] = mapped_column(Text)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
