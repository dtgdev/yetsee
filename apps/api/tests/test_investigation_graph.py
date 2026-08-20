from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.discovery_engine.engine import promote_candidate
from app.knowledge_graph.investigation import investigation_graph
from app.models.discovery import DiscoveryCandidate
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
