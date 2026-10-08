from __future__ import annotations

from hashlib import sha256
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.writer import governed_entity, governed_relationship
from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.scientific_literature import ScientificPassage, ScientificPublication
from app.scientific_literature.contradiction_intelligence import investigation_contradiction_intelligence
from app.scientific_literature.evidence_gap_intelligence import investigation_evidence_gap_intelligence
from app.scientific_literature.study_quality import investigation_study_quality


PROJECTION_VERSION = "evidence-state-graph-projection-v1"


def _safe_key(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:20]


def _publication_entity(db: Session, publication_id: str) -> Entity | None:
    publication = db.get(ScientificPublication, publication_id)
    if publication is None:
        return None
    return db.scalar(
        select(Entity).where(
            Entity.canonical_key == f"publication:pubmed:{publication.pmid or publication.id}"
        )
    )


def _passage_ids_for_publication(db: Session, investigation_id: str, publication_id: str) -> list[str]:
    return list(
        db.scalars(
            select(ScientificPassage.id)
            .join(EvidenceLink, EvidenceLink.scientific_passage_id == ScientificPassage.id)
            .where(
                EvidenceLink.investigation_id == investigation_id,
                ScientificPassage.publication_id == publication_id,
            )
            .order_by(ScientificPassage.id.asc())
        )
    )


def _assessment_node(
    db: Session,
    *,
    investigation_id: str,
    assessment_type: str,
    identity: str,
    label: str,
    attributes: dict,
):
    assessment = governed_entity(
        db,
        kind="assessment",
        canonical_name=label,
        canonical_key=f"assessment:{assessment_type}:{_safe_key(investigation_id + ':' + identity)}",
        attributes={
            **attributes,
            "assessment_type": assessment_type,
            "investigation_id": investigation_id,
            "canonical_evidence": False,
            "derived": True,
            "evidence_state_projection": True,
            "projection_version": PROJECTION_VERSION,
        },
    )
    assessment.canonical_name = label
    return assessment


def _link_assessment(
    db: Session,
    *,
    assessment: Entity,
    target: Entity,
    investigation_id: str,
    evidence_ids: list[str],
    confidence: float,
    provenance: dict,
):
    relationship = governed_relationship(
        db,
        source=assessment,
        target=target,
        kind="ASSESSMENT_CONCERNS",
        confidence=confidence,
        evidence_ids=evidence_ids,
        provenance={
            "method": PROJECTION_VERSION,
            "investigation_id": investigation_id,
            "investigation_ids": [investigation_id],
            "canonical_evidence": False,
            "derived_assessment": True,
            **provenance,
        },
    )
    # Derived assessments reflect the current calculation, including a lower
    # confidence after new evidence; the canonical writer retains its own rules.
    relationship.confidence = confidence
    return relationship


def _project_structured_observation_states(
    db: Session,
    investigation_id: str,
    observations: list[Observation],
) -> tuple[int, set[str]]:
    nodes = 0
    relations: set[str] = set()
    for observation in observations:
        payload = observation.payload or {}
        states = payload.get("evidence_states")
        if states is None:
            single = payload.get("evidence_state")
            states = [single] if isinstance(single, dict) else []
        if not isinstance(states, list):
            continue

        for index, state in enumerate(item for item in states if isinstance(item, dict)):
            assessment_type = str(state.get("type") or state.get("assessment_type") or "").strip()
            target_payload = state.get("target") or {}
            if not assessment_type or not isinstance(target_payload, dict):
                continue
            target_key = str(target_payload.get("key") or target_payload.get("canonical_key") or "").strip()
            if not target_key:
                continue
            target = db.scalar(select(Entity).where(Entity.canonical_key == target_key))
            if target is None:
                continue

            status = str(state.get("status") or "unknown")
            confidence = max(0.0, min(1.0, float(state.get("confidence", 1.0))))
            assessment = _assessment_node(
                db,
                investigation_id=investigation_id,
                assessment_type=assessment_type,
                identity=f"observation:{observation.id}:{index}:{target_key}",
                label=str(state.get("label") or f"{assessment_type.replace('_', ' ').title()}: {status}"),
                attributes={
                    "status": status,
                    "confidence": confidence,
                    "rationale": state.get("rationale"),
                    "source_observation_id": observation.id,
                    "domain": state.get("domain"),
                },
            )
            nodes += 1
            relation = _link_assessment(
                db,
                assessment=assessment,
                target=target,
                investigation_id=investigation_id,
                evidence_ids=[observation.id],
                confidence=confidence,
                provenance={
                    "canonical_evidence_kind": "observation",
                    "observation_id": observation.id,
                    "observation_ids": [observation.id],
                    "source": observation.source,
                    "source_ref": observation.source_ref,
                },
            )
            relations.add(relation.id)
    return nodes, relations


