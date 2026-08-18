from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.knowledge_graph.analytics import analyze_investigation_graph
from app.knowledge_graph.investigation import investigation_graph


SYSTEM_NODE_KINDS = {"investigation", "hypothesis", "observation"}


def evidence_scoped_investigation_graph(
    db: Session,
    investigation_id: str,
    evidence_ids: list[str],
) -> dict[str, Any]:
    """Return a deterministic evidence-scoped projection with fresh analytics.

    This never mutates the canonical investigation graph. The full canonical
    projection is built first, then relationships are retained only when their
    evidence provenance intersects the requested evidence IDs. Graph metrics and
    analytics are recomputed on the resulting projection.
    """
    canonical = investigation_graph(db, investigation_id)
    requested = {item for item in evidence_ids if item}

    if not requested:
        return canonical

    edges = [
        edge
        for edge in canonical["edges"]
        if requested.intersection(edge.get("evidence_ids", []))
    ]

    node_ids: set[str] = set()
    for edge in edges:
        node_ids.add(edge["source"])
        node_ids.add(edge["target"])

    for node in canonical["nodes"]:
        if node.get("kind") == "investigation":
            node_ids.add(node["id"])
        if node.get("kind") == "observation" and node.get("domain_id") in requested:
            node_ids.add(node["id"])

    nodes = [dict(node) for node in canonical["nodes"] if node["id"] in node_ids]

    degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    max_degree = max(degree.values(), default=1) or 1
    for node in nodes:
        node["degree"] = degree[node["id"]]
        node["degree_centrality"] = round(degree[node["id"]] / max_degree, 6)

    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge["source"]].add(edge["target"])
        adjacency[edge["target"]].add(edge["source"])

    seen: set[str] = set()
    connected_components = 0
    for node in nodes:
        node_id = node["id"]
        if node_id in seen:
            continue
        connected_components += 1
        stack = [node_id]
        seen.add(node_id)
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

    possible_edges = len(nodes) * (len(nodes) - 1) / 2
    density = len(edges) / possible_edges if possible_edges else 0.0

    observation_nodes = [node for node in nodes if node.get("kind") == "observation"]
    sources = sorted(
        {
            str(node.get("metadata", {}).get("source"))
            for node in observation_nodes
            if node.get("metadata", {}).get("source")
        }
    )
    hypothesis_nodes = [node for node in nodes if node.get("kind") == "hypothesis"]
    entity_nodes = [node for node in nodes if node.get("kind") not in SYSTEM_NODE_KINDS]

    relationship_types: dict[str, int] = defaultdict(int)
    for edge in edges:
        relationship_types[edge["kind"]] += 1

    projection = {
        "investigation": canonical["investigation"],
        "nodes": nodes,
        "edges": edges,
        "metrics": {
            "nodes": len(nodes),
            "edges": len(edges),
            "entities": len(entity_nodes),
            "observations": len(observation_nodes),
            "hypotheses": len(hypothesis_nodes),
            "independent_sources": len(sources),
            "sources": sources,
            "connected_components": connected_components,
            "density": round(density, 6),
            "relationship_types": dict(sorted(relationship_types.items())),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "derived": True,
        "scope": {
            "kind": "evidence",
            "evidence_ids": sorted(requested),
            "canonical_generated_at": canonical.get("generated_at"),
        },
    }
    projection["analytics"] = analyze_investigation_graph(projection)
    return projection
