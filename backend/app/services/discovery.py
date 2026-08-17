from sqlalchemy.orm import Session
from app.domain.models import DiscoveryRun, Signal, Trend, Opportunity, OpportunityEvidence
from datetime import datetime

DEMO_SIGNALS = [
    ("google_trends", "running clubs", "search_growth", 0.52),
    ("reddit", "running clubs", "discussion_velocity", 0.44),
    ("youtube", "running clubs", "creator_growth", 0.36),
    ("news", "running clubs", "coverage_growth", 0.29),
    ("commerce", "running clubs", "product_demand", 0.28),
]


def run_demo(db: Session):
    run = DiscoveryRun(mode="demo", status="running")
    db.add(run)
    db.flush()
    signals = []
    for source, topic, metric, value in DEMO_SIGNALS:
        signal = Signal(source=source, topic=topic, metric=metric, value=value, evidence={"demo": True})
        db.add(signal)
        signals.append(signal)
    trend = db.query(Trend).filter(Trend.name == "Running Clubs").first()
    if not trend:
        trend = Trend(name="Running Clubs")
        db.add(trend)
    trend.stage = "accelerating"
    trend.momentum = 0.78
    trend.confidence = 0.93
    trend.thesis = "Community-led running is expanding from fitness behavior into a social lifestyle category."
    db.flush()

    old_ids = [x[0] for x in db.query(Opportunity.id).filter(Opportunity.trend_id == trend.id).all()]
    if old_ids:
        db.query(OpportunityEvidence).filter(OpportunityEvidence.opportunity_id.in_(old_ids)).delete(synchronize_session=False)
        db.query(Opportunity).filter(Opportunity.id.in_(old_ids)).delete(synchronize_session=False)
        db.flush()

    specs = [
        ("investment", "Public companies exposed to social running", 88.0),
        ("startup", "Running club operating platform", 91.0),
        ("commerce", "Community running hydration kits", 84.0),
    ]
    for kind, title, score in specs:
        opp = Opportunity(
            trend_id=trend.id,
            type=kind,
            title=title,
            thesis=f"{trend.name} creates a {kind} opportunity while the category is still early.",
            score=score,
            confidence=score / 100,
            reasoning={
                "momentum": trend.momentum,
                "cross_source_confirmation": len(DEMO_SIGNALS),
                "supporting_evidence": len(signals),
                "risks": ["Trend may saturate", "Signals may be seasonal"],
            },
        )
        db.add(opp)
        db.flush()
        for signal in signals:
            db.add(OpportunityEvidence(opportunity_id=opp.id, signal_id=signal.id))

    run.status = "completed"
    run.connector_count = len({x[0] for x in DEMO_SIGNALS})
    run.signal_count = len(DEMO_SIGNALS)
    run.trend_count = 1
    run.opportunity_count = len(specs)
    run.details = {"topic": "running clubs"}
    run.finished_at = datetime.utcnow()
    db.commit()
    return {"run_id": run.id, "signals": len(DEMO_SIGNALS), "trend": trend.name, "opportunities": len(specs)}
