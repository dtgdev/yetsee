from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class Entity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "entities"

    kind: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
