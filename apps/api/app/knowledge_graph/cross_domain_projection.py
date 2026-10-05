from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.writer import governed_entity, governed_relationship
from app.knowledge_graph.domain_assertion_extraction import extract_graph_assertions
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _entity_from_payload(db: Session, payload: dict):
    kind = str(payload.get("kind") or "").strip()
    name = str(payload.get("name") or payload.get("canonical_name") or "").strip()
    key = str(payload.get("key") or payload.get("canonical_key") or "").strip()
    if not kind or not name or not key:
        raise ValueError("Graph assertion entities require kind, name, and key")

    return governed_entity(
        db,
        kind=kind,
        canonical_name=name,
        canonical_key=key,
        aliases=_as_list(payload.get("aliases")),
        description=payload.get("description"),
        attributes={
            **(payload.get("attributes") or {}),
            "cross_domain_projection": True,
        },
    )


def _assertions(observation: Observation) -> list[dict]:
    payload = observation.payload or {}
    explicit = payload.get("graph_assertions")
    if explicit is not None:
        if not isinstance(explicit, list):
            raise ValueError("Observation graph_assertions must be a list")
        return [item for item in explicit if isinstance(item, dict)]
    return extract_graph_assertions(observation)


def project_cross_domain_observation_graph(db: Session, investigation_id: str) -> dict:
    """Materialize explicit cross-domain graph assertions from canonical observations.

    Assertions are machine-readable facts carried by the observation payload.
    This projector does not infer missing entities or relations from free text.
    It creates a derived graph representation only; observations remain the
    canonical evidence records.
    """
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    links = list(
        db.scalars(
            select(EvidenceLink)
            .where(
                EvidenceLink.investigation_id == investigation_id,
                EvidenceLink.observation_id.is_not(None),
            )
            .order_by(EvidenceLink.created_at.asc())
        )
    )
    observation_ids = [link.observation_id for link in links if link.observation_id]
    observations = (
        list(
            db.scalars(
                select(Observation)
                .where(Observation.id.in_(observation_ids))
                .order_by(Observation.observed_at.asc(), Observation.id.asc())
            )
        )
        if observation_ids
        else []
    )

    node_ids: set[str] = set()
    relationship_ids: set[str] = set()
    assertion_count = 0
    skipped_observation_count = 0

    for observation in observations:
        assertions = _assertions(observation)
        if not assertions:
            skipped_observation_count += 1
            continue

        for assertion in assertions:
            subject_payload = assertion.get("subject") or {}
            object_payload = assertion.get("object") or {}
            predicate = str(assertion.get("predicate") or "").strip()
            if not predicate:
                raise ValueError("Graph assertion requires predicate")

            subject = _entity_from_payload(db, subject_payload)
            obj = _entity_from_payload(db, object_payload)
            node_ids.update([subject.id, obj.id])

            confidence = float(assertion.get("confidence", 1.0))
            provenance = {
                "method": str(assertion.get("method") or "explicit-observation-graph-assertion-v1"),
                "investigation_id": investigation_id,
                "investigation_ids": [investigation_id],
                "observation_id": observation.id,
                "observation_ids": [observation.id],
                "source": observation.source,
                "source_ref": observation.source_ref,
                "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
                "canonical_evidence_kind": "observation",
                "cross_domain_projection": True,
                **(assertion.get("provenance") or {}),
            }
            relationship = governed_relationship(
                db,
                source=subject,
                target=obj,
                kind=predicate,
                confidence=confidence,
                evidence_ids=[observation.id],
                first_seen=observation.observed_at,
                last_seen=observation.observed_at,
                provenance=provenance,
            )
            relationship_ids.add(relationship.id)
            assertion_count += 1

    db.commit()
    return {
        "investigation_id": investigation_id,
        "observation_count": len(observations),
        "assertion_count": assertion_count,
        "node_count": len(node_ids),
        "relationship_count": len(relationship_ids),
        "skipped_observation_count": skipped_observation_count,
        "policy": {
            "observations_remain_canonical_evidence": True,
            "graph_is_derived_projection": True,
            "free_text_inference_disabled": True,
            "domain_aware_extraction_enabled": True,
            "explicit_graph_assertions_take_precedence": True,
            "ontology_validation_required": True,
            "relationships_require_provenance": True,
            "projection": "cross-domain-observation-graph-projection-v1",
        },
    }
