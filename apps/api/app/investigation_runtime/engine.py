from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.investigation_runtime.confidence import calculate_confidence
from app.investigation_runtime.state import allowed_transitions, can_transition, normalize_state
from app.kernel.events import publish_event, replay_events
from app.kernel.investigations import commit_investigation, history
from app.models.evidence import EvidenceLink
from app.models.agent import AgentFinding, AgentTask
from app.models.hypothesis import Hypothesis, HypothesisConfidenceHistory, HypothesisEvidenceLink
from app.models.investigation import Investigation
from app.models.kernel import InvestigationRevision
from app.models.observation import Observation
from app.models.reasoning import ReasoningResult, ReasoningRun


def _require_investigation(db: Session, investigation_id: str) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError(investigation_id)
    return investigation


def _require_hypothesis(db: Session, investigation_id: str, hypothesis_id: str) -> Hypothesis:
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if hypothesis is None or hypothesis.investigation_id != investigation_id:
        raise KeyError(hypothesis_id)
    return hypothesis


def transition_investigation(
    db: Session,
    investigation_id: str,
    target_state: str,
    *,
    reason: str,
    actor_type: str = "human",
    actor_id: str | None = None,
) -> Investigation:
    investigation = _require_investigation(db, investigation_id)
    current = normalize_state(investigation.status).value
    target = normalize_state(target_state).value
    if not can_transition(current, target):
        raise ValueError(f"Invalid investigation transition: {current} -> {target}")
    if current == target:
        return investigation
    investigation.status = target
    publish_event(
        db,
        event_type="InvestigationStateChanged",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={"from": current, "to": target, "reason": reason},
        metadata={"actor_type": actor_type, "actor_id": actor_id},
    )
    commit_investigation(
        db,
        investigation,
        message=f"State changed {current} -> {target}: {reason}",
        change_type="state_transition",
        author_type=actor_type,
        author_id=actor_id,
    )
    db.commit()
    db.refresh(investigation)
    return investigation


def add_hypothesis(
    db: Session,
    investigation_id: str,
    *,
    title: str,
    description: str | None = None,
    confidence: float = 0.5,
    created_by_type: str = "human",
    created_by_id: str | None = None,
) -> Hypothesis:
    investigation = _require_investigation(db, investigation_id)
    bounded = max(0.0, min(1.0, confidence))
    hypothesis = Hypothesis(
        investigation_id=investigation.id,
        title=title,
        description=description,
        prior_confidence=bounded,
        confidence=bounded,
        created_by_type=created_by_type,
        created_by_id=created_by_id,
    )
    db.add(hypothesis)
    db.flush()
    publish_event(
        db,
        event_type="HypothesisAdded",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={"hypothesis_id": hypothesis.id, "title": title, "confidence": hypothesis.confidence},
        metadata={"actor_type": created_by_type, "actor_id": created_by_id},
    )
    commit_investigation(
        db,
        investigation,
        message=f"Added hypothesis: {title}",
        change_type="hypothesis_added",
        author_type=created_by_type,
        author_id=created_by_id,
    )
    db.commit()
    db.refresh(hypothesis)
    return hypothesis


