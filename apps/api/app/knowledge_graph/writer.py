from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.ontology import (
    ONTOLOGY_VERSION,
    entity_type_spec,
    relationship_endpoints_valid,
    relationship_type_spec,
)
from app.models.entity import Entity
from app.models.relationship import Relationship


def governed_entity(
    db: Session,
    *,
    kind: str,
    canonical_name: str,
    canonical_key: str,
    aliases: Iterable[str] = (),
    description: str | None = None,
    attributes: dict | None = None,
) -> Entity:
    spec = entity_type_spec(kind)
    if spec is None:
        raise ValueError(f"Unregistered ontology entity type: {kind}")

    existing = db.scalar(select(Entity).where(Entity.canonical_key == canonical_key))
    if existing is not None:
        if existing.kind != kind:
            raise ValueError(
                f"Ontology kind mismatch for {canonical_key}: existing={existing.kind}, requested={kind}"
            )
        existing.aliases = list(dict.fromkeys([*existing.aliases, *aliases]))
        merged_attributes = {**(existing.attributes or {}), **(attributes or {})}
        for key in set(existing.attributes or {}) | set(attributes or {}):
            left = (existing.attributes or {}).get(key)
            right = (attributes or {}).get(key)
            if key.endswith("_ids") and isinstance(left, list) and isinstance(right, list):
                merged_attributes[key] = list(dict.fromkeys([*left, *right]))
        existing.attributes = {
            **merged_attributes,
            "ontology": {
                "version": ONTOLOGY_VERSION,
                "domain": spec.domain,
                "kind": kind,
                "governed": True,
            },
        }
        return existing

    entity = Entity(
        kind=kind,
        canonical_name=canonical_name,
        canonical_key=canonical_key,
        aliases=list(dict.fromkeys(aliases)),
        description=description,
        attributes={
            **(attributes or {}),
            "ontology": {
                "version": ONTOLOGY_VERSION,
                "domain": spec.domain,
                "kind": kind,
                "governed": True,
            },
        },
    )
    db.add(entity)
    db.flush()
    return entity


def _merge_provenance(existing: dict, incoming: dict) -> dict:
    merged = {**existing, **incoming}
    for key in set(existing) | set(incoming):
        left = existing.get(key)
        right = incoming.get(key)
        if key.endswith("_ids") and isinstance(left, list) and isinstance(right, list):
            merged[key] = list(dict.fromkeys([*left, *right]))
    return merged


def governed_relationship(
    db: Session,
    *,
    source: Entity,
    target: Entity,
    kind: str,
    confidence: float = 1.0,
    evidence_ids: Iterable[str] = (),
    first_seen: datetime | None = None,
    last_seen: datetime | None = None,
    provenance: dict,
) -> Relationship:
    spec = relationship_type_spec(kind)
    if spec is None:
        raise ValueError(f"Unregistered ontology relationship type: {kind}")
    if not relationship_endpoints_valid(kind, source.kind, target.kind):
        raise ValueError(
            f"Ontology endpoint mismatch for {kind}: {source.kind} -> {target.kind}"
        )
    if not provenance:
        raise ValueError("Governed relationships require provenance")

    existing = db.scalar(
        select(Relationship).where(
            Relationship.source_entity_id == source.id,
            Relationship.target_entity_id == target.id,
            Relationship.kind == kind,
        )
    )
    ontology_provenance = {
        "ontology": {
            "version": ONTOLOGY_VERSION,
            "domain": spec.domain,
            "kind": kind,
            "governed": True,
        }
    }
    ids = list(dict.fromkeys(evidence_ids))

    if existing is not None:
        existing.evidence_ids = list(dict.fromkeys([*existing.evidence_ids, *ids]))
        existing.confidence = max(existing.confidence, max(0.0, min(1.0, confidence)))
        if first_seen is not None:
            existing.first_seen = first_seen if existing.first_seen is None else min(existing.first_seen, first_seen)
        if last_seen is not None:
            existing.last_seen = last_seen if existing.last_seen is None else max(existing.last_seen, last_seen)
        merged_provenance = _merge_provenance(existing.provenance or {}, provenance)
        existing.provenance = {
            **merged_provenance,
            **ontology_provenance,
            "evidence_count": len(existing.evidence_ids),
        }
        return existing

    relationship = Relationship(
        source_entity_id=source.id,
        target_entity_id=target.id,
        kind=kind,
        confidence=max(0.0, min(1.0, confidence)),
        evidence_ids=ids,
        first_seen=first_seen,
        last_seen=last_seen,
        provenance={
            **provenance,
            **ontology_provenance,
            "evidence_count": len(ids),
        },
    )
    db.add(relationship)
    db.flush()
    return relationship
