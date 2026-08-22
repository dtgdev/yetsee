from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.investigation_runtime.evidence_accounting import investigation_evidence_accounting
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificClaim, ScientificPassage, ScientificPublication
from app.scientific_literature.candidate_extraction import extract_investigation_claim_candidates
from app.scientific_literature.grounding import ground_claim_relationship


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _source(db: Session, *, pmid: str, doi: str, passage_hash: str, publication_hash: str, text: str | None = None) -> ScientificPassage:
    publication = ScientificPublication(
        source_system="pubmed",
        source_id=pmid,
        pmid=pmid,
        doi=doi,
        title=f"Publication {pmid}",
        journal="Test Journal",
        publication_date=date(2023, 1, 1),
        authors_json=[],
        metadata_json={},
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        retrieval_ref=f"pubmed:pmid:{pmid}",
        content_hash=publication_hash,
    )
    db.add(publication)
    db.flush()
    passage = ScientificPassage(
        publication_id=publication.id,
        section="Abstract",
        locator="abstract:1",
        text=text or f"Evidence from {pmid}",
        content_hash=passage_hash,
        provenance_json={"source_system": "pubmed", "pmid": pmid, "canonical_source": True},
    )
    db.add(passage)
    db.commit()
    db.refresh(passage)
    return passage


def _investigation(db: Session, slug: str = "osimertinib-resistance") -> Investigation:
    investigation = Investigation(title="Osimertinib resistance", slug=slug, attributes={})
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


