from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.kernel import KernelEvent
from app.kernel.commands import current_command_context


def publish_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str | None = None,
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> KernelEvent:
    sequence = 1
    if aggregate_id:
        current = db.scalar(
            select(func.max(KernelEvent.sequence)).where(
                KernelEvent.aggregate_type == aggregate_type,
                KernelEvent.aggregate_id == aggregate_id,
            )
        )
        sequence = int(current or 0) + 1
    event_metadata = dict(metadata or {})
    command_context = current_command_context()
    if command_context is not None:
        event_metadata.setdefault("command_id", command_context.command_id)
        event_metadata.setdefault("command_type", command_context.command_type)
        event_metadata.setdefault("correlation_id", command_context.correlation_id)
        if command_context.causation_id:
            event_metadata.setdefault("causation_id", command_context.causation_id)
        event_metadata.setdefault("command_actor_type", command_context.actor_type)
        if command_context.actor_id:
            event_metadata.setdefault("command_actor_id", command_context.actor_id)
        event_metadata.setdefault("actor_type", command_context.actor_type)
        if command_context.actor_id:
            event_metadata.setdefault("actor_id", command_context.actor_id)
    event = KernelEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        sequence=sequence,
        payload=payload or {},
        metadata_json=event_metadata,
    )
    db.add(event)
    db.flush()
    return event


def replay_events(db: Session, aggregate_type: str, aggregate_id: str) -> list[KernelEvent]:
    return list(
        db.scalars(
            select(KernelEvent)
            .where(
                KernelEvent.aggregate_type == aggregate_type,
                KernelEvent.aggregate_id == aggregate_id,
            )
            .order_by(KernelEvent.sequence.asc(), KernelEvent.occurred_at.asc())
        )
    )


def event_summary(db: Session) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(KernelEvent)) or 0
    rows = db.execute(
        select(KernelEvent.event_type, func.count(KernelEvent.id))
        .group_by(KernelEvent.event_type)
        .order_by(func.count(KernelEvent.id).desc())
    ).all()
    return {"events": total, "types": [{"event_type": t, "count": c} for t, c in rows]}
