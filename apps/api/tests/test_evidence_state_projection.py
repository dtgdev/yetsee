from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.knowledge_graph.evidence_state_projection import project_evidence_state_graph
from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.relationship import Relationship


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_projects_structured_cross_domain_evidence_state_without_mutating_observation():
    db = _db()
    try:
        investigation = Investigation(
            title="Business evidence state",
            slug="business-evidence-state",
            status="collecting",
            confidence=0.42,
            attributes={},
        )
        company = Entity(
            kind="company",
            canonical_name="ExampleCo",
            canonical_key="company:exampleco",
            aliases=[],
            attributes={},
        )
        db.add_all([investigation, company])
        db.flush()

        payload = {
            "evidence_state": {
                "type": "source_reliability",
                "status": "moderate",
                "confidence": 0.78,
                "rationale": "Primary company filing is available but independent confirmation is limited.",
                "domain": "business",
                "target": {
                    "kind": "company",
                    "name": "ExampleCo",
                    "key": "company:exampleco",
                },
            }
        }
        observation = Observation(
            source="filing",
            source_ref="filing:exampleco",
            topic="ExampleCo",
            metric="company_update",
            value=1.0,
            observed_at=datetime.now(timezone.utc),
            payload=payload,
            content_hash="a" * 64,
        )
        db.add(observation)
        db.flush()
        db.add(EvidenceLink(
            investigation_id=investigation.id,
            observation_id=observation.id,
            stance="supporting",
            weight=1.0,
        ))
        db.commit()

        before_confidence = investigation.confidence
        result = project_evidence_state_graph(db, investigation.id)

        assert result["structured_cross_domain_state_count"] == 1
        assert result["policy"]["canonical_evidence_unchanged"] is True
        assert result["policy"]["does_not_change_evidence_count"] is True
        assert result["policy"]["does_not_change_hypothesis_confidence"] is True
        assert result["policy"]["cross_domain_states_require_structured_input"] is True

        assessment = db.scalar(
            select(Entity).where(
                Entity.kind == "assessment",
                Entity.canonical_key.like("assessment:source_reliability:%"),
            )
        )
        assert assessment is not None
        assert assessment.attributes["status"] == "moderate"
        assert assessment.attributes["canonical_evidence"] is False
        assert assessment.attributes["derived"] is True

        relation = db.scalar(
            select(Relationship).where(
                Relationship.source_entity_id == assessment.id,
                Relationship.target_entity_id == company.id,
                Relationship.kind == "ASSESSMENT_CONCERNS",
            )
        )
        assert relation is not None
        assert relation.evidence_ids == [observation.id]
        assert relation.provenance["canonical_evidence_kind"] == "observation"
        assert relation.provenance["derived_assessment"] is True

        db.refresh(observation)
        db.refresh(investigation)
        assert observation.payload == payload
        assert investigation.confidence == before_confidence
    finally:
        db.close()


def test_unstructured_observation_does_not_create_cross_domain_assessment():
    db = _db()
    try:
        investigation = Investigation(
            title="Unstructured context",
            slug="unstructured-context",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        company = Entity(
            kind="company",
            canonical_name="ExampleCo",
            canonical_key="company:exampleco",
            aliases=[],
            attributes={},
        )
        db.add_all([investigation, company])
        db.flush()
        observation = Observation(
            source="news",
            source_ref="news:exampleco",
            topic="ExampleCo",
            metric="coverage",
            value=1.0,
            observed_at=datetime.now(timezone.utc),
            payload={"text": "This source seems unreliable and contradictory."},
            content_hash="b" * 64,
        )
        db.add(observation)
        db.flush()
        db.add(EvidenceLink(
            investigation_id=investigation.id,
            observation_id=observation.id,
            stance="contextual",
            weight=1.0,
        ))
        db.commit()

        result = project_evidence_state_graph(db, investigation.id)

        assert result["structured_cross_domain_state_count"] == 0
        assert db.scalar(
            select(Entity).where(
                Entity.kind == "assessment",
                Entity.canonical_key.like("assessment:source_reliability:%"),
            )
        ) is None
    finally:
        db.close()


def test_evidence_gap_is_derived_and_does_not_become_canonical_evidence():
    db = _db()
    try:
        investigation = Investigation(
            title="Scientific gap only",
            slug="scientific-gap-only",
            status="collecting",
            confidence=0.0,
            attributes={"research_question": "What mechanism explains this effect?"},
        )
        db.add(investigation)
        db.commit()

        result = project_evidence_state_graph(db, investigation.id)

        assert result["evidence_gap_count"] >= 1
        gap = db.scalar(select(Entity).where(Entity.kind == "evidence_gap"))
        assert gap is not None
        assert gap.attributes["canonical_evidence"] is False
        assert gap.attributes["derived"] is True
        assert gap.attributes["absence_of_evidence_is_not_evidence_of_absence"] is True
    finally:
        db.close()