def recalculate_hypothesis_confidence(
    db: Session,
    investigation_id: str,
    hypothesis_id: str,
    *,
    reason: str = "Recalculated from directional evidence",
    trigger: str = "manual",
    observation_id: str | None = None,
    author_type: str = "system",
    author_id: str | None = None,
    commit: bool = True,
) -> dict:
    investigation = _require_investigation(db, investigation_id)
    hypothesis = _require_hypothesis(db, investigation.id, hypothesis_id)

    rows = db.execute(
        select(
            HypothesisEvidenceLink.stance,
            func.coalesce(func.sum(HypothesisEvidenceLink.weight), 0.0),
        )
        .where(HypothesisEvidenceLink.hypothesis_id == hypothesis.id)
        .group_by(HypothesisEvidenceLink.stance)
    ).all()
    weights = {stance: float(weight or 0.0) for stance, weight in rows}
    result = calculate_confidence(
        prior=hypothesis.prior_confidence,
        supporting_weight=weights.get("supporting", 0.0),
        contradicting_weight=weights.get("contradicting", 0.0),
        neutral_weight=weights.get("neutral", 0.0),
    )
    old = float(hypothesis.confidence)
    new = round(result.posterior, 6)
    hypothesis.confidence = new

    history_row = HypothesisConfidenceHistory(
        hypothesis_id=hypothesis.id,
        old_confidence=old,
        new_confidence=new,
        prior_confidence=hypothesis.prior_confidence,
        supporting_weight=result.supporting_weight,
        contradicting_weight=result.contradicting_weight,
        neutral_weight=result.neutral_weight,
        reason=reason,
        trigger=trigger,
        observation_id=observation_id,
    )
    db.add(history_row)
    db.flush()

    publish_event(
        db,
        event_type="HypothesisConfidenceChanged" if old != new else "HypothesisRecalculated",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={
            "hypothesis_id": hypothesis.id,
            "old_confidence": old,
            "new_confidence": new,
            "prior_confidence": hypothesis.prior_confidence,
            "supporting_weight": result.supporting_weight,
            "contradicting_weight": result.contradicting_weight,
            "neutral_weight": result.neutral_weight,
            "trigger": trigger,
            "observation_id": observation_id,
        },
        metadata={"actor_type": author_type, "actor_id": author_id},
    )

    if commit:
        commit_investigation(
            db,
            investigation,
            message=f"Hypothesis confidence {old:.3f} -> {new:.3f}: {reason}",
            change_type="hypothesis_confidence_changed",
            author_type=author_type,
            author_id=author_id,
        )
    db.commit()
    db.refresh(hypothesis)
    db.refresh(history_row)
    return {
        "hypothesis": hypothesis,
        "history": history_row,
        "evidence": {
            "supporting_weight": result.supporting_weight,
            "contradicting_weight": result.contradicting_weight,
            "neutral_weight": result.neutral_weight,
        },
    }


def confidence_history(db: Session, investigation_id: str, hypothesis_id: str) -> list[HypothesisConfidenceHistory]:
    _require_investigation(db, investigation_id)
    _require_hypothesis(db, investigation_id, hypothesis_id)
    return list(db.scalars(
        select(HypothesisConfidenceHistory)
        .where(HypothesisConfidenceHistory.hypothesis_id == hypothesis_id)
        .order_by(HypothesisConfidenceHistory.created_at.asc())
    ))


def attach_hypothesis_evidence(
    db: Session,
    investigation_id: str,
    hypothesis_id: str,
    *,
    observation_id: str,
    stance: str,
    weight: float = 1.0,
    rationale: str | None = None,
    author_type: str = "human",
    author_id: str | None = None,
) -> HypothesisEvidenceLink:
    investigation = _require_investigation(db, investigation_id)
    hypothesis = _require_hypothesis(db, investigation.id, hypothesis_id)
    if db.get(Observation, observation_id) is None:
        raise KeyError(observation_id)
    if stance not in {"supporting", "contradicting", "neutral"}:
        raise ValueError("stance must be supporting, contradicting, or neutral")

    existing = db.scalar(
        select(HypothesisEvidenceLink).where(
            HypothesisEvidenceLink.hypothesis_id == hypothesis.id,
            HypothesisEvidenceLink.observation_id == observation_id,
            HypothesisEvidenceLink.stance == stance,
        )
    )
    if existing:
        return existing

    link = HypothesisEvidenceLink(
        hypothesis_id=hypothesis.id,
        observation_id=observation_id,
        stance=stance,
        weight=max(0.0, weight),
        rationale=rationale,
    )
    db.add(link)
    inv_link = db.scalar(
        select(EvidenceLink).where(
            EvidenceLink.investigation_id == investigation.id,
            EvidenceLink.observation_id == observation_id,
            EvidenceLink.stance == stance,
        )
    )
    if inv_link is None:
        db.add(EvidenceLink(
            investigation_id=investigation.id,
            observation_id=observation_id,
            stance=stance,
            weight=max(0.0, weight),
        ))
    db.flush()
    publish_event(
        db,
        event_type="EvidenceLinked",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={
            "hypothesis_id": hypothesis.id,
            "observation_id": observation_id,
            "stance": stance,
            "weight": link.weight,
        },
    )
    # Confidence recalculation owns the commit so evidence + confidence become one
    # atomic, replayable investigation revision.
    recalculate_hypothesis_confidence(
        db,
        investigation.id,
        hypothesis.id,
        reason=f"Linked {stance} evidence",
        trigger="evidence_linked",
        observation_id=observation_id,
        author_type=author_type,
        author_id=author_id,
        commit=True,
    )
    db.refresh(link)
    return link