def project_evidence_state_graph(db: Session, investigation_id: str, *, commit: bool = True) -> dict:
    """Project derived quality, contradiction, gap, and cross-domain evidence states.

    The projection creates graph context only. It never changes canonical evidence,
    evidence counts, hypothesis confidence, or the source assessment outputs.
    """
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    node_ids: set[str] = set()
    relationship_ids: set[str] = set()

    quality = investigation_study_quality(db, investigation_id)
    for study in quality.get("studies", []):
        target = _publication_entity(db, study["publication_id"])
        if target is None:
            continue
        evidence_ids = _passage_ids_for_publication(db, investigation_id, study["publication_id"])
        assessment = _assessment_node(
            db,
            investigation_id=investigation_id,
            assessment_type="study_quality",
            identity=study["publication_id"],
            label=f"Study quality: {study['quality_rating'].replace('_', ' ')}",
            attributes={
                "status": study["quality_rating"],
                "score": study["quality_score"],
                "assessment_confidence": study["assessment_confidence"],
                "formal_risk_of_bias": False,
                "algorithm": study.get("policy", {}).get("algorithm"),
                "publication_id": study["publication_id"],
            },
        )
        node_ids.add(assessment.id)
        relation = _link_assessment(
            db,
            assessment=assessment,
            target=target,
            investigation_id=investigation_id,
            evidence_ids=evidence_ids,
            confidence=float(study["assessment_confidence"]),
            provenance={
                "canonical_evidence_kind": "scientific_passage",
                "publication_id": study["publication_id"],
                "assessment_layer": "quality",
            },
        )
        relationship_ids.add(relation.id)

    contradiction = investigation_contradiction_intelligence(db, investigation_id)
    for group in contradiction.get("groups", []):
        relation = group.get("relationship") or {}
        subject_key = (relation.get("subject") or {}).get("key")
        object_key = (relation.get("object") or {}).get("key")
        targets = [
            db.scalar(select(Entity).where(Entity.canonical_key == key))
            for key in [subject_key, object_key]
            if key
        ]
        targets = [target for target in targets if target is not None]
        if not targets:
            continue
        evidence_ids = sorted({
            source.get("passage_id")
            for source in group.get("sources", [])
            if source.get("passage_id")
        })
        if not evidence_ids:
            publication_ids = {
                source.get("publication_id") for source in group.get("sources", []) if source.get("publication_id")
            }
            evidence_ids = sorted({
                passage_id
                for publication_id in publication_ids
                for passage_id in _passage_ids_for_publication(db, investigation_id, publication_id)
            })
        identity = f"{subject_key}:{relation.get('predicate')}:{object_key}"
        assessment = _assessment_node(
            db,
            investigation_id=investigation_id,
            assessment_type="contradiction_state",
            identity=identity,
            label=f"Evidence consistency: {group['overall_status'].replace('_', ' ')}",
            attributes={
                "status": group["overall_status"],
                "source_count": group.get("source_count", 0),
                "publication_count": group.get("publication_count", 0),
                "contextual_divergence_pair_count": group.get("contextual_divergence_pair_count", 0),
                "reviewed_contradiction_pair_count": group.get("reviewed_contradiction_pair_count", 0),
                "provisional_tension_pair_count": group.get("provisional_tension_pair_count", 0),
                "algorithm": contradiction.get("policy", {}).get("algorithm"),
            },
        )
        node_ids.add(assessment.id)
        for target in targets:
            edge = _link_assessment(
                db,
                assessment=assessment,
                target=target,
                investigation_id=investigation_id,
                evidence_ids=evidence_ids,
                confidence=0.95,
                provenance={
                    "canonical_evidence_kind": "scientific_passage",
                    "assessment_layer": "contradiction",
                    "review_aware": True,
                    "contextual_divergence_is_not_direct_contradiction": True,
                },
            )
            relationship_ids.add(edge.id)

    gaps = investigation_evidence_gap_intelligence(db, investigation_id)
    publication_targets = [
        target for study in quality.get("studies", [])
        if (target := _publication_entity(db, study["publication_id"])) is not None
    ]
    for index, gap in enumerate(gaps.get("gaps", [])):
        gap_entity = governed_entity(
            db,
            kind="evidence_gap",
            canonical_name=gap["title"],
            canonical_key=f"evidence-gap:{_safe_key(investigation_id + ':' + gap['gap_type'] + ':' + str(index))}",
            attributes={
                "gap_type": gap["gap_type"],
                "priority": gap["priority"],
                "rationale": gap["rationale"],
                "suggested_next_evidence": gap.get("suggested_next_evidence", []),
                "investigation_id": investigation_id,
                "canonical_evidence": False,
                "derived": True,
                "absence_of_evidence_is_not_evidence_of_absence": True,
                "projection_version": PROJECTION_VERSION,
            },
        )
        node_ids.add(gap_entity.id)
        gap_entity.canonical_name = gap["title"]
        for target in publication_targets:
            evidence_ids = _passage_ids_for_publication(db, investigation_id, target.attributes.get("publication_id"))
            edge = governed_relationship(
                db,
                source=gap_entity,
                target=target,
                kind="EVIDENCE_GAP_CONCERNS",
                confidence=1.0,
                evidence_ids=evidence_ids,
                provenance={
                    "method": PROJECTION_VERSION,
                    "investigation_id": investigation_id,
                    "investigation_ids": [investigation_id],
                    "canonical_evidence_kind": "scientific_passage",
                    "derived_gap_assessment": True,
                    "does_not_change_evidence_count": True,
                    "absence_of_evidence_is_not_evidence_of_absence": True,
                },
            )
            relationship_ids.add(edge.id)

    observation_ids = list(
        db.scalars(
            select(EvidenceLink.observation_id)
            .where(
                EvidenceLink.investigation_id == investigation_id,
                EvidenceLink.observation_id.is_not(None),
            )
        )
    )
    observations = (
        list(db.scalars(select(Observation).where(Observation.id.in_(observation_ids))))
        if observation_ids else []
    )
    structured_nodes, structured_relations = _project_structured_observation_states(
        db, investigation_id, observations
    )

    relationship_ids.update(structured_relations)

    if commit:
        db.commit()
    else:
        db.flush()
    return {
        "investigation_id": investigation_id,
        "assessment_node_count": len(node_ids) + structured_nodes,
        "relationship_count": len(relationship_ids),
        "relationship_ids": sorted(relationship_ids),
        "node_ids": sorted(node_ids),
        "study_quality_assessment_count": len(quality.get("studies", [])),
        "contradiction_assessment_count": len(contradiction.get("groups", [])),
        "evidence_gap_count": len(gaps.get("gaps", [])),
        "structured_cross_domain_state_count": structured_nodes,
        "policy": {
            "graph_context_is_derived": True,
            "canonical_evidence_unchanged": True,
            "does_not_change_evidence_count": True,
            "does_not_change_hypothesis_confidence": True,
            "quality_is_not_formal_risk_of_bias": True,
            "contextual_divergence_is_not_direct_contradiction": True,
            "absence_of_evidence_is_not_evidence_of_absence": True,
            "cross_domain_states_require_structured_input": True,
            "projection": PROJECTION_VERSION,
        },
    }