def _attach(db: Session, investigation: Investigation, passage: ScientificPassage, stance: str = "supporting") -> EvidenceLink:
    link = EvidenceLink(
        investigation_id=investigation.id,
        scientific_passage_id=passage.id,
        stance=stance,
        weight=1.0,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def _ground(db: Session, passage_id: str, claim_text: str, investigation_id: str | None = None):
    return ground_claim_relationship(
        db,
        investigation_id=investigation_id,
        passage_id=passage_id,
        claim_text=claim_text,
        subject_kind="genomic_alteration",
        subject_name="MET amplification",
        subject_key="genomic-alteration:met-amplification",
        predicate="contributes_to",
        object_kind="drug_resistance",
        object_name="Acquired osimertinib resistance",
        object_key="drug-resistance:osimertinib-acquired",
    )


def test_grounding_is_idempotent_and_claim_is_not_canonical_evidence():
    db = _db()
    try:
        passage = _source(db, pmid="36849494", doi="10.1000/flaura", passage_hash="a" * 64, publication_hash="b" * 64)
        claim, relationship, created = _ground(db, passage.id, "MET amplification contributes to acquired osimertinib resistance.")
        again_claim, again_relationship, again_created = _ground(db, passage.id, "MET amplification contributes to acquired osimertinib resistance.")

        assert created is True
        assert again_created is False
        assert claim.id == again_claim.id
        assert relationship.id == again_relationship.id
        assert claim.canonical_evidence is False
        assert relationship.evidence_ids == [passage.id]
        assert relationship.provenance["pmids"] == ["36849494"]
        assert relationship.provenance["canonical_evidence_kind"] == "scientific_passage"
    finally:
        db.close()


def test_same_relationship_aggregates_independent_publications():
    db = _db()
    try:
        first = _source(db, pmid="36849494", doi="10.1000/flaura", passage_hash="c" * 64, publication_hash="d" * 64)
        second = _source(db, pmid="36849516", doi="10.1000/aura3", passage_hash="e" * 64, publication_hash="f" * 64)

        first_claim, relationship, first_created = _ground(db, first.id, "FLAURA reports MET amplification among acquired resistance mechanisms.")
        second_claim, same_relationship, second_created = _ground(db, second.id, "AURA3 reports MET amplification among acquired resistance mechanisms.")

        assert first_created is True
        assert second_created is False
        assert relationship.id == same_relationship.id
        assert first_claim.id != second_claim.id
        assert set(same_relationship.evidence_ids) == {first.id, second.id}
        assert set(same_relationship.provenance["pmids"]) == {"36849494", "36849516"}
        assert set(same_relationship.provenance["dois"]) == {"10.1000/flaura", "10.1000/aura3"}
        assert set(same_relationship.provenance["claim_ids"]) == {first_claim.id, second_claim.id}
    finally:
        db.close()


def test_investigation_scoped_grounding_requires_attached_passage():
    db = _db()
    try:
        investigation = _investigation(db)
        passage = _source(db, pmid="36849494", doi="10.1000/flaura", passage_hash="1" * 64, publication_hash="2" * 64)

        with pytest.raises(ValueError, match="must be attached to the investigation"):
            _ground(
                db,
                passage.id,
                "MET amplification contributes to acquired osimertinib resistance.",
                investigation.id,
            )
    finally:
        db.close()


def test_investigation_scoped_grounding_records_investigation_provenance():
    db = _db()
    try:
        investigation = _investigation(db)
        passage = _source(db, pmid="36849494", doi="10.1000/flaura", passage_hash="3" * 64, publication_hash="4" * 64)
        _attach(db, investigation, passage)

        claim, relationship, created = _ground(
            db,
            passage.id,
            "MET amplification contributes to acquired osimertinib resistance.",
            investigation.id,
        )

        assert created is True
        assert claim.extraction_json["investigation_id"] == investigation.id
        assert relationship.provenance["investigation_ids"] == [investigation.id]
        assert relationship.provenance["passage_ids"] == [passage.id]
        assert relationship.provenance["pmids"] == ["36849494"]
    finally:
        db.close()


def test_canonical_evidence_accounting_counts_literature_and_publications():
    db = _db()
    try:
        investigation = _investigation(db, "evidence-accounting")
        first = _source(db, pmid="36849494", doi="10.1000/flaura", passage_hash="5" * 64, publication_hash="6" * 64)
        second = _source(db, pmid="36849516", doi="10.1000/aura3", passage_hash="7" * 64, publication_hash="8" * 64)
        _attach(db, investigation, first, "supporting")
        _attach(db, investigation, second, "supporting")

        result = investigation_evidence_accounting(db, investigation.id)

        assert result["canonical_evidence_count"] == 2
        assert result["literature_evidence_count"] == 2
        assert result["independent_source_count"] == 2
        assert result["independent_publication_count"] == 2
        assert result["supporting_count"] == 2
        assert result["contradicting_count"] == 0
        assert {item["publication"]["pmid"] for item in result["literature_items"]} == {"36849494", "36849516"}
        assert result["policy"]["derived_claims_are_evidence"] is False
    finally:
        db.close()


def test_claim_candidates_preserve_independent_publication_provenance_and_are_noncanonical():
    db = _db()
    try:
        investigation = _investigation(db, "claim-candidates")
        first = _source(
            db,
            pmid="36849494",
            doi="10.1038/s41467-023-35961-y",
            passage_hash="9" * 64,
            publication_hash="a" * 64,
            text=(
                "This analysis identifies acquired resistance mechanisms to first-line osimertinib. "
                "The most frequent resistance mechanisms are MET amplification and EGFR C797S mutation."
            ),
        )
        second = _source(
            db,
            pmid="36849516",
            doi="10.1038/s41467-023-35962-x",
            passage_hash="b" * 64,
            publication_hash="c" * 64,
            text=(
                "This analysis evaluates acquired resistance mechanisms to second-line osimertinib. "
                "Resistance mechanisms include MET amplification and EGFR C797X mutation."
            ),
        )
        _attach(db, investigation, first)
        _attach(db, investigation, second)

        candidates = extract_investigation_claim_candidates(db, investigation.id)

        met = [item for item in candidates if item["claim"]["subject"]["name"] == "MET amplification"]
        assert len(met) == 2
        assert {item["provenance"]["pmid"] for item in met} == {"36849494", "36849516"}
        assert all(item["claim"]["predicate"] == "reported_as_resistance_mechanism" for item in met)
        assert all(item["extraction"]["requires_review"] is True for item in met)
        assert all(item["extraction"]["canonical_evidence"] is False for item in met)
        assert all("MET amplification" in item["claim"]["assertion_text"] for item in met)
        assert all(item["provenance"]["passage_id"] in {first.id, second.id} for item in met)
    finally:
        db.close()


def test_claim_candidate_extraction_is_deterministic_and_has_no_write_side_effects():
    db = _db()
    try:
        investigation = _investigation(db, "claim-candidate-idempotency")
        passage = _source(
            db,
            pmid="36849494",
            doi="10.1038/s41467-023-35961-y",
            passage_hash="d" * 64,
            publication_hash="e" * 64,
            text="The most frequent resistance mechanisms are MET amplification and EGFR C797S mutation in osimertinib-treated disease.",
        )
        _attach(db, investigation, passage)

        first = extract_investigation_claim_candidates(db, investigation.id)
        second = extract_investigation_claim_candidates(db, investigation.id)

        assert first == second
        assert [item["candidate_id"] for item in first] == [item["candidate_id"] for item in second]
        assert db.scalar(select(ScientificClaim).limit(1)) is None
        assert db.scalar(select(Relationship).limit(1)) is None
        accounting = investigation_evidence_accounting(db, investigation.id)
        assert accounting["canonical_evidence_count"] == 1
        assert accounting["literature_evidence_count"] == 1
    finally:
        db.close()