def investigation_workspace(db: Session, investigation_id: str) -> dict:
    investigation = _require_investigation(db, investigation_id)
    hypotheses = list(db.scalars(
        select(Hypothesis).where(Hypothesis.investigation_id == investigation.id).order_by(Hypothesis.created_at.asc())
    ))
    hypothesis_ids = [item.id for item in hypotheses]
    links = []
    confidence_rows = []
    if hypothesis_ids:
        links = list(db.scalars(
            select(HypothesisEvidenceLink)
            .where(HypothesisEvidenceLink.hypothesis_id.in_(hypothesis_ids))
            .order_by(HypothesisEvidenceLink.created_at.asc())
        ))
        confidence_rows = list(db.scalars(
            select(HypothesisConfidenceHistory)
            .where(HypothesisConfidenceHistory.hypothesis_id.in_(hypothesis_ids))
            .order_by(HypothesisConfidenceHistory.created_at.asc())
        ))
    evidence = list(db.scalars(
        select(EvidenceLink).where(EvidenceLink.investigation_id == investigation.id).order_by(EvidenceLink.created_at.asc())
    ))
    observation_ids = {item.observation_id for item in evidence if item.observation_id}
    observation_ids.update(item.observation_id for item in links if item.observation_id)
    observations = []
    if observation_ids:
        observations = list(db.scalars(
            select(Observation)
            .where(Observation.id.in_(observation_ids))
            .order_by(Observation.observed_at.desc())
        ))
    return {
        "investigation": investigation,
        "lifecycle": {
            "current": normalize_state(investigation.status).value,
            "allowed_transitions": allowed_transitions(investigation.status),
        },
        "hypotheses": hypotheses,
        "hypothesis_evidence": links,
        "confidence_history": confidence_rows,
        "evidence": evidence,
        "observations": observations,
        "agent_findings": list(db.scalars(
            select(AgentFinding)
            .where(AgentFinding.target_id == investigation.id)
            .order_by(AgentFinding.created_at.desc())
            .limit(100)
        )),
        "agent_tasks": list(db.scalars(
            select(AgentTask)
            .where(AgentTask.target_id == investigation.id)
            .order_by(AgentTask.created_at.desc())
            .limit(50)
        )),
        "reasoning_runs": list(db.scalars(
            select(ReasoningRun)
            .where(ReasoningRun.investigation_id == investigation.id)
            .order_by(ReasoningRun.started_at.desc())
            .limit(50)
        )),
        "reasoning_results": list(db.scalars(
            select(ReasoningResult)
            .where(ReasoningResult.investigation_id == investigation.id)
            .order_by(ReasoningResult.created_at.desc())
            .limit(50)
        )),
        "timeline": replay_events(db, "investigation", investigation.id),
        "revisions": history(db, investigation.id),
    }


def investigation_diff(db: Session, investigation_id: str, from_revision: int, to_revision: int) -> dict:
    _require_investigation(db, investigation_id)
    revisions = list(db.scalars(
        select(InvestigationRevision).where(
            InvestigationRevision.investigation_id == investigation_id,
            InvestigationRevision.revision_number.in_([from_revision, to_revision]),
        )
    ))
    by_number = {item.revision_number: item for item in revisions}
    if from_revision not in by_number or to_revision not in by_number:
        raise KeyError("revision")
    before = by_number[from_revision].snapshot
    after = by_number[to_revision].snapshot
    changed = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed[key] = {"from": before.get(key), "to": after.get(key)}
    return {
        "investigation_id": investigation_id,
        "from_revision": from_revision,
        "to_revision": to_revision,
        "changed": changed,
    }
