from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificPassage, ScientificPublication
from app.scientific_literature.graph_projection import project_investigation_literature_graph


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _add_publication(db: Session, investigation: Investigation, *, pmid: str, trial_id: str, text: str):
    publication = ScientificPublication(
        source_system="pubmed",
        source_id=pmid,
        pmid=pmid,
        doi=f"10.1000/{pmid}",
        title=f"Publication {pmid}",
        journal="Test Journal",
        publication_date=date(2023, 1, 1),
        authors_json=[],
        metadata_json={"clinical_trial_ids": [trial_id]},
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        retrieval_ref=f"pubmed:pmid:{pmid}",
        content_hash=f"pub-{pmid}",
    )
    db.add(publication)
    db.flush()
    passage = ScientificPassage(
        publication_id=publication.id,
        section="Abstract",
        locator="abstract:1",
        text=text,
        content_hash=f"passage-{pmid}",
        provenance_json={"canonical_source": True, "pmid": pmid},
    )
    db.add(passage)
    db.flush()
    db.add(EvidenceLink(
        investigation_id=investigation.id,
        scientific_passage_id=passage.id,
        stance="supporting",
        weight=1.0,
    ))
    return publication, passage


def test_literature_projection_creates_publication_trial_passage_and_context_nodes():
    db = _db()
    try:
        investigation = Investigation(
            title="Osimertinib resistance",
            slug="kg-literature-projection",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()
        publication, passage = _add_publication(
            db,
            investigation,
            pmid="36849494",
            trial_id="NCT02296125",
            text=(
                "First-line osimertinib in EGFRm NSCLC. "
                "Paired plasma samples were analyzed using next-generation sequencing."
            ),
        )
        db.commit()

        result = project_investigation_literature_graph(db, investigation.id)

        assert result["publication_count"] == 1
        assert result["publication_nodes"] == 1
        assert result["trial_nodes"] == 1
        assert result["passage_nodes"] == 1
        assert result["policy"]["graph_is_derived_projection"] is True
        assert result["policy"]["canonical_literature_remains_in_scientific_tables"] is True
        assert result["policy"]["passage_text_not_duplicated_into_graph"] is True

        kinds = {item.kind for item in db.scalars(select(Entity))}
        assert {"publication", "source", "clinical_trial", "population", "drug", "assay"} <= kinds

        relations = {item.kind for item in db.scalars(select(Relationship))}
        assert "PUBLICATION_CONTAINS_PASSAGE" in relations
        assert "PUBLICATION_REPORTS_STUDY" in relations
        assert "STUDY_HAS_POPULATION" in relations
        assert "STUDY_USES_INTERVENTION" in relations
        assert "STUDY_USES_ASSAY" in relations

        projected_edges = list(db.scalars(select(Relationship)))
        assert all(investigation.id in edge.provenance.get("investigation_ids", []) for edge in projected_edges)
        assert all(edge.provenance.get("ontology", {}).get("governed") is True for edge in projected_edges)

        publication_node = db.scalar(select(Entity).where(Entity.kind == "publication"))
        assert publication_node is not None
        assert publication_node.attributes["pmid"] == publication.pmid

        passage_node = db.scalar(select(Entity).where(Entity.canonical_key == f"scientific-passage:{passage.id}"))
        assert passage_node is not None
        assert "text" not in passage_node.attributes
    finally:
        db.close()


def test_literature_projection_is_idempotent():
    db = _db()
    try:
        investigation = Investigation(
            title="Osimertinib resistance",
            slug="kg-literature-idempotent",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()
        _add_publication(
            db,
            investigation,
            pmid="36849516",
            trial_id="NCT02151981",
            text=(
                "Second-line osimertinib in EGFR T790M EGFR-mutated NSCLC. "
                "Plasma samples were analyzed using next-generation sequencing."
            ),
        )
        db.commit()

        first = project_investigation_literature_graph(db, investigation.id)
        entity_count = len(list(db.scalars(select(Entity))))
        relationship_count = len(list(db.scalars(select(Relationship))))
        second = project_investigation_literature_graph(db, investigation.id)

        assert first["node_count"] == second["node_count"]
        assert first["relationship_count"] == second["relationship_count"]
        assert len(list(db.scalars(select(Entity)))) == entity_count
        assert len(list(db.scalars(select(Relationship)))) == relationship_count
    finally:
        db.close()


def test_projection_only_uses_literature_attached_to_requested_investigation():
    db = _db()
    try:
        first = Investigation(title="First", slug="first-investigation", status="collecting", confidence=0.0, attributes={})
        second = Investigation(title="Second", slug="second-investigation", status="collecting", confidence=0.0, attributes={})
        db.add_all([first, second])
        db.flush()
        _add_publication(
            db,
            first,
            pmid="11111111",
            trial_id="NCT11111111",
            text="First-line osimertinib in EGFRm NSCLC using plasma next-generation sequencing.",
        )
        _add_publication(
            db,
            second,
            pmid="22222222",
            trial_id="NCT22222222",
            text="Second-line osimertinib in EGFR T790M NSCLC using plasma next-generation sequencing.",
        )
        db.commit()

        result = project_investigation_literature_graph(db, first.id)
        assert result["publication_count"] == 1

        publication_nodes = list(db.scalars(select(Entity).where(Entity.kind == "publication")))
        assert len(publication_nodes) == 1
        assert publication_nodes[0].attributes["pmid"] == "11111111"
    finally:
        db.close()
