from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source: str
    topic: str
    metric: str
    value: float
    observed_at: datetime
    evidence: dict


class TrendOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    stage: str
    momentum: float
    confidence: float
    thesis: str


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    trend_id: str | None
    type: str
    title: str
    thesis: str
    score: float
    confidence: float
    stage: str
    reasoning: dict


class DiscoveryRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    mode: str
    status: str
    connector_count: int
    signal_count: int
    trend_count: int
    opportunity_count: int
    details: dict
    started_at: datetime
    finished_at: datetime | None


class OpportunityInvestigation(BaseModel):
    opportunity: OpportunityOut
    trend: TrendOut | None
    evidence: list[SignalOut]
    supporting_sources: int
    risks: list[str]
    score_components: dict
