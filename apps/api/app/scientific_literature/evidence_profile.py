from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificPassage, ScientificPublication


def relationship_evidence_profile(db: Session, *, investigation_id: str, relationship_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")
    relationship = db.get(Relationship, relationship_id)
    if relationship is None:
        raise KeyError("Relationship not found")

    subject = db.get(Entity, relationship.source_entity_id)
    obj = db.get(Entity, relationship.target_entity_id)
    passage_ids = set(relationship.evidence_ids or [])
    rows = []
    if passage_ids:
        rows = db.execute(
            select(EvidenceLink, ScientificPassage, ScientificPublication)
            .join(ScientificPassage, EvidenceLink.scientific_passage_id == ScientificPassage.id)
            .join(ScientificPublication, ScientificPassage.publication_id == ScientificPublication.id)
            .where(
                EvidenceLink.investigation_id == investigation_id,
                EvidenceLink.scientific_passage_id.in_(passage_ids),
            )
        ).all()

    stance_counts = Counter(link.stance for link, _, _ in rows)
    publication_ids = {publication.id for _, _, publication in rows}
    weighted_support = sum(link.weight for link, _, _ in rows if link.stance == "supporting")
    weighted_contradiction = sum(link.weight for link, _, _ in rows if link.stance == "contradicting")
    supporting = stance_counts["supporting"]
    contradicting = stance_counts["contradicting"]
    contextual = stance_counts["contextual"]

    if supporting and contradicting:
        agreement = "mixed"
    elif supporting:
        agreement = "supporting_consensus"
    elif contradicting:
        agreement = "contradicting_consensus"
    elif contextual:
        agreement = "context_only"
    else:
        agreement = "no_evidence"

    independent_count = len(publication_ids)
    if supporting >= 3 and contradicting == 0 and independent_count >= 3:
        strength = "strong"
    elif supporting >= 2 and contradicting == 0 and independent_count >= 2:
        strength = "moderate"
    elif supporting >= 1 and contradicting == 0:
        strength = "limited"
    elif supporting and contradicting:
        strength = "contested"
    else:
        strength = "insufficient"

    return {
        "relationship_id": relationship.id,
        "investigation_id": investigation_id,
        "subject": subject.canonical_name if subject else relationship.source_entity_id,
        "predicate": relationship.kind,
        "object": obj.canonical_name if obj else relationship.target_entity_id,
        "supporting_count": supporting,
        "contradicting_count": contradicting,
        "contextual_count": contextual,
        "independent_publication_count": independent_count,
        "agreement": agreement,
        "strength": strength,
        "weighted_support": weighted_support,
        "weighted_contradiction": weighted_contradiction,
        "sources": [
            {
                "evidence_link_id": link.id,
                "stance": link.stance,
                "weight": link.weight,
                "passage_id": passage.id,
                "publication_id": publication.id,
                "pmid": publication.pmid,
                "doi": publication.doi,
                "title": publication.title,
                "source_url": publication.source_url,
                "text": passage.text,
            }
            for link, passage, publication in rows
        ],
    }


def investigation_evidence_profiles(db: Session, *, investigation_id: str) -> list[dict]:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")
    relationships = db.scalars(select(Relationship)).all()
    scoped = [
        relationship
        for relationship in relationships
        if investigation_id in (relationship.provenance or {}).get("investigation_ids", [])
    ]
    return [
        relationship_evidence_profile(db, investigation_id=investigation_id, relationship_id=relationship.id)
        for relationship in scoped
    ]
