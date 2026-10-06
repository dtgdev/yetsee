from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.investigation import investigation_graph
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.scientific_literature import ScientificPassage, ScientificPublication


QUERY_VERSION = "unified-graph-query-v1"
_MAX_PATH_DEPTH = 8


def _node_index(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in graph.get("nodes", [])}


def _resolve_node(graph: dict[str, Any], ref: str) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    exact = [node for node in nodes if node["id"] == ref or node.get("domain_id") == ref]
    if len(exact) == 1:
        return exact[0]

    lowered = ref.strip().lower()
    key_matches = [
        node for node in nodes
        if str(node.get("metadata", {}).get("canonical_key", "")).lower() == lowered
    ]
    if len(key_matches) == 1:
        return key_matches[0]

    label_matches = [node for node in nodes if node.get("label", "").strip().lower() == lowered]
    if len(label_matches) == 1:
        return label_matches[0]
    if len(label_matches) > 1:
        raise ValueError(f"Graph node reference is ambiguous: {ref}")
    raise KeyError(f"Graph node not found: {ref}")


def _adjacency(graph: dict[str, Any], *, directed: bool = False):
    adjacency: dict[str, list[tuple[str, dict[str, Any], str]]] = defaultdict(list)
    for edge in graph.get("edges", []):
        adjacency[edge["source"]].append((edge["target"], edge, "forward"))
        if not directed:
            adjacency[edge["target"]].append((edge["source"], edge, "reverse"))
    for node_id in adjacency:
        adjacency[node_id].sort(key=lambda item: (item[1]["kind"], item[0], item[1]["id"]))
    return adjacency


def _shortest_path(
    graph: dict[str, Any],
    source_id: str,
    target_id: str,
    *,
    directed: bool = False,
    max_depth: int = _MAX_PATH_DEPTH,
) -> list[dict[str, Any]]:
    if source_id == target_id:
        return []
    adjacency = _adjacency(graph, directed=directed)
    queue = deque([(source_id, [])])
    seen = {source_id}

    while queue:
        current, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for neighbor, edge, direction in adjacency.get(current, []):
            if neighbor in seen:
                continue
            step = {"edge": edge, "from": current, "to": neighbor, "direction": direction}
            candidate = [*path, step]
            if neighbor == target_id:
                return candidate
            seen.add(neighbor)
            queue.append((neighbor, candidate))
    return []


def _evidence_details(db: Session, investigation_id: str, evidence_ids: list[str]) -> list[dict[str, Any]]:
    requested = list(dict.fromkeys(evidence_ids))
    if not requested:
        return []

    links = list(
        db.scalars(
            select(EvidenceLink).where(
                EvidenceLink.investigation_id == investigation_id,
            )
        )
    )
    allowed_observation_ids = {link.observation_id for link in links if link.observation_id}
    allowed_passage_ids = {link.scientific_passage_id for link in links if link.scientific_passage_id}

    observation_ids = [item for item in requested if item in allowed_observation_ids]
    passage_ids = [item for item in requested if item in allowed_passage_ids]

    observations = (
        list(db.scalars(select(Observation).where(Observation.id.in_(observation_ids))))
        if observation_ids else []
    )
    passages = (
        list(db.scalars(select(ScientificPassage).where(ScientificPassage.id.in_(passage_ids))))
        if passage_ids else []
    )
    publication_ids = {passage.publication_id for passage in passages}
    publications = (
        list(db.scalars(select(ScientificPublication).where(ScientificPublication.id.in_(publication_ids))))
        if publication_ids else []
    )
    publication_by_id = {publication.id: publication for publication in publications}

    details: list[dict[str, Any]] = []
    for observation in observations:
        details.append({
            "evidence_id": observation.id,
            "kind": "observation",
            "source": observation.source,
            "source_ref": observation.source_ref,
            "topic": observation.topic,
            "metric": observation.metric,
            "value": observation.value,
            "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
        })
    for passage in passages:
        publication = publication_by_id.get(passage.publication_id)
        details.append({
            "evidence_id": passage.id,
            "kind": "scientific_passage",
            "publication_id": passage.publication_id,
            "publication_title": publication.title if publication else None,
            "pmid": publication.pmid if publication else None,
            "doi": publication.doi if publication else None,
            "section": passage.section,
            "locator": passage.locator,
            "content_hash": passage.content_hash,
        })

    order = {evidence_id: index for index, evidence_id in enumerate(requested)}
    details.sort(key=lambda item: order.get(item["evidence_id"], len(order)))
    return details


