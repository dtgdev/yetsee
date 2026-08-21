from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.scientific_literature import ScientificPassage, ScientificPublication

LITERATURE_STANCES = {"supporting", "contradicting", "contextual"}


def bind_passage_to_investigation(
    db: Session,
    investigation_id: str,
    passage_id: str,
    *,
    stance: str = "contextual",
    weight: float = 1.0,
) -> tuple[EvidenceLink, bool]:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")
    passage = db.get(ScientificPassage, passage_id)
    if passage is None:
        raise KeyError("Scientific passage not found")
    if stance not in LITERATURE_STANCES:
        raise ValueError("Literature evidence stance must be supporting, contradicting, or contextual")
    if weight < 0.0 or weight > 1.0:
        raise ValueError("Evidence weight must be between 0 and 1")

    existing = db.scalar(
        select(EvidenceLink).where(
            EvidenceLink.investigation_id == investigation_id,
            EvidenceLink.scientific_passage_id == passage_id,
        )
    )
    if existing is not None:
        return existing, False

    link = EvidenceLink(
        investigation_id=investigation_id,
        scientific_passage_id=passage_id,
        stance=stance,
        weight=weight,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link, True


def list_literature_evidence(db: Session, investigation_id: str) -> list[dict]:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    rows = db.execute(
        select(EvidenceLink, ScientificPassage, ScientificPublication)
        .join(ScientificPassage, EvidenceLink.scientific_passage_id == ScientificPassage.id)
        .join(ScientificPublication, ScientificPassage.publication_id == ScientificPublication.id)
        .where(EvidenceLink.investigation_id == investigation_id)
        .order_by(EvidenceLink.created_at.asc())
    ).all()

    return [
        {
            "evidence_link_id": link.id,
            "stance": link.stance,
            "weight": link.weight,
            "passage": {
                "id": passage.id,
                "section": passage.section,
                "locator": passage.locator,
                "text": passage.text,
                "content_hash": passage.content_hash,
                "provenance": passage.provenance_json,
            },
            "publication": {
                "id": publication.id,
                "pmid": publication.pmid,
                "doi": publication.doi,
                "title": publication.title,
                "journal": publication.journal,
                "publication_date": publication.publication_date.isoformat() if publication.publication_date else None,
                "source_url": publication.source_url,
                "content_hash": publication.content_hash,
            },
        }
        for link, passage, publication in rows
    ]
