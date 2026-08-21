from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificClaim, ScientificPassage, ScientificPublication


def _entity(db: Session, *, kind: str, canonical_name: str, canonical_key: str) -> Entity:
    existing = db.scalar(select(Entity).where(Entity.canonical_key == canonical_key))
    if existing is not None:
        return existing
    entity = Entity(
        kind=kind,
        canonical_name=canonical_name,
        canonical_key=canonical_key,
        aliases=[],
        attributes={"scientific_grounding": True},
    )
    db.add(entity)
    db.flush()
    return entity


def ground_claim_relationship(
    db: Session,
    *,
    passage_id: str,
    claim_text: str,
    subject_kind: str,
    subject_name: str,
    subject_key: str,
    predicate: str,
    object_kind: str,
    object_name: str,
    object_key: str,
    investigation_id: str | None = None,
    extraction_method: str = "manual",
    extraction_version: str = "l2-v1",
) -> tuple[ScientificClaim, Relationship, bool]:
    passage = db.get(ScientificPassage, passage_id)
    if passage is None:
        raise KeyError("Scientific passage not found")
    publication = db.get(ScientificPublication, passage.publication_id)
    if publication is None:
        raise KeyError("Scientific publication not found")

    if investigation_id is not None:
        if db.get(Investigation, investigation_id) is None:
            raise KeyError("Investigation not found")
        evidence_link = db.scalar(
            select(EvidenceLink).where(
                EvidenceLink.investigation_id == investigation_id,
                EvidenceLink.scientific_passage_id == passage_id,
            )
        )
        if evidence_link is None:
            raise ValueError("Scientific passage must be attached to the investigation as evidence before grounding")

    existing_claim = db.scalar(
        select(ScientificClaim).where(
            ScientificClaim.passage_id == passage_id,
            ScientificClaim.claim_text == claim_text,
        )
    )
    if existing_claim is not None:
        relationship_id = existing_claim.extraction_json.get("relationship_id")
        relationship = db.get(Relationship, relationship_id) if relationship_id else None
        if relationship is not None:
            if investigation_id is not None:
                relationship.provenance = {
                    **relationship.provenance,
                    "investigation_ids": sorted(set([*relationship.provenance.get("investigation_ids", []), investigation_id])),
                }
                db.commit()
                db.refresh(relationship)
            return existing_claim, relationship, False

    subject = _entity(db, kind=subject_kind, canonical_name=subject_name, canonical_key=subject_key)
    obj = _entity(db, kind=object_kind, canonical_name=object_name, canonical_key=object_key)

    claim = existing_claim or ScientificClaim(
        publication_id=publication.id,
        passage_id=passage.id,
        claim_text=claim_text,
        claim_type="relationship",
        extraction_method=extraction_method,
        extraction_version=extraction_version,
        extraction_json={},
        canonical_evidence=False,
    )
    if existing_claim is None:
        db.add(claim)
        db.flush()

    relationship = db.scalar(
        select(Relationship).where(
            Relationship.source_entity_id == subject.id,
            Relationship.target_entity_id == obj.id,
            Relationship.kind == predicate,
        )
    )
    created = relationship is None
    if relationship is None:
        relationship = Relationship(
            source_entity_id=subject.id,
            target_entity_id=obj.id,
            kind=predicate,
            confidence=1.0,
            evidence_ids=[passage.id],
            provenance={},
        )
        db.add(relationship)
        db.flush()
    elif passage.id not in relationship.evidence_ids:
        relationship.evidence_ids = [*relationship.evidence_ids, passage.id]

    relationship.provenance = {
        **relationship.provenance,
        "scientific_grounding": True,
        "claim_ids": sorted(set([*relationship.provenance.get("claim_ids", []), claim.id])),
        "passage_ids": sorted(set([*relationship.provenance.get("passage_ids", []), passage.id])),
        "publication_ids": sorted(set([*relationship.provenance.get("publication_ids", []), publication.id])),
        "pmids": sorted(set([*relationship.provenance.get("pmids", []), *([publication.pmid] if publication.pmid else [])])),
        "dois": sorted(set([*relationship.provenance.get("dois", []), *([publication.doi] if publication.doi else [])])),
        "investigation_ids": sorted(set([*relationship.provenance.get("investigation_ids", []), *([investigation_id] if investigation_id else [])])),
        "canonical_evidence_kind": "scientific_passage",
    }
    claim.extraction_json = {
        **claim.extraction_json,
        "subject_entity_id": subject.id,
        "predicate": predicate,
        "object_entity_id": obj.id,
        "relationship_id": relationship.id,
        "source_passage_id": passage.id,
        "source_publication_id": publication.id,
        "investigation_id": investigation_id,
    }
    db.commit()
    db.refresh(claim)
    db.refresh(relationship)
    return claim, relationship, created
