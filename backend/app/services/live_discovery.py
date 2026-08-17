from datetime import datetime
from sqlalchemy.orm import Session
from app.connectors.registry import live_connectors
from app.domain.models import DiscoveryRun, Opportunity, OpportunityEvidence, Signal, Trend
from app.services.topic_discovery import discover_topics


def _opportunity_specs(topic: str, momentum: float):
    display = topic.title()
    base = min(92.0, 62.0 + momentum * 28.0)
    return [
        ("investment", f"Companies exposed to {display}", round(base, 1)),
        ("startup", f"Build for the {display} shift", round(min(95.0, base + 3), 1)),
        ("commerce", f"Products serving {display} demand", round(max(60.0, base - 4), 1)),
    ]


async def run_live(db: Session):
    run = DiscoveryRun(mode="live", status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    observations = []
    connector_results = {}
    for connector in live_connectors():
        try:
            rows = await connector.fetch()
            observations.extend(rows)
            connector_results[connector.name] = {"status": "ok", "observations": len(rows)}
        except Exception as exc:
            connector_results[connector.name] = {"status": "error", "message": str(exc)[:180]}

    topics = discover_topics(observations)
    created_signals = 0
    created_opportunities = 0

    for candidate in topics:
        topic = candidate["topic"]
        evidence_signals: list[Signal] = []
        for obs in candidate["observations"]:
            signal = Signal(
                source=obs.source,
                topic=topic,
                metric="emerging_mention",
                value=1.0,
                observed_at=obs.published_at or datetime.utcnow(),
                evidence={
                    "title": obs.title,
                    "url": obs.url,
                    "metadata": obs.metadata or {},
                    "live": True,
                },
            )
            db.add(signal)
            evidence_signals.append(signal)
            created_signals += 1

        momentum = min(1.0, 0.30 + candidate["score"] / 20.0)
        confidence = min(0.96, 0.48 + len(candidate["sources"]) * 0.12 + len(evidence_signals) * 0.025)
        name = topic.title()
        trend = db.query(Trend).filter(Trend.name == name).first()
        if not trend:
            trend = Trend(name=name)
            db.add(trend)
        trend.stage = "emerging" if momentum < 0.7 else "accelerating"
        trend.momentum = momentum
        trend.confidence = confidence
        trend.thesis = f"{name} is appearing across {len(candidate['sources'])} source types with repeated recent mentions."
        trend.updated_at = datetime.utcnow()
        db.flush()

        db.query(OpportunityEvidence).filter(
            OpportunityEvidence.opportunity_id.in_(
                db.query(Opportunity.id).filter(Opportunity.trend_id == trend.id)
            )
        ).delete(synchronize_session=False)
        db.query(Opportunity).filter(Opportunity.trend_id == trend.id).delete(synchronize_session=False)
        db.flush()

        for kind, title, score in _opportunity_specs(topic, momentum):
            opp = Opportunity(
                trend_id=trend.id,
                type=kind,
                title=title,
                thesis=f"The {name} trend may create a {kind} opportunity if current cross-source attention persists.",
                score=score,
                confidence=confidence,
                stage="early",
                reasoning={
                    "momentum": round(momentum, 3),
                    "cross_source_confirmation": len(candidate["sources"]),
                    "supporting_evidence": len(evidence_signals),
                    "risks": [
                        "Attention may be event-driven rather than durable",
                        "Current signal set is directional, not proof of market demand",
                    ],
                },
            )
            db.add(opp)
            db.flush()
            for signal in evidence_signals:
                db.add(OpportunityEvidence(opportunity_id=opp.id, signal_id=signal.id))
            created_opportunities += 1

    run.status = "completed"
    run.connector_count = len(live_connectors())
    run.signal_count = created_signals
    run.trend_count = len(topics)
    run.opportunity_count = created_opportunities
    run.details = {"connectors": connector_results, "topics": [x["topic"] for x in topics]}
    run.finished_at = datetime.utcnow()
    db.commit()
    return {
        "run_id": run.id,
        "signals": created_signals,
        "trends": len(topics),
        "opportunities": created_opportunities,
        "topics": [x["topic"] for x in topics],
        "connectors": connector_results,
    }
