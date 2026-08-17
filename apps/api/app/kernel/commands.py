from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.kernel import KernelCommandLog


@dataclass(frozen=True)
class KernelCommand:
    command_type: str
    aggregate_type: str
    aggregate_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    actor_type: str = "human"
    actor_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    causation_id: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CommandContext:
    command_id: str
    command_type: str
    actor_type: str
    actor_id: str | None
    correlation_id: str
    causation_id: str | None


_current_context: ContextVar[CommandContext | None] = ContextVar("yetsee_kernel_command_context", default=None)


def current_command_context() -> CommandContext | None:
    return _current_context.get()


CommandHandler = Callable[[Session, KernelCommand], Any]


class CommandRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command_type: str, handler: CommandHandler) -> None:
        if command_type in self._handlers:
            raise ValueError(f"Command handler already registered: {command_type}")
        self._handlers[command_type] = handler

    def get(self, command_type: str) -> CommandHandler:
        try:
            return self._handlers[command_type]
        except KeyError as exc:
            raise KeyError(f"Unknown kernel command: {command_type}") from exc

    def all(self) -> list[str]:
        return sorted(self._handlers)


registry = CommandRegistry()


AGENT_COMMAND_PERMISSIONS: dict[str, str] = {
    "CreateHypothesis": "write:hypotheses",
    "LinkHypothesisEvidence": "write:hypothesis_evidence",
    "RecalculateHypothesisConfidence": "write:hypothesis_confidence",
    "TransitionInvestigation": "write:investigation_state",
    "RunInvestigationAgent": "execute:agents",
    "RefreshInvestigation": "execute:investigation_refresh",
    "RunReasoner": "execute:reasoners",
}


def _authorize(command: KernelCommand) -> None:
    # Humans/system/API callers are authorized by the existing API boundary for Alpha.
    if command.actor_type != "agent":
        return
    required = AGENT_COMMAND_PERMISSIONS.get(command.command_type)
    if required is None:
        raise PermissionError(f"Agents may not execute command {command.command_type}")
    from app.agent_orchestration.registry import registry as agent_registry

    if not command.actor_id:
        raise PermissionError("Agent actor_id is required")
    manifest = agent_registry.get(command.actor_id).manifest()
    if required not in set(manifest.permissions):
        raise PermissionError(f"Agent {command.actor_id} lacks permission {required}")


def execute_command(db: Session, command: KernelCommand) -> Any:
    # Lazy registration avoids circular imports between the event publisher,
    # investigation runtime, and agent runtime during module initialization.
    if command.command_type not in registry.all():
        from app.kernel import handlers as _handlers  # noqa: F401
    handler = registry.get(command.command_type)
    _authorize(command)
    log = KernelCommandLog(
        command_id=command.id,
        command_type=command.command_type,
        actor_type=command.actor_type,
        actor_id=command.actor_id,
        aggregate_type=command.aggregate_type,
        aggregate_id=command.aggregate_id,
        correlation_id=command.correlation_id,
        causation_id=command.causation_id,
        payload=command.payload,
        status="running",
        requested_at=command.requested_at,
        started_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    token = _current_context.set(
        CommandContext(
            command_id=command.id,
            command_type=command.command_type,
            actor_type=command.actor_type,
            actor_id=command.actor_id,
            correlation_id=command.correlation_id,
            causation_id=command.causation_id,
        )
    )
    try:
        result = handler(db, command)
        log = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == command.id))
        if log is not None:
            log.status = "completed"
            log.finished_at = datetime.now(timezone.utc)
            db.commit()
        return result
    except Exception as exc:
        db.rollback()
        log = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == command.id))
        if log is not None:
            log.status = "failed"
            log.error = str(exc)[:4000]
            log.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise
    finally:
        _current_context.reset(token)
