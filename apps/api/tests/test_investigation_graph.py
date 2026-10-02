from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.discovery_engine.engine import promote_candidate
from app.knowledge_graph.investigation import investigation_graph
from app.models.discovery import DiscoveryCandidate
from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificPassage, ScientificPublication
from app.scientific_literature.graph_projection import project_investigation_literature_graph
from app.signal_engine.ingestion import run_connector
from app.workflow_engine.engine import run_workflow


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_investigation_graph_is_scoped_derived_and_evidence_backed():
    db = make_session()
    run_connector(db, "demo")
    run_workflow(db, "intelligence-refresh", hours=720)
    candidate = db.scalar(select(DiscoveryCandidate).where(DiscoveryCandidate.canonical_key == "running clubs"))
    assert candidate is not None
    investigation = promote_candidate(db, candidate.id, allow_override=True, override_reason="galileo")

    graph = investigation_graph(db, investigation.id)

    assert graph["derived"] is True
    assert graph["investigation"]["id"] == investigation.id
    assert graph["metrics"]["nodes"] >= 1
    assert graph["metrics"]["observations"] >= 1
    assert graph["metrics"]["independent_sources"] >= 1
    assert any(node["kind"] == "investigation" for node in graph["nodes"])
    assert any(node["kind"] == "observation" for node in graph["nodes"])
    assert any(edge["kind"] == "HAS_EVIDENCE" for edge in graph["edges"])
    assert all("degree_centrality" in node for node in graph["nodes"])


def test_investigation_graph_exposes_galileo_analytics():
    db = make_session()

    run_connector(db, "demo")
    run_workflow(db, "intelligence-refresh", hours=720)

    candidate = db.scalar(
        select(DiscoveryCandidate).where(
            DiscoveryCandidate.canonical_key == "running clubs"
        )
    )

    assert candidate is not None

    investigation = promote_candidate(
        db,
        candidate.id,
        allow_override=True,
        override_reason="galileo analytics",
    )

    graph = investigation_graph(
        db,
        investigation.id,
    )

    analytics = graph["analytics"]

    assert "degree_centrality" in analytics
    assert "betweenness_centrality" in analytics
    assert "closeness_centrality" in analytics
    assert "pagerank" in analytics
    assert "communities" in analytics
    assert "bridge_nodes" in analytics
    assert "top_semantic_nodes" in analytics
    assert "density" in analytics

    assert set(analytics["degree_centrality"]) == {
        node["id"]
        for node in graph["nodes"]
    }


def test_investigation_graph_includes_projected_literature_nodes_and_edges():
    db = make_session()
    investigation = Investigation(
        title="Osimertinib resistance",
        slug="investigation-graph-literature",
        status="collecting",
        confidence=0.0,
        attributes={},
    )
    db.add(investigation)
    db.flush()

    publication = ScientificPublication(
        source_system="pubmed",
        source_id="36849494",
        pmid="36849494",
        doi="10.1000/flaura",
        title="Candidate mechanisms of acquired resistance to first-line osimertinib",
        journal="Test Journal",
        publication_date=None,
        authors_json=[],
        metadata_json={"clinical_trial_ids":["NCT02296125"]},
        source_url="https://pubmed.ncbi.nlm.nih.gov/36849494/",
        retrieval_ref="pubmed:pmid:36849494",
        content_hash="pub-investigation-graph-literature",
    )
    db.add(publication)
    db.flush()

    passage = ScientificPassage(
        publication_id=publication.id,
        section="Abstract",
        locator="abstract:1",
        text="First-line osimertinib in EGFRm NSCLC using plasma next-generation sequencing.",
        content_hash="passage-investigation-graph-literature",
        provenance_json={"canonical_source": True},
    )
    db.add(passage)
    db.flush()
    db.add(EvidenceLink(
        investigation_id=investigation.id,
        scientific_passage_id=passage.id,
        stance="supporting",
        weight=1.0,
    ))
    db.commit()

    project_investigation_literature_graph(db, investigation.id)
    graph = investigation_graph(db, investigation.id)

    kinds = {node["kind"] for node in graph["nodes"]}
    assert "publication" in kinds
    assert "clinical_trial" in kinds
    assert "population" in kinds
    assert "drug" in kinds
    assert "assay" in kinds

    edge_kinds = {edge["kind"] for edge in graph["edges"]}
    assert "HAS_LITERATURE" in edge_kinds
    assert "PUBLICATION_REPORTS_STUDY" in edge_kinds
    assert "STUDY_HAS_POPULATION" in edge_kinds
    assert "STUDY_USES_INTERVENTION" in edge_kinds
    assert "STUDY_USES_ASSAY" in edge_kinds

    assert graph["metrics"]["literature_passages"] == 1
    assert graph["metrics"]["literature_publications"] == 1
    assert "PubMed 36849494" in graph["metrics"]["sources"]

    publication_nodes = [node for node in graph["nodes"] if node["kind"] == "publication"]
    assert publication_nodes[0]["evidence_count"] == 1
    assert publication_nodes[0]["source_count"] == 1
    assert graph["derived"] is True
