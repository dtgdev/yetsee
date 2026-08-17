from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel.events import publish_event
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation


def _canonical(value: str | None) -> str:
    return " ".join((value or "").lower().replace("-", " ").split())


def match_observations_to_investigations(db: Session, observation_ids: list[str]) -> dict[str, list[str]]:
    """Attach obvious topic matches as neutral investigation evidence.

    Matching is intentionally conservative in Alpha: an observation topic must equal the
    investigation title/slug canonical form. The link is neutral so ingestion can improve
    source coverage without silently asserting that the observation supports a hypothesis.
    """
    if not observation_ids:
        return {}
    observations = list(db.scalars(select(Observation).where(Observation.id.in_(observation_ids))))
    investigations = list(db.scalars(select(Investigation)))
    by_topic: dict[str, list[Investigation]] = defaultdict(list)
    for investigation in investigations:
        by_topic[_canonical(investigation.title)].append(investigation)
        by_topic[_canonical(investigation.slug)].append(investigation)

    matched: dict[str, list[str]] = defaultdict(list)
    for observation in observations:
        topic = _canonical(observation.topic)
        if not topic:
            continue
        seen_investigations: set[str] = set()
        for investigation in by_topic.get(topic, []):
            if investigation.id in seen_investigations:
                continue
            seen_investigations.add(investigation.id)
            existing = db.scalar(
                select(EvidenceLink.id).where(
                    EvidenceLink.investigation_id == investigation.id,
                    EvidenceLink.observation_id == observation.id,
                )
            )
            if existing:
                continue
            db.add(
                EvidenceLink(
                    investigation_id=investigation.id,
                    observation_id=observation.id,
                    stance="neutral",
                    weight=1.0,
                )
            )
            matched[investigation.id].append(observation.id)
            publish_event(
                db,
                event_type="InvestigationEvidenceObserved",
                aggregate_type="investigation",
                aggregate_id=investigation.id,
                payload={
                    "observation_id": observation.id,
                    "source": observation.source,
                    "topic": observation.topic,
                    "stance": "neutral",
                    "matching_method": "exact_canonical_topic_v1",
                },
                metadata={"actor_type": "system", "component": "signal_matcher"},
            )
    db.commit()
    return dict(matched)
