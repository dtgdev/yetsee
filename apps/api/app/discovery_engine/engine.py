from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.discovery_engine.registry import registry
from app.models.discovery import DetectorRun, DiscoveryCandidate
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.kernel.investigations import commit_investigation
from app.kernel.events import publish_event
from app.models.observation import Observation
from app.models.signal import Signal
from app.models.feature import Feature
from app.models.semantic import SemanticConcept
from app.feature_engine.engine import recompute_features
from app.knowledge_graph.engine import rebuild_graph
from app.semantic_engine.engine import recompute_semantics


def _slug(value: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value.lower())) or "investigation"



_KIND_RANK = {
    "behavior": 10, "technology": 9, "market": 9, "industry": 8, "product_category": 8,
    "company": 7, "product": 7, "topic": 5, "keyword": 1,
}


def _preferred_semantic_subject(db: Session, raw_subject: str, evidence_ids: list[str]) -> tuple[str, dict]:
    if not evidence_ids:
        return raw_subject, {}
    concepts = list(db.scalars(select(SemanticConcept).where(SemanticConcept.observation_id.in_(evidence_ids))))
    eligible = [
        c for c in concepts
        if c.kind != "keyword" and c.method != "title_fallback_v1" and c.confidence >= 0.80
    ]
    if not eligible:
        return raw_subject, {}
    # Prefer durable thematic concepts over article/company mentions. If the same
    # concept appears in multiple evidence items, that recurrence is rewarded.
    counts: dict[str, int] = defaultdict(int)
    best: dict[str, SemanticConcept] = {}
    for concept in eligible:
        counts[concept.canonical_key] += 1
        current = best.get(concept.canonical_key)
        if current is None or concept.confidence > current.confidence:
            best[concept.canonical_key] = concept
    selected = max(
        best.values(),
        key=lambda c: (counts[c.canonical_key], _KIND_RANK.get(c.kind, 3), c.confidence),
    )
    return selected.canonical_key, {
        "semantic_name": selected.canonical_name,
        "semantic_kind": selected.kind,
        "semantic_method": selected.method,
        "semantic_confidence": selected.confidence,
        "semantic_evidence_count": counts[selected.canonical_key],
    }


def _quality_status(evidence_count: int, source_count: int, detector_count: int) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if evidence_count < 3:
        reasons.append("fewer than 3 independent evidence items")
    if source_count < 2:
        reasons.append("fewer than 2 independent sources")
    if detector_count < 2:
        reasons.append("fewer than 2 agreeing discovery models")
    return ("candidate" if not reasons else "watch", reasons)

def run_discovery(db: Session, hours: int = 24 * 30) -> dict:
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    observations = list(db.scalars(select(Observation).where(Observation.observed_at >= start).order_by(Observation.observed_at)))
    detections_by_subject: dict[str, list] = defaultdict(list)
    run_ids: list[str] = []

    semantic_result = recompute_semantics(db, hours=hours)
    feature_result = recompute_features(db, hours=hours)
    feature_run_ids = set(feature_result["feature_runs"])
    graph_result = rebuild_graph(db, hours=hours)
    graph_run_id = graph_result.get("run_id")
    feature_rows = list(db.scalars(select(Feature).order_by(Feature.computed_at.desc()).limit(20000)))
    features = [
        item
        for item in feature_rows
        if item.attributes.get("feature_run_id") in feature_run_ids
        or item.attributes.get("graph_run_id") == graph_run_id
    ]

    for detector in registry.all():
        manifest = detector.manifest()
        run = DetectorRun(detector_id=manifest.id, detector_version=manifest.version, status="running", started_at=datetime.now(timezone.utc), observation_count=len(observations))
        db.add(run)
        db.flush()
        try:
            detections = detector.detect(observations, features)
            for detection in detections:
                detections_by_subject[detection.subject].append((manifest.id, detection))
                observation_id = detection.evidence_ids[-1] if detection.evidence_ids else None
                if observation_id:
                    db.add(Signal(
                        observation_id=observation_id,
                        kind=detection.kind,
                        subject=detection.subject,
                        strength=detection.strength,
                        confidence=detection.confidence,
                        detector=manifest.id,
                        attributes={**detection.attributes, "explanation": detection.explanation, "evidence_ids": detection.evidence_ids, "detector_run_id": run.id},
                    ))
                    run.signal_count += 1
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)[:4000]
            run.finished_at = datetime.now(timezone.utc)
        run_ids.append(run.id)

    # Candidates are living syntheses, not evidence. Recompute the current view.
    # Semantic concepts may merge source-specific article titles into a durable
    # concept before quality gates decide whether the result is WATCH or CANDIDATE.
    db.execute(delete(DiscoveryCandidate).where(DiscoveryCandidate.status.in_(["candidate", "watch"])))
    canonical_entries: dict[str, list] = defaultdict(list)
    semantic_metadata: dict[str, dict] = {}
    for raw_subject, entries in detections_by_subject.items():
        evidence_ids = list(dict.fromkeys(eid for _, detection in entries for eid in detection.evidence_ids))
        canonical_subject, metadata = _preferred_semantic_subject(db, raw_subject, evidence_ids)
        canonical_entries[canonical_subject].extend(entries)
        if metadata:
            semantic_metadata[canonical_subject] = metadata

    observation_source = {item.id: item.source for item in observations}
    candidates: list[DiscoveryCandidate] = []
    status_counts = {"candidate": 0, "watch": 0}
    for subject, entries in canonical_entries.items():
        # A detector may contribute multiple detections after semantic merging. Keep
        # its strongest score so detector agreement remains honest.
        strongest: dict[str, object] = {}
        for detector_id, detection in entries:
            current = strongest.get(detector_id)
            if current is None or detection.strength > current.strength:
                strongest[detector_id] = detection
        compact_entries = list(strongest.items())
        detector_scores = {detector_id: round(detection.strength, 4) for detector_id, detection in compact_entries}
        weighted = [detection.strength * detection.confidence for _, detection in compact_entries]
        detector_bonus = min(0.2, max(0, len(compact_entries) - 1) * 0.06)
        score = min(1.0, (sum(weighted) / len(weighted)) + detector_bonus)
        confidence = min(1.0, sum(d.confidence for _, d in compact_entries) / len(compact_entries) + detector_bonus / 2)
        evidence_ids = list(dict.fromkeys(eid for _, d in compact_entries for eid in d.evidence_ids))
        sources = sorted({observation_source[eid] for eid in evidence_ids if eid in observation_source})
        status, quality_reasons = _quality_status(len(evidence_ids), len(sources), len(compact_entries))
        metadata = semantic_metadata.get(subject, {})
        display_name = metadata.get("semantic_name", subject.title())
        candidate = DiscoveryCandidate(
            canonical_key=subject,
            title=display_name,
            status=status,
            score=score,
            confidence=confidence,
            detector_count=len(compact_entries),
            evidence_count=len(evidence_ids),
            summary=f"{len(compact_entries)} independent detector(s) surfaced {display_name} from {len(evidence_ids)} evidence item(s) across {len(sources)} source(s).",
            detector_scores=detector_scores,
            evidence_ids=evidence_ids,
            attributes={
                "detectors": [detector_id for detector_id, _ in compact_entries],
                "window_hours": hours,
                "source_count": len(sources),
                "sources": sources,
                "quality_gate": {"status": status, "reasons": quality_reasons},
                **metadata,
            },
        )
        db.add(candidate)
        candidates.append(candidate)
        status_counts[status] += 1
    db.commit()
    for item in candidates:
        db.refresh(item)
    return {
        "observations": len(observations),
        "semantic_run": semantic_result,
        "feature_runs": list(feature_run_ids),
        "graph_run": graph_result,
        "features": len(features),
        "detector_runs": run_ids,
        "candidates": len(candidates),
        "status_counts": status_counts,
    }


