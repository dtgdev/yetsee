from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DB
from app.knowledge_graph.projection import evidence_scoped_investigation_graph
from app.knowledge_graph.cross_domain_projection import project_cross_domain_observation_graph
from app.knowledge_graph.temporal_events import project_temporal_events
from app.knowledge_graph.evidence_state_projection import project_evidence_state_graph
from app.knowledge_graph.query import query_investigation_graph


router = APIRouter()


class EvidenceGraphProjectionRequest(BaseModel):
    evidence_ids: list[str] = Field(default_factory=list, max_length=1000)


@router.post("/investigations/{investigation_id}/graph/project")
def project_investigation_graph(
    investigation_id: str,
    payload: EvidenceGraphProjectionRequest,
    db: DB,
):
    try:
        return evidence_scoped_investigation_graph(
            db,
            investigation_id,
            payload.evidence_ids,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc


@router.post("/investigations/{investigation_id}/graph/project-cross-domain")
def project_cross_domain_graph(
    investigation_id: str,
    db: DB,
):
    try:
        return project_cross_domain_observation_graph(db, investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/investigations/{investigation_id}/graph/project-temporal")
def project_temporal_graph(
    investigation_id: str,
    db: DB,
):
    try:
        return project_temporal_events(db, investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/investigations/{investigation_id}/graph/project-evidence-state")
def project_evidence_state_context(
    investigation_id: str,
    db: DB,
):
    try:
        return project_evidence_state_graph(db, investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class GraphQueryRequest(BaseModel):
    query_type: str
    node_ref: str | None = None
    target_ref: str | None = None
    evidence_id: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/investigations/{investigation_id}/graph/query")
def query_graph(
    investigation_id: str,
    payload: GraphQueryRequest,
    db: DB,
):
    try:
        return query_investigation_graph(
            db,
            investigation_id,
            query_type=payload.query_type,
            node_ref=payload.node_ref,
            target_ref=payload.target_ref,
            evidence_id=payload.evidence_id,
            limit=payload.limit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
