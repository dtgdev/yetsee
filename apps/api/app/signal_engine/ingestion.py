from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.connector import ConnectorRun, ConnectorState
from app.models.observation import Observation
from app.signal_engine.hashing import observation_hash
from app.signal_engine.registry import registry
from app.kernel.events import publish_event


def run_connector(db: Session, connector_id: str) -> ConnectorRun:
    connector = registry.get(connector_id)
    manifest = connector.manifest()
    state = db.scalar(select(ConnectorState).where(ConnectorState.connector_id == connector_id))
    if state is None:
        state = ConnectorState(connector_id=connector_id)
        db.add(state)
        db.flush()

    run = ConnectorRun(
        connector_id=connector_id,
        connector_version=manifest.version,
        status="running",
        started_at=datetime.now(timezone.utc),
        cursor_before=state.cursor,
    )
    db.add(run)
    db.flush()
    publish_event(
        db, event_type="ConnectorRunStarted", aggregate_type="connector", aggregate_id=connector_id,
        payload={"run_id": run.id, "connector_version": manifest.version, "cursor_before": state.cursor},
        metadata={"actor_type": "connector", "actor_id": connector_id},
    )
    db.commit()
    db.refresh(run)

    try:
        page = connector.fetch(state.cursor)
        run.fetched_count = len(page.items)
        accepted_observation_ids: list[str] = []
        for raw in page.items:
            normalized = connector.normalize(raw)
            errors = connector.validate(normalized)
            if errors:
                run.rejected_count += 1
                continue

            checksum = observation_hash(normalized)
            existing = db.scalar(select(Observation.id).where(Observation.content_hash == checksum))
            if existing:
                run.duplicate_count += 1
                continue

            observation = Observation(
                source=normalized.source,
                source_ref=normalized.source_ref,
                topic=normalized.topic,
                metric=normalized.metric,
                value=normalized.value,
                observed_at=normalized.observed_at,
                payload={
                    **normalized.payload,
                    "provenance": {
                        "connector_id": manifest.id,
                        "connector_version": manifest.version,
                        "run_id": run.id,
                    },
                },
                content_hash=checksum,
            )
            db.add(observation)
            db.flush()
            accepted_observation_ids.append(observation.id)
            publish_event(
                db, event_type="ObservationCreated", aggregate_type="observation", aggregate_id=observation.id,
                payload={"source": observation.source, "topic": observation.topic, "metric": observation.metric, "connector_run_id": run.id},
                metadata={"actor_type": "connector", "actor_id": connector_id},
            )
            run.accepted_count += 1

        state.cursor = page.next_cursor
        state.last_success_at = datetime.now(timezone.utc)
        state.consecutive_failures = 0
        run.cursor_after = page.next_cursor
        run.status = "succeeded"
        run.metadata_json = {**(run.metadata_json or {}), "accepted_observation_ids": accepted_observation_ids}
        run.finished_at = datetime.now(timezone.utc)
        publish_event(
            db, event_type="ConnectorRunCompleted", aggregate_type="connector", aggregate_id=connector_id,
            payload={"run_id": run.id, "fetched": run.fetched_count, "accepted": run.accepted_count, "duplicates": run.duplicate_count, "rejected": run.rejected_count},
            metadata={"actor_type": "connector", "actor_id": connector_id},
        )
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = db.get(ConnectorRun, run.id)
        state = db.scalar(select(ConnectorState).where(ConnectorState.connector_id == connector_id))
        if run is not None:
            run.status = "failed"
            run.error = str(exc)[:4000]
            run.finished_at = datetime.now(timezone.utc)
        if state is not None:
            state.last_error_at = datetime.now(timezone.utc)
            state.consecutive_failures += 1
        db.commit()
        if run is None:
            raise
        db.refresh(run)
        return run


def run_all_connectors(db: Session, include_demo: bool = False) -> list[ConnectorRun]:
    runs: list[ConnectorRun] = []
    for connector in registry.all():
        if connector.manifest().id == "demo" and not include_demo:
            continue
        runs.append(run_connector(db, connector.manifest().id))
    return runs
