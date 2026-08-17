from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DB
from app.core.config import settings
from app.models.agent import AgentFinding, AgentRun, AgentTask
from app.models.connector import ConnectorRun, ConnectorState
from app.models.discovery import DetectorRun, DiscoveryCandidate
from app.models.entity import Entity
from app.models.feature import Feature, FeatureRun
from app.models.investigation import Investigation
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink
from app.models.kernel import InvestigationRevision, KernelCommandLog, KernelEvent, WorkflowRun
from app.models.graph import GraphRun
from app.models.relationship import Relationship
from app.models.reasoning import ReasoningResult, ReasoningRun
from app.models.observation import Observation
from app.models.opportunity import Opportunity
from app.models.signal import Signal
from app.models.semantic import SemanticConcept, SemanticRun
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth import AuthError, authenticate_user, register_user
from app.signal_engine.ingestion import run_all_connectors, run_connector
from app.signal_engine.registry import registry
from app.signal_engine.replay import replay_observations
from app.discovery_engine.engine import promote_candidate, run_discovery
from app.discovery_engine.registry import registry as detector_registry
from app.feature_engine.engine import latest_features, recompute_features
from app.feature_engine.registry import registry as feature_registry
from app.knowledge_graph.engine import graph_summary, neighborhood, rebuild_graph
from app.knowledge_graph.investigation import investigation_graph
from app.agent_orchestration.engine import refresh_investigation, run_agent, run_investigation_team
from app.agent_orchestration.registry import registry as agent_registry
from app.semantic_engine.engine import latest_concepts, recompute_semantics, semantic_summary
from app.kernel.events import event_summary, replay_events
from app.kernel import KernelCommand, execute_command, command_registry
from app.kernel.investigations import commit_investigation, history as investigation_history
from app.kernel.plugins import registry as kernel_plugin_registry
from app.investigation_runtime.engine import (
    add_hypothesis,
    attach_hypothesis_evidence,
    confidence_history,
    investigation_diff,
    investigation_workspace,
    recalculate_hypothesis_confidence,
    transition_investigation,
)
from app.workflow_engine.engine import WORKFLOWS, run_workflow
from app.reasoning_runtime.engine import list_results as reasoning_results_list, list_runs as reasoning_runs_list
from app.reasoning_runtime import registry as reasoner_registry


class InvestigationTransitionRequest(BaseModel):
    state: str
    reason: str = Field(min_length=1, max_length=500)


class HypothesisCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class HypothesisEvidenceRequest(BaseModel):
    observation_id: str
    stance: str = "supporting"
    weight: float = Field(default=1.0, ge=0.0)
    rationale: str | None = None


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DB) -> UserRead:
    try:
        return register_user(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DB) -> TokenResponse:
    try:
        _, token = authenticate_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return user


@router.get("/observations")
def observations(
    db: DB,
    limit: int = Query(default=50, ge=1, le=500),
    source: str | None = None,
    topic: str | None = None,
):
    statement = select(Observation)
    if source:
        statement = statement.where(Observation.source == source)
    if topic:
        statement = statement.where(Observation.topic.ilike(f"%{topic}%"))
    statement = statement.order_by(Observation.observed_at.desc()).limit(limit)
    return list(db.scalars(statement))


@router.get("/observations/replay/window")
def replay(
    db: DB,
    start: datetime,
    end: datetime,
    source: str | None = None,
):
    if end < start:
        raise HTTPException(status_code=400, detail="end must be greater than or equal to start")
    return replay_observations(db, start=start, end=end, source=source)


