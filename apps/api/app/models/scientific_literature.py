from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class ScientificPublication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scientific_publications"
    __table_args__ = (
        UniqueConstraint("source_system", "source_id", name="uq_scientific_publication_source"),
    )

    source_system: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    pmid: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    journal: Mapped[str | None] = mapped_column(String(255))
    publication_date: Mapped[date | None] = mapped_column(Date)
    authors_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    retrieval_ref: Mapped[str | None] = mapped_column(String(1000))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)


class ScientificPassage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scientific_passages"
    __table_args__ = (
        UniqueConstraint("publication_id", "content_hash", name="uq_scientific_passage_publication_hash"),
    )

    publication_id: Mapped[str] = mapped_column(
        ForeignKey("scientific_publications.id"), index=True, nullable=False
    )
    section: Mapped[str | None] = mapped_column(String(120), index=True)
    locator: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ScientificClaim(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scientific_claims"

    publication_id: Mapped[str] = mapped_column(
        ForeignKey("scientific_publications.id"), index=True, nullable=False
    )
    passage_id: Mapped[str] = mapped_column(
        ForeignKey("scientific_passages.id"), index=True, nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(40), default="scientific_claim", nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False)
    extraction_version: Mapped[str | None] = mapped_column(String(80))
    extraction_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    canonical_evidence: Mapped[bool] = mapped_column(default=False, nullable=False)
