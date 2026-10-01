from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.knowledge_graph.writer import governed_entity, governed_relationship


def _db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_governed_entity_requires_registered_type_and_marks_ontology():
    db = _db()
    try:
        company = governed_entity(
            db,
            kind="company",
            canonical_name="Example Co",
            canonical_key="example-co",
            aliases=["Example"],
            attributes={"source": "test"},
        )
        assert company.kind == "company"
        assert company.attributes["ontology"]["governed"] is True
        assert company.attributes["ontology"]["domain"] == "business"

        try:
            governed_entity(
                db,
                kind="made_up_kind",
                canonical_name="Nope",
                canonical_key="nope",
            )
        except ValueError as exc:
            assert "Unregistered ontology entity type" in str(exc)
        else:
            raise AssertionError("unregistered entity type should be rejected")
    finally:
        db.close()


def test_governed_relationship_validates_type_endpoints_and_provenance():
    db = _db()
    try:
        company = governed_entity(db, kind="company", canonical_name="Example Co", canonical_key="example-co")
        product = governed_entity(db, kind="product", canonical_name="Product A", canonical_key="product-a")
        market = governed_entity(db, kind="market", canonical_name="Healthcare", canonical_key="healthcare")

        relationship = governed_relationship(
            db,
            source=company,
            target=product,
            kind="COMPANY_LAUNCHED_PRODUCT",
            confidence=0.9,
            evidence_ids=["evidence-1"],
            provenance={"source": "press-release"},
        )
        assert relationship.kind == "COMPANY_LAUNCHED_PRODUCT"
        assert relationship.provenance["ontology"]["domain"] == "business"
        assert relationship.provenance["ontology"]["governed"] is True

        try:
            governed_relationship(
                db,
                source=market,
                target=product,
                kind="COMPANY_LAUNCHED_PRODUCT",
                provenance={"source": "test"},
            )
        except ValueError as exc:
            assert "Ontology endpoint mismatch" in str(exc)
        else:
            raise AssertionError("invalid relationship endpoints should be rejected")

        try:
            governed_relationship(
                db,
                source=company,
                target=product,
                kind="COMPANY_LAUNCHED_PRODUCT",
                provenance={},
            )
        except ValueError as exc:
            assert "require provenance" in str(exc)
        else:
            raise AssertionError("provenance-less governed relationship should be rejected")
    finally:
        db.close()


def test_governed_relationship_is_idempotent_and_accumulates_evidence():
    db = _db()
    try:
        company = governed_entity(db, kind="company", canonical_name="Example Co", canonical_key="example-co")
        technology = governed_entity(db, kind="technology", canonical_name="AI Agents", canonical_key="ai-agents")

        first = governed_relationship(
            db,
            source=company,
            target=technology,
            kind="COMPANY_DEVELOPS_TECHNOLOGY",
            confidence=0.8,
            evidence_ids=["e1"],
            provenance={"source": "company-site"},
        )
        again = governed_relationship(
            db,
            source=company,
            target=technology,
            kind="COMPANY_DEVELOPS_TECHNOLOGY",
            confidence=0.9,
            evidence_ids=["e2"],
            provenance={"source": "patent"},
        )
        assert first.id == again.id
        assert set(again.evidence_ids) == {"e1", "e2"}
        assert again.confidence == 0.9
        assert again.provenance["evidence_count"] == 2
    finally:
        db.close()