@router.get("/observations/{observation_id}")
def observation(observation_id: str, db: DB):
    item = db.get(Observation, observation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    return item


@router.get("/connectors")
def connectors(db: DB):
    states = {state.connector_id: state for state in db.scalars(select(ConnectorState))}
    result = []
    for connector in registry.all():
        manifest = connector.manifest()
        state = states.get(manifest.id)
        result.append(
            {
                **manifest.__dict__,
                "state": None
                if state is None
                else {
                    "cursor": state.cursor,
                    "last_success_at": state.last_success_at,
                    "last_error_at": state.last_error_at,
                    "consecutive_failures": state.consecutive_failures,
                    "health": "degraded" if state.consecutive_failures else ("healthy" if state.last_success_at else "never_run"),
                },
            }
        )
    return result


@router.get("/connectors/{connector_id}")
def connector(connector_id: str, db: DB):
    try:
        manifest = registry.get(connector_id).manifest()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Connector not found") from exc
    state = db.scalar(select(ConnectorState).where(ConnectorState.connector_id == connector_id))
    runs = list(
        db.scalars(
            select(ConnectorRun)
            .where(ConnectorRun.connector_id == connector_id)
            .order_by(ConnectorRun.started_at.desc())
            .limit(20)
        )
    )
    return {"manifest": manifest.__dict__, "state": state, "recent_runs": runs}


@router.post("/connectors/{connector_id}/run")
def connector_run(connector_id: str, db: DB):
    try:
        registry.get(connector_id)
        run = execute_command(
            db,
            KernelCommand(
                command_type="RunConnector",
                aggregate_type="connector",
                aggregate_id=connector_id,
                payload={"connector_id": connector_id},
                actor_type="human",
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Connector not found") from exc
    if run.status == "failed":
        raise HTTPException(status_code=502, detail={"message": "Connector failed", "run_id": run.id, "error": run.error})
    return run


@router.post("/connectors/run-all")
def connectors_run_all(db: DB, include_demo: bool = False):
    runs = []
    for connector_item in registry.all():
        connector_id = connector_item.manifest().id
        if connector_id == "demo" and not include_demo:
            continue
        runs.append(
            execute_command(
                db,
                KernelCommand(
                    command_type="RunConnector",
                    aggregate_type="connector",
                    aggregate_id=connector_id,
                    payload={"connector_id": connector_id},
                    actor_type="human",
                ),
            )
        )
    return runs


@router.get("/connector-runs")
def connector_runs(db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return list(db.scalars(select(ConnectorRun).order_by(ConnectorRun.started_at.desc()).limit(limit)))


@router.get("/signal-lake/summary")
def signal_lake_summary(db: DB):
    observation_count = db.scalar(select(func.count()).select_from(Observation)) or 0
    connector_count = len(registry.all())
    source_rows = db.execute(
        select(Observation.source, func.count(Observation.id))
        .group_by(Observation.source)
        .order_by(func.count(Observation.id).desc())
    ).all()
    last_run = db.scalar(select(ConnectorRun).order_by(ConnectorRun.started_at.desc()).limit(1))
    return {
        "observations": observation_count,
        "connectors": connector_count,
        "sources": [{"source": source, "count": count} for source, count in source_rows],
        "last_run": last_run,
    }


@router.post("/semantics/recompute")
def semantics_recompute(db: DB, hours: int = Query(default=720, ge=1, le=24 * 365)):
    return recompute_semantics(db, hours=hours)


@router.get("/semantic-concepts")
def semantic_concepts(
    db: DB,
    limit: int = Query(default=200, ge=1, le=1000),
    kind: str | None = None,
    canonical_key: str | None = None,
):
    return latest_concepts(db, limit=limit, kind=kind, canonical_key=canonical_key)


@router.get("/semantic-runs")
def semantic_runs(db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return list(db.scalars(select(SemanticRun).order_by(SemanticRun.started_at.desc()).limit(limit)))


@router.get("/semantic-engine/summary")
def semantic_engine_summary(db: DB):
    return semantic_summary(db)


@router.get("/signals")
def signals(db: DB, limit: int = 50):
    return list(db.scalars(select(Signal).order_by(Signal.created_at.desc()).limit(limit)))


@router.get("/entities")
def entities(db: DB, limit: int = 50):
    return list(db.scalars(select(Entity).order_by(Entity.created_at.desc()).limit(limit)))


@router.get("/investigations")
def investigations(db: DB, limit: int = Query(default=50, ge=1, le=500), status_filter: str | None = None):
    statement = select(Investigation)
    if status_filter:
        statement = statement.where(Investigation.status == status_filter)
    return list(db.scalars(statement.order_by(Investigation.created_at.desc()).limit(limit)))


@router.get("/investigations/by-slug/{slug}")
def investigation_by_slug(slug: str, db: DB):
    item = db.scalar(select(Investigation).where(Investigation.slug == slug))
    if item is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return item


@router.get("/investigations/{investigation_id}")
def investigation_detail(investigation_id: str, db: DB):
    item = db.get(Investigation, investigation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return item


@router.get("/opportunities")
def opportunities(db: DB, limit: int = 50):
    return list(db.scalars(select(Opportunity).order_by(Opportunity.score.desc()).limit(limit)))


@router.get("/feature-extractors")
def feature_extractors():
    return [extractor.manifest().__dict__ for extractor in feature_registry.all()]


@router.post("/features/recompute")
def features_recompute(db: DB, hours: int = Query(default=720, ge=1, le=24 * 365)):
    return recompute_features(db, hours=hours)


@router.get("/features")
def features(
    db: DB,
    limit: int = Query(default=200, ge=1, le=1000),
    subject: str | None = None,
    feature_type: str | None = None,
):
    return latest_features(db, subject=subject, feature_type=feature_type, limit=limit)


@router.get("/features/subject/{subject}")
def features_for_subject(subject: str, db: DB, limit: int = Query(default=200, ge=1, le=1000)):
    return latest_features(db, subject=subject, limit=limit)


@router.get("/feature-runs")
def feature_runs(db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return list(db.scalars(select(FeatureRun).order_by(FeatureRun.started_at.desc()).limit(limit)))


@router.get("/feature-store/summary")
def feature_store_summary(db: DB):
    feature_count = db.scalar(select(func.count()).select_from(Feature)) or 0
    subject_count = db.scalar(select(func.count(func.distinct(Feature.subject)))) or 0
    type_rows = db.execute(
        select(Feature.feature_type, func.count(Feature.id))
        .group_by(Feature.feature_type)
        .order_by(func.count(Feature.id).desc())
    ).all()
    last_run = db.scalar(select(FeatureRun).order_by(FeatureRun.started_at.desc()).limit(1))
    return {
        "features": feature_count,
        "subjects": subject_count,
        "extractors": len(feature_registry.all()),
        "types": [{"feature_type": feature_type, "count": count} for feature_type, count in type_rows],
        "last_run": last_run,
    }


@router.get("/detectors")
def detectors():
    return [detector.manifest().__dict__ for detector in detector_registry.all()]


@router.post("/discovery/run")
def discovery_run(db: DB, hours: int = Query(default=720, ge=1, le=24 * 365)):
    return run_discovery(db, hours=hours)


@router.get("/discovery/candidates")
def discovery_candidates(db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return list(db.scalars(select(DiscoveryCandidate).order_by(DiscoveryCandidate.score.desc()).limit(limit)))


@router.get("/discovery/candidates/{candidate_id}")
def discovery_candidate(candidate_id: str, db: DB):
    candidate = db.get(DiscoveryCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Discovery candidate not found")
    evidence = []
    if candidate.evidence_ids:
        evidence = list(db.scalars(select(Observation).where(Observation.id.in_(candidate.evidence_ids))))
    return {"candidate": candidate, "evidence": evidence}


@router.post("/discovery/candidates/{candidate_id}/promote")
def discovery_candidate_promote(
    candidate_id: str,
    db: DB,
    override: bool = Query(default=False),
    reason: str | None = Query(default=None, max_length=500),
):
    if override and (settings.environment.lower() == "production" or not settings.allow_manual_promotion):
        raise HTTPException(status_code=403, detail="Manual candidate promotion is disabled")
    try:
        return promote_candidate(db, candidate_id, allow_override=override, override_reason=reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Discovery candidate not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/detector-runs")
def detector_runs(db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return list(db.scalars(select(DetectorRun).order_by(DetectorRun.started_at.desc()).limit(limit)))


@router.post("/graph/rebuild")
def graph_rebuild(db: DB, hours: int = Query(default=720, ge=1, le=24 * 365)):
    return rebuild_graph(db, hours=hours)


@router.get("/graph/summary")
def graph_summary_route(db: DB):
    return graph_summary(db)


@router.get("/graph/entities")
def graph_entities(
    db: DB,
    limit: int = Query(default=100, ge=1, le=1000),
    kind: str | None = None,
):
    statement = select(Entity)
    if kind:
        statement = statement.where(Entity.kind == kind)
    return list(db.scalars(statement.order_by(Entity.canonical_name).limit(limit)))


@router.get("/graph/entities/{entity_id}")
def graph_entity(entity_id: str, db: DB):
    item = db.get(Entity, entity_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return item


@router.get("/graph/entities/{entity_id}/neighborhood")
def graph_entity_neighborhood(entity_id: str, db: DB, limit: int = Query(default=100, ge=1, le=500)):
    try:
        return neighborhood(db, entity_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Entity not found") from exc


@router.get("/graph/relationships")
def graph_relationships(
    db: DB,
    limit: int = Query(default=200, ge=1, le=1000),
    kind: str | None = None,
):
    statement = select(Relationship)
    if kind:
        statement = statement.where(Relationship.kind == kind)
    return list(db.scalars(statement.order_by(Relationship.confidence.desc()).limit(limit)))


@router.get("/graph-runs")
def graph_runs(db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return list(db.scalars(select(GraphRun).order_by(GraphRun.started_at.desc()).limit(limit)))


@router.get("/investigations/{investigation_id}/graph")
def investigation_graph_route(investigation_id: str, db: DB):
    try:
        return investigation_graph(db, investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc


@router.get("/agents")
def agents():
    return [agent.manifest().__dict__ for agent in agent_registry.all()]


@router.get("/agent-plane/summary")
def agent_plane_summary(db: DB):
    task_count = db.scalar(select(func.count()).select_from(AgentTask)) or 0
    run_count = db.scalar(select(func.count()).select_from(AgentRun)) or 0
    finding_count = db.scalar(select(func.count()).select_from(AgentFinding)) or 0
    status_rows = db.execute(
        select(AgentTask.status, func.count(AgentTask.id)).group_by(AgentTask.status)
    ).all()
    return {
        "agents": len(agent_registry.all()),
        "tasks": task_count,
        "runs": run_count,
        "findings": finding_count,
        "task_statuses": [{"status": status, "count": count} for status, count in status_rows],
    }


@router.post("/agents/{agent_id}/run")
def agent_run(
    agent_id: str,
    db: DB,
    task_type: str = Query(default="AUDIT"),
    target_type: str | None = None,
    target_id: str | None = None,
):
    try:
        return run_agent(db, agent_id=agent_id, task_type=task_type, target_type=target_type, target_id=target_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent or target not found") from exc


@router.post("/investigations/{investigation_id}/agents/run")
def investigation_agents_run(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return run_investigation_team(db, investigation_id)


@router.post("/investigations/{investigation_id}/agents/evidence/run")
def investigation_evidence_agent_run(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return execute_command(db, KernelCommand(
        command_type="RunInvestigationAgent",
        aggregate_type="investigation",
        aggregate_id=investigation_id,
        payload={"agent_id": "evidence_agent", "task_type": "AUDIT_INVESTIGATION_EVIDENCE"},
    ))


@router.post("/investigations/{investigation_id}/refresh")
def investigation_refresh_route(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        return execute_command(db, KernelCommand(
            command_type="RefreshInvestigation",
            aggregate_type="investigation",
            aggregate_id=investigation_id,
        ))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc


@router.get("/investigations/{investigation_id}/agent-findings")
def investigation_agent_findings(
    investigation_id: str,
    db: DB,
    limit: int = Query(default=200, ge=1, le=1000),
):
    return list(
        db.scalars(
            select(AgentFinding)
            .where(AgentFinding.target_id == investigation_id)
            .order_by(AgentFinding.created_at.desc())
            .limit(limit)
        )
    )


@router.get("/agent-tasks")
def agent_tasks(db: DB, limit: int = Query(default=100, ge=1, le=1000)):
    return list(db.scalars(select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)))


@router.get("/agent-runs")
def agent_runs(db: DB, limit: int = Query(default=100, ge=1, le=1000)):
    return list(db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)))


@router.get("/agent-findings")
def agent_findings(
    db: DB,
    limit: int = Query(default=200, ge=1, le=1000),
    agent_id: str | None = None,
    severity: str | None = None,
):
    statement = select(AgentFinding)
    if agent_id:
        statement = statement.where(AgentFinding.agent_id == agent_id)
    if severity:
        statement = statement.where(AgentFinding.severity == severity)
    return list(db.scalars(statement.order_by(AgentFinding.created_at.desc()).limit(limit)))


# ---------------------------------------------------------------------------
# YetSee OS Alpha kernel/runtime APIs
# ---------------------------------------------------------------------------

@router.get("/kernel/status")
def kernel_status(db: DB):
    return {
        "name": "YetSee OS",
        "api_version": "yetsee.ai/v1alpha1",
        "kernel": {
            "evidence": "immutable",
            "investigations": "versioned",
            "events": "append_only",
            "plugins": "registry",
            "workflows": list(WORKFLOWS),
        },
        "plugin_summary": kernel_plugin_registry.summary(),
        "event_summary": event_summary(db),
    }


@router.get("/kernel/commands")
def kernel_commands(db: DB, limit: int = Query(default=100, ge=1, le=1000), status_filter: str | None = None):
    statement = select(KernelCommandLog)
    if status_filter:
        statement = statement.where(KernelCommandLog.status == status_filter)
    return list(db.scalars(statement.order_by(KernelCommandLog.requested_at.desc()).limit(limit)))


@router.get("/kernel/commands/{command_id}")
def kernel_command(command_id: str, db: DB):
    item = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == command_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Kernel command not found")
    return item


@router.get("/kernel/command-types")
def kernel_command_types():
    from app.kernel import handlers as _handlers  # noqa: F401
    return {"commands": command_registry.all()}


@router.get("/plugins")
def kernel_plugins():
    return kernel_plugin_registry.all()


@router.get("/events")
def kernel_events(db: DB, limit: int = Query(default=100, ge=1, le=1000), event_type: str | None = None):
    statement = select(KernelEvent)
    if event_type:
        statement = statement.where(KernelEvent.event_type == event_type)
    return list(db.scalars(statement.order_by(KernelEvent.occurred_at.desc()).limit(limit)))


@router.get("/events/{aggregate_type}/{aggregate_id}")
def kernel_event_replay(aggregate_type: str, aggregate_id: str, db: DB):
    return replay_events(db, aggregate_type, aggregate_id)


@router.get("/workflows")
def workflows():
    return [{"id": key, "steps": list(value)} for key, value in WORKFLOWS.items()]


@router.post("/workflows/{workflow_id}/run")
def workflow_run(workflow_id: str, db: DB, hours: int = Query(default=720, ge=1, le=24 * 365)):
    try:
        return run_workflow(db, workflow_id, hours=hours)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@router.get("/workflow-runs")
def workflow_runs(db: DB, limit: int = Query(default=100, ge=1, le=1000)):
    return list(db.scalars(select(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(limit)))


@router.post("/investigations/{investigation_id}/commit")
def investigation_commit(investigation_id: str, db: DB, message: str = Query(min_length=1, max_length=500)):
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    revision = commit_investigation(db, investigation, message=message, change_type="manual_commit")
    db.commit()
    db.refresh(revision)
    return revision


@router.get("/investigations/{investigation_id}/history")
def investigation_history_route(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation_history(db, investigation_id)


# ---------------------------------------------------------------------------
# Living Investigation Runtime APIs
# ---------------------------------------------------------------------------

@router.get("/investigations/{investigation_id}/workspace")
def investigation_workspace_route(investigation_id: str, db: DB):
    try:
        return investigation_workspace(db, investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc


@router.post("/investigations/{investigation_id}/transition")
def investigation_transition_route(investigation_id: str, payload: InvestigationTransitionRequest, db: DB):
    try:
        return execute_command(db, KernelCommand(
            command_type="TransitionInvestigation",
            aggregate_type="investigation",
            aggregate_id=investigation_id,
            payload={"state": payload.state, "reason": payload.reason},
        ))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/investigations/{investigation_id}/hypotheses", status_code=status.HTTP_201_CREATED)
def hypothesis_create_route(investigation_id: str, payload: HypothesisCreateRequest, db: DB):
    try:
        return execute_command(db, KernelCommand(
            command_type="CreateHypothesis",
            aggregate_type="investigation",
            aggregate_id=investigation_id,
            payload={"title": payload.title, "description": payload.description, "confidence": payload.confidence},
        ))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc


@router.get("/investigations/{investigation_id}/hypotheses")
def hypotheses_list_route(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return list(db.scalars(
        select(Hypothesis)
        .where(Hypothesis.investigation_id == investigation_id)
        .order_by(Hypothesis.created_at.asc())
    ))


@router.post("/investigations/{investigation_id}/hypotheses/{hypothesis_id}/evidence", status_code=status.HTTP_201_CREATED)
def hypothesis_evidence_route(
    investigation_id: str,
    hypothesis_id: str,
    payload: HypothesisEvidenceRequest,
    db: DB,
):
    try:
        return execute_command(db, KernelCommand(
            command_type="LinkHypothesisEvidence",
            aggregate_type="investigation",
            aggregate_id=investigation_id,
            payload={
                "hypothesis_id": hypothesis_id,
                "observation_id": payload.observation_id,
                "stance": payload.stance,
                "weight": payload.weight,
                "rationale": payload.rationale,
            },
        ))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation, hypothesis, or observation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/investigations/{investigation_id}/hypotheses/{hypothesis_id}/confidence")
def hypothesis_confidence_route(investigation_id: str, hypothesis_id: str, db: DB):
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if hypothesis is None or hypothesis.investigation_id != investigation_id:
        raise HTTPException(status_code=404, detail="Investigation or hypothesis not found")
    links = list(db.scalars(
        select(HypothesisEvidenceLink)
        .where(HypothesisEvidenceLink.hypothesis_id == hypothesis_id)
        .order_by(HypothesisEvidenceLink.created_at.asc())
    ))
    weights = {"supporting": 0.0, "contradicting": 0.0, "neutral": 0.0}
    for link in links:
        weights[link.stance] = weights.get(link.stance, 0.0) + float(link.weight)
    return {
        "hypothesis_id": hypothesis.id,
        "prior_confidence": hypothesis.prior_confidence,
        "confidence": hypothesis.confidence,
        "evidence": weights,
        "evidence_count": len(links),
    }


@router.get("/investigations/{investigation_id}/hypotheses/{hypothesis_id}/confidence/history")
def hypothesis_confidence_history_route(investigation_id: str, hypothesis_id: str, db: DB):
    try:
        return confidence_history(db, investigation_id, hypothesis_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation or hypothesis not found") from exc


@router.post("/investigations/{investigation_id}/hypotheses/{hypothesis_id}/confidence/recalculate")
def hypothesis_confidence_recalculate_route(investigation_id: str, hypothesis_id: str, db: DB):
    try:
        return execute_command(db, KernelCommand(
            command_type="RecalculateHypothesisConfidence",
            aggregate_type="investigation",
            aggregate_id=investigation_id,
            payload={
                "hypothesis_id": hypothesis_id,
                "reason": "Manual confidence recalculation",
                "trigger": "manual",
            },
        ))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation or hypothesis not found") from exc


@router.get("/investigations/{investigation_id}/timeline")
def investigation_timeline_route(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return replay_events(db, "investigation", investigation_id)


@router.get("/investigations/{investigation_id}/diff")
def investigation_diff_route(
    investigation_id: str,
    db: DB,
    from_revision: int = Query(ge=1),
    to_revision: int = Query(ge=1),
):
    try:
        return investigation_diff(db, investigation_id, from_revision, to_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation or revision not found") from exc


# ---------------------------------------------------------------------------
# Scientific Reasoning Runtime APIs
# ---------------------------------------------------------------------------

@router.get("/reasoners")
def reasoners():
    return [reasoner.manifest().__dict__ for reasoner in reasoner_registry.all()]


@router.post("/investigations/{investigation_id}/reasoning/{reasoner_id}/run")
def reasoning_run_route(investigation_id: str, reasoner_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        reasoner_registry.get(reasoner_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Reasoner not found") from exc
    try:
        return execute_command(db, KernelCommand(
            command_type="RunReasoner",
            aggregate_type="investigation",
            aggregate_id=investigation_id,
            payload={"reasoner_id": reasoner_id},
        ))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/investigations/{investigation_id}/reasoning/runs")
def reasoning_runs_route(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return reasoning_runs_list(db, investigation_id)


@router.get("/investigations/{investigation_id}/reasoning/results")
def reasoning_results_route(investigation_id: str, db: DB):
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return reasoning_results_list(db, investigation_id)


@router.get("/reasoning/results/{result_id}")
def reasoning_result_route(result_id: str, db: DB):
    item = db.get(ReasoningResult, result_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Reasoning result not found")
    return item
