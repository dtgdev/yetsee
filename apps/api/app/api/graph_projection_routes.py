from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DB
from app.knowledge_graph.projection import evidence_scoped_investigation_graph


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
