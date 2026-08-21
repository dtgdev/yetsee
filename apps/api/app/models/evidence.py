from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class EvidenceLink(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evidence_links"

    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True, nullable=False
    )
    observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"), index=True)
    signal_id: Mapped[str | None] = mapped_column(ForeignKey("signals.id"), index=True)
    scientific_passage_id: Mapped[str | None] = mapped_column(
        ForeignKey("scientific_passages.id"), index=True
    )
    scientific_claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("scientific_claims.id"), index=True
    )
    stance: Mapped[str] = mapped_column(String(24), default="supporting", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
