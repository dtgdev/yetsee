from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import DB
from app.kernel import KernelCommand, execute_command
from app.mission_runtime.engine import get_mission, list_missions
from app.models.investigation import Investigation


router = APIRouter()


class MissionStepRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    task_type: str = Field(min_length=1, max_length=100)
    inputs: dict[str, Any] = Field(default_factory=dict)


class MissionCreateRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    plan: list[MissionStepRequest] | None = None


@router.post("/investigations/{investigation_id}/missions")
def create_investigation_mission(
    investigation_id: str,
    request: MissionCreateRequest,
    db: DB,
):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        mission = execute_command(
            db,
            KernelCommand(
                command_type="CreateInvestigationMission",
                aggregate_type="investigation",
                aggregate_id=investigation_id,
                payload={
                    "objective": request.objective,
                    "metadata": request.metadata,
                    "plan": [item.model_dump() for item in request.plan] if request.plan else None,
                },
                actor_type="human",
                actor_id="api",
            ),
        )
        db.refresh(mission)
        return mission
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/investigations/{investigation_id}/missions")
def investigation_missions(
    investigation_id: str,
    db: DB,
    limit: int = Query(default=50, ge=1, le=500),
):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return list_missions(db, investigation_id, limit=limit)


@router.get("/missions/{mission_id}")
def mission_detail(mission_id: str, db: DB):
    try:
        return get_mission(db, mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Mission not found") from exc


@router.post("/missions/{mission_id}/run")
def run_investigation_mission(mission_id: str, db: DB):
    try:
        execute_command(
            db,
            KernelCommand(
                command_type="RunInvestigationMission",
                aggregate_type="mission",
                aggregate_id=mission_id,
                payload={"mission_id": mission_id},
                actor_type="human",
                actor_id="api",
            ),
        )
        return get_mission(db, mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Mission not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
