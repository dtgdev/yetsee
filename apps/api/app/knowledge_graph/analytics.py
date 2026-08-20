from __future__ import annotations

from collections import Counter
from typing import Any

import networkx as nx


SYSTEM_KINDS = {
    "investigation",
    "hypothesis",
    "observation",
    "source",
    "metric",
}


def _semantic_node(node: dict[str, Any]) -> bool:
    return str(node.get("kind", "")).lower() not in SYSTEM_KINDS


def _build_graph(graph: dict[str, Any]) -> nx.Graph:
    g = nx.Graph()

    for node in graph["nodes"]:
        g.add_node(
            node["id"],
            label=node.get("label"),
            kind=node.get("kind"),
            evidence_count=node.get("evidence_count", 0),
            source_count=node.get("source_count", 0),
        )

    for edge in graph["edges"]:
        source = edge["source"]
        target = edge["target"]

        weight = max(
            0.000001,
            float(edge.get("confidence", 1.0)),
        )

        if g.has_edge(source, target):
            g[source][target]["weight"] += weight
            g[source][target]["evidence_count"] += len(
                edge.get("evidence_ids", [])
            )
        else:
            g.add_edge(
                source,
                target,
                weight=weight,
                evidence_count=len(edge.get("evidence_ids", [])),
            )

    for source, target, data in g.edges(data=True):
        strength = max(
            0.000001,
            float(data.get("weight", 1.0)),
        )
        data["distance"] = 1.0 / strength

    return g


def _rank(
    values: dict[str, float],
    node_lookup: dict[str, dict[str, Any]],
    *,
    semantic_only: bool = False,
    limit: int = 10,
):
    ranked = []

    for node_id, value in values.items():
        node = node_lookup[node_id]

        if semantic_only and not _semantic_node(node):
            continue

        ranked.append(
            {
                "node_id": node_id,
                "domain_id": node.get("domain_id"),
                "label": node.get("label"),
                "kind": node.get("kind"),
                "score": round(float(value), 6),
                "evidence_count": node.get("evidence_count", 0),
                "source_count": node.get("source_count", 0),
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["score"],
            -item["evidence_count"],
            item["label"],
        )
    )

    return ranked[:limit]


def analyze_investigation_graph(
    graph: dict[str, Any],
) -> dict[str, Any]:

    node_lookup = {
        node["id"]: node
        for node in graph["nodes"]
    }

    g = _build_graph(graph)

    if g.number_of_nodes() == 0:
        return {
            "degree_centrality": {},
            "betweenness_centrality": {},
            "closeness_centrality": {},
            "pagerank": {},
            "communities": [],
            "bridge_nodes": [],
            "density": 0,
        }

    degree = nx.degree_centrality(g)

    betweenness = nx.betweenness_centrality(
        g,
        normalized=True,
        weight="distance",
    )

    closeness = nx.closeness_centrality(
        g,
        distance="distance",
    )

    pagerank = nx.pagerank(
        g,
        weight="weight",
    )

    communities = list(
        nx.community.greedy_modularity_communities(
            g,
            weight="weight",
        )
    )

    articulation = set(nx.articulation_points(g))

    community_lookup = {}

    for index, community in enumerate(communities):
        for node in community:
            community_lookup[node] = index

    bridge_nodes = []

    for node in g.nodes:

        if not _semantic_node(node_lookup[node]):
            continue

        neighboring = {
            community_lookup[n]
            for n in g.neighbors(node)
        }

        if (
            len(neighboring) > 1
            or node in articulation
            or betweenness[node] > 0
        ):
            bridge_nodes.append(
                {
                    "node_id": node,
                    "label": node_lookup[node]["label"],
                    "kind": node_lookup[node]["kind"],
                    "betweenness": round(
                        betweenness[node],
                        6,
                    ),
                    "communities_connected": len(
                        neighboring
                    ),
                    "articulation_point": node in articulation,
                }
            )

    bridge_nodes.sort(
        key=lambda x: (
            -int(x["articulation_point"]),
            -x["communities_connected"],
            -x["betweenness"],
        )
    )

    community_payload = []

    for index, community in enumerate(communities):

        members = [
            node_lookup[n]
            for n in community
        ]

        kinds = Counter(
            member["kind"]
            for member in members
        )

        community_payload.append(
            {
                "id": index,
                "size": len(community),
                "node_ids": sorted(list(community)),
                "kinds": dict(kinds),
            }
        )

    return {
        "degree_centrality": degree,
        "betweenness_centrality": betweenness,
        "closeness_centrality": closeness,
        "pagerank": pagerank,
        "density": nx.density(g),
        "bridge_nodes": bridge_nodes,
        "communities": community_payload,
        "top_semantic_nodes": _rank(
            pagerank,
            node_lookup,
            semantic_only=True,
        ),
        "top_nodes": _rank(
            pagerank,
            node_lookup,
        ),
    }

