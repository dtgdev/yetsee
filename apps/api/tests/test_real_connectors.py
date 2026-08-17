from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.kernel import KernelCommand, execute_command
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.kernel import KernelCommandLog, KernelEvent
from app.signal_engine.connectors.reddit import RedditConnector
from app.signal_engine.contracts import RawItem
from app.signal_engine.registry import registry


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_registry_exposes_real_connectors():
    ids = {connector.manifest().id for connector in registry.all()}
    assert {"reddit", "google_trends"}.issubset(ids)


def test_reddit_normalizes_query_topic_and_engagement():
    connector = RedditConnector()
    raw = RawItem(
        source_ref="abc123",
        observed_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
        payload={
            "id": "abc123",
            "title": "A running club post",
            "score": 40,
            "num_comments": 12,
            "yetsee_query_topic": "running clubs",
        },
    )
    observation = connector.normalize(raw)
    assert observation.source == "reddit"
    assert observation.topic == "running clubs"
    assert observation.metric == "discussion_engagement"
    assert observation.value == 52.0


def test_kernel_run_connector_matches_neutral_evidence_and_refreshes():
    db = make_session()
    investigation = Investigation(
        title="Running Clubs",
        slug="running-clubs",
        status="collecting",
        confidence=0.7,
        attributes={},
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    command = KernelCommand(
        command_type="RunConnector",
        aggregate_type="connector",
        aggregate_id="demo",
        payload={"connector_id": "demo"},
        correlation_id="connector-correlation",
    )
    run = execute_command(db, command)
    assert run.status == "succeeded"

    links = list(db.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation.id)))
    assert len(links) == 2
    assert {link.stance for link in links} == {"neutral"}

    outer = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == command.id))
    assert outer is not None and outer.status == "completed"
    refresh = db.scalar(
        select(KernelCommandLog).where(
            KernelCommandLog.command_type == "RefreshInvestigation",
            KernelCommandLog.aggregate_id == investigation.id,
        )
    )
    assert refresh is not None
    assert refresh.correlation_id == "connector-correlation"
    assert refresh.causation_id == command.id

    events = list(db.scalars(select(KernelEvent)))
    assert any(event.event_type == "ObservationCreated" for event in events)
    matched = [event for event in events if event.event_type == "InvestigationEvidenceObserved"]
    assert len(matched) == 2
    assert all(event.payload["stance"] == "neutral" for event in matched)
