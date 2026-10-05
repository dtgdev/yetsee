from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.domain_assertion_extraction import RULES, extract_graph_assertions
from app.knowledge_graph.writer import governed_entity, governed_relationship
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation


TEMPORAL_NORMALIZER_VERSION = "cross-domain-temporal-event-v1"
_SUPPORTED_EVENT_TYPES = {rule.event_type for rule in RULES}


def _parse_occurred_at(value: Any, fallback: datetime) -> tuple[datetime, str]:
    if value is None:
        return fallback, "observation_time"
    if isinstance(value, datetime):
        parsed = value
        precision = "timestamp"
    else:
        raw = str(value).strip()
        if not raw:
            return fallback, "observation_time"
        try:
            if len(raw) == 10:
                parsed = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
                precision = "date"
            else:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                precision = "timestamp"
        except ValueError:
            return fallback, "observation_time"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, precision


def normalize_observation_event(observation: Observation) -> dict[str, Any] | None:
    payload = observation.payload or {}
    event_payload = payload.get("domain_event")
    if isinstance(event_payload, dict):
        event = dict(event_payload)
    else:
        event_type = payload.get("event_type") or observation.metric
        event = {**payload, "type": event_type}

    event_type = str(event.get("type") or event.get("event_type") or "").strip().lower()
    if event_type not in _SUPPORTED_EVENT_TYPES:
        return None

    assertions = extract_graph_assertions(observation)
    if not assertions:
        return None

    occurred_at, time_precision = _parse_occurred_at(
        event.get("occurred_at") or event.get("event_date") or event.get("date"),
        observation.observed_at,
    )
    label = str(event.get("label") or event.get("name") or "").strip()
    if not label:
        subject = assertions[0]["subject"]["name"]
        obj = assertions[0]["object"]["name"]
        label = f"{subject} · {event_type.replace('_', ' ')} · {obj}"

    return {
        "event_type": event_type,
        "label": label,
        "occurred_at": occurred_at,
        "time_precision": time_precision,
        "observation_id": observation.id,
        "source": observation.source,
        "source_ref": observation.source_ref,
        "assertions": assertions,
        "policy": {
            "derived_event": True,
            "canonical_observation_unchanged": True,
            "free_text_inference": False,
            "normalizer": TEMPORAL_NORMALIZER_VERSION,
        },
    }


