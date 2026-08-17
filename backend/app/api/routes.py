from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.models import DiscoveryRun, Opportunity, OpportunityEvidence, Signal, Trend
from app.domain.schemas import DiscoveryRunOut, OpportunityInvestigation, OpportunityOut, SignalOut, TrendOut
from app.services.discovery import run_demo
from app.services.live_discovery import run_live

router = APIRouter(prefix="/api/v1")


@router.get("/signals", response_model=list[SignalOut])
def signals(db: Session = Depends(get_db)):
    return db.query(Signal).order_by(Signal.observed_at.desc()).limit(200).all()


@router.get("/trends", response_model=list[TrendOut])
def trends(db: Session = Depends(get_db)):
    return db.query(Trend).order_by(Trend.confidence.desc()).all()


@router.get("/opportunities", response_model=list[OpportunityOut])
def opportunities(db: Session = Depends(get_db)):
    return db.query(Opportunity).order_by(Opportunity.score.desc()).all()


@router.get("/opportunities/{opportunity_id}/investigation", response_model=OpportunityInvestigation)
def opportunity_investigation(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    trend = db.get(Trend, opportunity.trend_id) if opportunity.trend_id else None
    links = db.query(OpportunityEvidence).filter(OpportunityEvidence.opportunity_id == opportunity_id).all()
    evidence = [db.get(Signal, link.signal_id) for link in links]
    evidence = [x for x in evidence if x]
    return {
        "opportunity": opportunity,
        "trend": trend,
        "evidence": evidence,
        "supporting_sources": len({x.source for x in evidence}),
        "risks": opportunity.reasoning.get("risks", []),
        "score_components": {
            "momentum": opportunity.reasoning.get("momentum"),
            "cross_source_confirmation": opportunity.reasoning.get("cross_source_confirmation"),
            "supporting_evidence": opportunity.reasoning.get("supporting_evidence"),
        },
    }


@router.get("/runs", response_model=list[DiscoveryRunOut])
def runs(db: Session = Depends(get_db)):
    return db.query(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(30).all()


@router.post("/discovery/demo")
def discovery_demo(db: Session = Depends(get_db)):
    return run_demo(db)


@router.post("/discovery/live")
async def discovery_live(db: Session = Depends(get_db)):
    return await run_live(db)
