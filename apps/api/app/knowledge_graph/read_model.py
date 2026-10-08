from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from sqlalchemy.orm import Session

from app.knowledge_graph.investigation import investigation_graph
from app.knowledge_graph.auto_projection import projection_input_fingerprint
from app.models.graph import InvestigationGraphProjection


READ_MODEL_VERSION = "unified-graph-read-model-v1"


def read_investigation_graph(db: Session, investigation_id: str) -> dict[str, Any]:
    """Shared read-only graph contract for display, filtering and traversal.

    Preparation is an explicit write command. Readers never run projectors or
    commit a transaction, and remain useful when a preparation command fails.
    """
    graph = investigation_graph(db, investigation_id)
    content = {key: graph[key] for key in ["investigation", "nodes", "edges", "metrics"]}
    graph["read_model"] = {
        "version": READ_MODEL_VERSION,
        "graph_id": sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest(),
        "investigation_id": investigation_id,
        "read_only": True,
        "canonical_evidence_unchanged": True,
    }
    state = db.get(InvestigationGraphProjection, investigation_id)
    graph["auto_projection"] = {
        "status": (
            "current" if state.input_fingerprint == projection_input_fingerprint(db, investigation_id)
            else "stale"
        ) if state else "not_prepared",
        "projection_version": state.projection_version if state else None,
        "input_fingerprint": state.input_fingerprint if state else None,
        "prepared_at": state.updated_at.isoformat() if state else None,
    }
    return graph
