from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.knowledge_graph.cross_domain_projection import project_cross_domain_observation_graph
from app.knowledge_graph.evidence_state_projection import project_evidence_state_graph
from app.knowledge_graph.ontology import ONTOLOGY_VERSION
from app.knowledge_graph.temporal_events import project_temporal_events
from app.models.evidence import EvidenceLink
from app.models.graph import InvestigationGraphProjection
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.relationship import Relationship
from app.models.scientific_literature import (
    ScientificClaimCandidateReview, ScientificPassage, ScientificPublication,
)
from app.scientific_literature.graph_projection import project_investigation_literature_graph


PROJECTION_VERSION = "investigation-auto-projection-v1"


def _record_value(value):
    if isinstance(value, datetime):
        utc = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return utc.isoformat()
    return value


def _records(rows) -> list[dict]:
    return sorted([
        {
            column.key: _record_value(getattr(row, column.key))
            for column in inspect(type(row)).column_attrs
            if column.key not in {"created_at", "updated_at"}
        }
        for row in rows
    ], key=lambda row: row.get("id", ""))


def projection_input_fingerprint(db: Session, investigation_id: str) -> str:
    """Hash source inputs, never the graph outputs produced from them."""
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError("Investigation not found")
    links = list(db.scalars(select(EvidenceLink).where(
        EvidenceLink.investigation_id == investigation_id
    )))
    hypothesis_links = list(db.scalars(
        select(HypothesisEvidenceLink)
        .join(Hypothesis, Hypothesis.id == HypothesisEvidenceLink.hypothesis_id)
        .where(Hypothesis.investigation_id == investigation_id)
    ))
    observation_ids = {link.observation_id for link in [*links, *hypothesis_links]
                       if link.observation_id}
    passage_ids = {link.scientific_passage_id for link in links if link.scientific_passage_id}
    observations = list(db.scalars(select(Observation).where(Observation.id.in_(observation_ids))))
    passages = list(db.scalars(select(ScientificPassage).where(ScientificPassage.id.in_(passage_ids))))
    publications = list(db.scalars(select(ScientificPublication).where(
        ScientificPublication.id.in_({passage.publication_id for passage in passages})
    )))
    reviews = list(db.scalars(select(ScientificClaimCandidateReview).where(
        ScientificClaimCandidateReview.investigation_id == investigation_id
    )))
    payload = {
        "version": PROJECTION_VERSION,
        "ontology_version": ONTOLOGY_VERSION,
        "research_question": str(
            (investigation.attributes or {}).get("research_question")
            or investigation.summary or investigation.title
        ),
        "links": _records(links),
        "hypothesis_links": _records(hypothesis_links),
        "observations": _records(observations),
        "passages": _records(passages),
        "publications": _records(publications),
        "reviews": _records(reviews),
    }
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def ensure_investigation_projection(
    db: Session, investigation_id: str, *, force: bool = False,
) -> dict:
    """Prepare all derived layers atomically; unchanged inputs are a no-op.

    The investigation row serializes concurrent preparation on PostgreSQL. A
    failed layer rolls back the entire projection and its freshness record.
    Canonical evidence, hypothesis confidence and investigation state are not
    edited. This is a write command, separate from the read-only graph APIs.
    """
    investigation = db.scalar(select(Investigation).where(
        Investigation.id == investigation_id
    ).with_for_update())
    if investigation is None:
        raise KeyError("Investigation not found")

    fingerprint = projection_input_fingerprint(db, investigation_id)
    state = db.get(InvestigationGraphProjection, investigation_id, populate_existing=True)
    if not force and state is not None and state.input_fingerprint == fingerprint:
        db.commit()  # release the preparation lock
        return {**state.summary_json, "status": "current", "rebuilt": False}

    try:
        layers = {
            "literature": project_investigation_literature_graph(db, investigation_id, commit=False),
            "cross_domain": project_cross_domain_observation_graph(db, investigation_id, commit=False),
            "temporal": project_temporal_events(db, investigation_id, commit=False),
            "evidence_state": project_evidence_state_graph(db, investigation_id, commit=False),
        }
        relationship_ids = sorted({
            relation_id for layer in layers.values() for relation_id in layer["relationship_ids"]
        })
        relationships = list(db.scalars(select(Relationship).where(
            Relationship.id.in_(relationship_ids)
        )))
        node_ids = sorted({
            node_id for layer in layers.values() for node_id in layer.get("node_ids", [])
        } | {
            node_id for relation in relationships
            for node_id in [relation.source_entity_id, relation.target_entity_id]
        })
        summary = {
            "investigation_id": investigation_id,
            "projection_version": PROJECTION_VERSION,
            "input_fingerprint": fingerprint,
            "layers": layers,
            "relationship_ids": relationship_ids,
            "node_ids": node_ids,
            "policy": {
                "derived_graph_only": True,
                "canonical_evidence_unchanged": True,
                "hypothesis_confidence_unchanged": True,
                "atomic": True,
                "ontology_validation_required": True,
            },
        }
        if state is None:
            state = InvestigationGraphProjection(investigation_id=investigation_id)
            db.add(state)
        state.projection_version = PROJECTION_VERSION
        state.input_fingerprint = fingerprint
        state.summary_json = summary
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {**summary, "status": "current", "rebuilt": True}