def promote_candidate(
    db: Session,
    candidate_id: str,
    *,
    allow_override: bool = False,
    override_reason: str | None = None,
) -> Investigation:
    candidate = db.get(DiscoveryCandidate, candidate_id)
    if candidate is None:
        raise KeyError(candidate_id)
    overridden = candidate.status == "watch" and allow_override
    if candidate.status == "watch" and not allow_override:
        raise ValueError("Candidate is on WATCH and has not passed evidence/source/model quality gates")
    if overridden and not (override_reason or "").strip():
        raise ValueError("A manual promotion override requires a reason")
    slug = _slug(candidate.title)
    existing = db.scalar(select(Investigation).where(Investigation.slug == slug))
    if existing:
        candidate.status = "promoted"
        db.commit()
        return existing
    investigation = Investigation(
        title=candidate.title,
        slug=slug,
        status="collecting",
        confidence=candidate.confidence,
        summary=candidate.summary,
        hypothesis=f"Observed changes around {candidate.title} may represent an emerging behavior or market shift.",
        counter_thesis="The pattern may be transient, source-specific, duplicated, or driven by a short-lived news cycle.",
        attributes={
            "candidate_id": candidate.id,
            "detector_scores": candidate.detector_scores,
            "discovery_score": candidate.score,
            "promotion": {
                "mode": "manual_override" if overridden else "quality_gate",
                "override_reason": override_reason if overridden else None,
                "original_status": candidate.status,
                "quality_gate": (candidate.attributes or {}).get("quality_gate", {}),
            },
        },
    )
    db.add(investigation)
    db.flush()
    for observation_id in candidate.evidence_ids:
        db.add(EvidenceLink(investigation_id=investigation.id, observation_id=observation_id, stance="supporting", weight=1.0))
    candidate.status = "promoted"
    if overridden:
        publish_event(
            db,
            event_type="CandidatePromotionOverridden",
            aggregate_type="investigation",
            aggregate_id=investigation.id,
            payload={
                "candidate_id": candidate.id,
                "reason": override_reason,
                "quality_gate": (candidate.attributes or {}).get("quality_gate", {}),
            },
            metadata={"actor_type": "human", "mode": "development_override"},
        )
    commit_investigation(
        db,
        investigation,
        message=(
            f"Promoted from discovery candidate {candidate.id} using manual override: {override_reason}"
            if overridden
            else f"Promoted from discovery candidate {candidate.id}"
        ),
        change_type="candidate_promotion",
        author_type="discovery_engine",
        author_id="ensemble",
    )
    db.commit()
    db.refresh(investigation)
    return investigation