def project_temporal_events(db: Session, investigation_id: str) -> dict[str, Any]:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    links = list(
        db.scalars(
            select(EvidenceLink)
            .where(
                EvidenceLink.investigation_id == investigation_id,
                EvidenceLink.observation_id.is_not(None),
            )
            .order_by(EvidenceLink.created_at.asc())
        )
    )
    observation_ids = [link.observation_id for link in links if link.observation_id]
    observations = (
        list(
            db.scalars(
                select(Observation)
                .where(Observation.id.in_(observation_ids))
                .order_by(Observation.observed_at.asc(), Observation.id.asc())
            )
        )
        if observation_ids
        else []
    )

    normalized = [
        item
        for observation in observations
        if (item := normalize_observation_event(observation)) is not None
    ]

    event_entities = []
    relationship_ids: set[str] = set()
    involved_entity_ids: set[str] = set()

    for event in normalized:
        observation = db.get(Observation, event["observation_id"])
        if observation is None:
            continue
        event_entity = governed_entity(
            db,
            kind="event",
            canonical_name=event["label"],
            canonical_key=f"event:{event['event_type']}:{event['observation_id']}",
            attributes={
                "event_type": event["event_type"],
                "occurred_at": event["occurred_at"].isoformat(),
                "time_precision": event["time_precision"],
                "observation_id": event["observation_id"],
                "source": event["source"],
                "source_ref": event["source_ref"],
                "temporal_projection": True,
                "normalizer": TEMPORAL_NORMALIZER_VERSION,
            },
        )
        event_entities.append((event, event_entity))

        seen_roles: set[tuple[str, str]] = set()
        for assertion in event["assertions"]:
            for role, payload in (("subject", assertion["subject"]), ("object", assertion["object"])):
                role_key = (role, payload["key"])
                if role_key in seen_roles:
                    continue
                seen_roles.add(role_key)
                entity = governed_entity(
                    db,
                    kind=payload["kind"],
                    canonical_name=payload["name"],
                    canonical_key=payload["key"],
                    aliases=payload.get("aliases", []),
                    attributes={
                        **(payload.get("attributes") or {}),
                        "cross_domain_projection": True,
                    },
                )
                involved_entity_ids.add(entity.id)
                relation = governed_relationship(
                    db,
                    source=event_entity,
                    target=entity,
                    kind="EVENT_INVOLVES",
                    confidence=float(assertion.get("confidence", 1.0)),
                    evidence_ids=[event["observation_id"]],
                    first_seen=event["occurred_at"],
                    last_seen=event["occurred_at"],
                    provenance={
                        "method": TEMPORAL_NORMALIZER_VERSION,
                        "investigation_id": investigation_id,
                        "investigation_ids": [investigation_id],
                        "observation_id": event["observation_id"],
                        "observation_ids": [event["observation_id"]],
                        "canonical_evidence_kind": "observation",
                        "event_type": event["event_type"],
                        "event_role": role,
                        "occurred_at": event["occurred_at"].isoformat(),
                        "time_precision": event["time_precision"],
                        "temporal_projection": True,
                    },
                )
                relationship_ids.add(relation.id)

    # Only assert order when timestamps are strictly ordered. Equal timestamps
    # remain unordered because observation precision may not support sequencing.
    groups: dict[datetime, list[tuple[dict[str, Any], Any]]] = {}
    for item in event_entities:
        groups.setdefault(item[0]["occurred_at"], []).append(item)
    ordered_times = sorted(groups)
    precedence_count = 0
    for earlier_time, later_time in zip(ordered_times, ordered_times[1:]):
        for earlier_event, earlier_entity in groups[earlier_time]:
            for later_event, later_entity in groups[later_time]:
                evidence_ids = sorted({
                    earlier_event["observation_id"],
                    later_event["observation_id"],
                })
                relation = governed_relationship(
                    db,
                    source=earlier_entity,
                    target=later_entity,
                    kind="EVENT_PRECEDES",
                    confidence=1.0,
                    evidence_ids=evidence_ids,
                    first_seen=earlier_time,
                    last_seen=later_time,
                    provenance={
                        "method": TEMPORAL_NORMALIZER_VERSION,
                        "investigation_id": investigation_id,
                        "investigation_ids": [investigation_id],
                        "observation_ids": evidence_ids,
                        "canonical_evidence_kind": "observation",
                        "earlier_occurred_at": earlier_time.isoformat(),
                        "later_occurred_at": later_time.isoformat(),
                        "temporal_order_only": True,
                        "causality_inferred": False,
                    },
                )
                relationship_ids.add(relation.id)
                precedence_count += 1

    db.commit()
    return {
        "investigation_id": investigation_id,
        "observation_count": len(observations),
        "normalized_event_count": len(event_entities),
        "event_node_count": len(event_entities),
        "involved_entity_count": len(involved_entity_ids),
        "relationship_count": len(relationship_ids),
        "precedence_relationship_count": precedence_count,
        "timeline": [
            {
                "event_id": entity.id,
                "event_type": event["event_type"],
                "label": event["label"],
                "occurred_at": event["occurred_at"].isoformat(),
                "time_precision": event["time_precision"],
                "observation_id": event["observation_id"],
            }
            for event, entity in sorted(event_entities, key=lambda item: (item[0]["occurred_at"], item[1].id))
        ],
        "policy": {
            "events_are_derived_graph_objects": True,
            "observations_remain_canonical_evidence": True,
            "event_time_distinct_from_observation_time": True,
            "equal_timestamps_are_not_ordered": True,
            "temporal_order_does_not_imply_causality": True,
            "free_text_inference_disabled": True,
            "normalizer": TEMPORAL_NORMALIZER_VERSION,
        },
    }