def _serialize_path(
    db: Session,
    investigation_id: str,
    graph: dict[str, Any],
    path: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = _node_index(graph)
    evidence_ids = sorted({
        evidence_id
        for step in path
        for evidence_id in step["edge"].get("evidence_ids", [])
    })

    return {
        "hop_count": len(path),
        "nodes": [
            {
                "id": nodes[node_id]["id"],
                "domain_id": nodes[node_id].get("domain_id"),
                "kind": nodes[node_id]["kind"],
                "label": nodes[node_id]["label"],
            }
            for node_id in (
                [path[0]["from"], *[step["to"] for step in path]]
                if path else []
            )
            if node_id in nodes
        ],
        "relationships": [
            {
                "id": step["edge"]["id"],
                "kind": step["edge"]["kind"],
                "direction": step["direction"],
                "confidence": step["edge"].get("confidence"),
                "evidence_ids": step["edge"].get("evidence_ids", []),
                "metadata": step["edge"].get("metadata", {}),
            }
            for step in path
        ],
        "evidence_ids": evidence_ids,
        "evidence": _evidence_details(db, investigation_id, evidence_ids),
    }


def _why_paths(
    db: Session,
    investigation_id: str,
    graph: dict[str, Any],
    node: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    candidate_targets = [
        target for target in graph.get("nodes", [])
        if target["kind"] in {"observation", "source", "publication"}
        and target["id"] != node["id"]
    ]
    ranked: list[tuple[int, str, list[dict[str, Any]]]] = []
    for target in candidate_targets:
        path = _shortest_path(graph, node["id"], target["id"], max_depth=_MAX_PATH_DEPTH)
        if path:
            ranked.append((len(path), target["id"], path))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [
        _serialize_path(db, investigation_id, graph, path)
        for _, _, path in ranked[:limit]
    ]


def _before_paths(
    db: Session,
    investigation_id: str,
    graph: dict[str, Any],
    node: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    incoming = [
        edge for edge in graph.get("edges", [])
        if edge["target"] == node["id"] and edge["kind"] == "EVENT_PRECEDES"
    ]
    incoming.sort(key=lambda edge: (
        edge.get("metadata", {}).get("first_seen") or "",
        edge["source"],
    ))
    result = []
    for edge in incoming[:limit]:
        result.append(_serialize_path(
            db,
            investigation_id,
            graph,
            [{"edge": edge, "from": edge["source"], "to": edge["target"], "direction": "forward"}],
        ))
    return result


def _depends_on_paths(
    db: Session,
    investigation_id: str,
    graph: dict[str, Any],
    evidence_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    nodes = _node_index(graph)
    matched_edges = [
        edge for edge in graph.get("edges", [])
        if evidence_id in edge.get("evidence_ids", [])
    ]
    matched_edges.sort(key=lambda edge: (edge["kind"], edge["source"], edge["target"]))
    result = []
    for edge in matched_edges[:limit]:
        result.append({
            "hop_count": 1,
            "nodes": [
                {
                    "id": nodes[edge["source"]]["id"],
                    "domain_id": nodes[edge["source"]].get("domain_id"),
                    "kind": nodes[edge["source"]]["kind"],
                    "label": nodes[edge["source"]]["label"],
                },
                {
                    "id": nodes[edge["target"]]["id"],
                    "domain_id": nodes[edge["target"]].get("domain_id"),
                    "kind": nodes[edge["target"]]["kind"],
                    "label": nodes[edge["target"]]["label"],
                },
            ],
            "relationships": [{
                "id": edge["id"],
                "kind": edge["kind"],
                "direction": "forward",
                "confidence": edge.get("confidence"),
                "evidence_ids": edge.get("evidence_ids", []),
                "metadata": edge.get("metadata", {}),
            }],
            "evidence_ids": [evidence_id],
            "evidence": _evidence_details(db, investigation_id, [evidence_id]),
        })
    return result


def query_investigation_graph(
    db: Session,
    investigation_id: str,
    *,
    query_type: str,
    node_ref: str | None = None,
    target_ref: str | None = None,
    evidence_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    graph = investigation_graph(db, investigation_id)
    query_type = query_type.strip().lower()
    limit = max(1, min(50, limit))

    subject = None
    target = None
    if query_type in {"why", "before", "path"}:
        if not node_ref:
            raise ValueError(f"{query_type} query requires node_ref")
        subject = _resolve_node(graph, node_ref)
    if query_type == "path":
        if not target_ref:
            raise ValueError("path query requires target_ref")
        target = _resolve_node(graph, target_ref)

    if query_type == "why":
        paths = _why_paths(db, investigation_id, graph, subject, limit)
    elif query_type == "before":
        paths = _before_paths(db, investigation_id, graph, subject, limit)
    elif query_type == "depends_on":
        if not evidence_id:
            raise ValueError("depends_on query requires evidence_id")
        paths = _depends_on_paths(db, investigation_id, graph, evidence_id, limit)
    elif query_type == "path":
        path = _shortest_path(graph, subject["id"], target["id"], max_depth=_MAX_PATH_DEPTH)
        paths = [_serialize_path(db, investigation_id, graph, path)] if path else []
    else:
        raise ValueError("query_type must be one of: why, before, depends_on, path")

    return {
        "investigation_id": investigation_id,
        "query_type": query_type,
        "subject": {
            "id": subject["id"],
            "kind": subject["kind"],
            "label": subject["label"],
        } if subject else None,
        "target": {
            "id": target["id"],
            "kind": target["kind"],
            "label": target["label"],
        } if target else None,
        "evidence_id": evidence_id,
        "result_count": len(paths),
        "paths": paths,
        "policy": {
            "investigation_scoped": True,
            "deterministic": True,
            "read_only": True,
            "canonical_evidence_unchanged": True,
            "path_is_not_causality": True,
            "temporal_precedence_is_not_causality": True,
            "derived_assessments_are_not_canonical_evidence": True,
            "query_version": QUERY_VERSION,
        },
    }
