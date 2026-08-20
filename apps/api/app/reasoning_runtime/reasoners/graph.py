from __future__ import annotations

from app.knowledge_graph.investigation import investigation_graph
from app.reasoning_runtime.contracts import ReasonerManifest, ReasoningOutput


class GraphReasoner:
    def manifest(self) -> ReasonerManifest:
        return ReasonerManifest(
            id="graph",
            name="Graph Reasoner",
            version="1.2.0",
            scientific_question="What does the structure imply?",
            evidence_types=("investigation_graph", "entities", "relationships", "evidence_links", "graph_analytics"),
            deterministic=True,
        )

    def execute(self, db, investigation_id: str) -> ReasoningOutput:
        graph = investigation_graph(db, investigation_id)
        metrics = graph["metrics"]
        analytics = graph.get("analytics", {})
        nodes = graph["nodes"]
        edges = graph["edges"]

        observations = [node for node in nodes if node["kind"] == "observation"]
        semantic_nodes = [
            node
            for node in nodes
            if str(node.get("kind", "")).lower()
            not in {
                "investigation",
                "hypothesis",
                "observation",
                "source",
                "metric",
            }
        ]
        evidence_ids = sorted({node["domain_id"] for node in observations})
        sources = metrics["sources"]

        semantic_central_nodes = analytics.get("top_semantic_nodes", [])
        bridge_nodes = analytics.get("bridge_nodes", [])
        communities = analytics.get("communities", [])

        supporting_factors = [
            {
                "entity": item["label"],
                "entity_kind": item["kind"],
                "relationship": "INVESTIGATION_GRAPH_PAGERANK",
                "confidence": round(float(item.get("score", 0.0)), 6),
                "evidence_count": int(item.get("evidence_count", 0) or 0),
            }
            for item in semantic_central_nodes[:5]
        ]
        if sources:
            supporting_factors.append(
                {
                    "factor": "independent_sources",
                    "value": len(sources),
                    "sources": sources,
                }
            )

        for bridge in bridge_nodes[:3]:
            supporting_factors.append(
                {
                    "factor": "bridge_concept",
                    "entity": bridge.get("label"),
                    "entity_kind": bridge.get("kind"),
                    "betweenness": round(float(bridge.get("betweenness", 0.0)), 6),
                    "communities_connected": int(
                        bridge.get("communities_connected", 0) or 0
                    ),
                    "articulation_point": bool(
                        bridge.get("articulation_point", False)
                    ),
                }
            )

        support = sum(float(edge["confidence"]) for edge in edges if edge["kind"] == "SUPPORTS")
        contradict = sum(float(edge["confidence"]) for edge in edges if edge["kind"] == "CONTRADICTS")
        contradicting_factors = []
        if contradict:
            contradicting_factors.append(
                {"factor": "contradicting_evidence_weight", "value": round(contradict, 4)}
            )

        source_factor = min(1.0, len(sources) / 3.0)
        entity_factor = min(1.0, len(semantic_nodes) / 8.0)
        evidence_factor = min(1.0, len(evidence_ids) / 8.0)
        connectivity_factor = 1.0 if metrics["connected_components"] <= 1 else max(
            0.25, 1.0 / metrics["connected_components"]
        )
        confidence = round(
            min(
                0.95,
                0.25
                + 0.25 * source_factor
                + 0.20 * entity_factor
                + 0.20 * evidence_factor
                + 0.10 * connectivity_factor,
            ),
            6,
        )
        if contradict > support and contradict > 0:
            confidence = round(max(0.05, confidence - 0.15), 6)

        support_level = "strong" if confidence >= 0.75 else "moderate" if confidence >= 0.55 else "weak"
        limitations = []
        if len(sources) < 3:
            limitations.append(
                f"Only {len(sources)} independent source(s) are currently linked to the investigation."
            )
        if len(semantic_nodes) < 4:
            limitations.append(
                "The canonical investigation graph still has limited semantic/entity breadth."
            )
        if contradict == 0:
            limitations.append("No explicit counter-evidence is linked to the current hypothesis set.")
        if metrics["connected_components"] > 1:
            limitations.append(
                f"The investigation graph contains {metrics['connected_components']} disconnected components."
            )

        recommended = []
        if len(sources) < 3:
            recommended.append("Collect at least one additional independent source family.")
        if contradict == 0:
            recommended.append("Actively collect evidence that could falsify the leading hypothesis.")
        if len(semantic_nodes) < 6:
            recommended.append("Expand semantic/entity extraction to strengthen the investigation graph.")

        central_names = [
            item["label"]
            for item in semantic_central_nodes[:3]
            if item.get("label")
        ]
        bridge_names = [
            item["label"]
            for item in bridge_nodes[:2]
            if item.get("label")
        ]
        investigation_title = graph["investigation"]["title"]
        conclusion = (
            f"The canonical investigation graph provides {support_level} structural support for the "
            f"{investigation_title} investigation"
        )
        if central_names:
            conclusion += (
                f". The most influential semantic concepts are {', '.join(central_names)}"
            )
        if bridge_names:
            conclusion += (
                f", with {', '.join(bridge_names)} acting as important structural bridge concepts"
            )
        conclusion += "."
        explanation = (
            f"Graph Reasoner v1.2 evaluated the canonical investigation graph containing "
            f"{metrics['nodes']} node(s), {metrics['edges']} edge(s), "
            f"{len(evidence_ids)} observation(s), {len(sources)} independent source(s), "
            f"and {len(communities)} structural community or communities. "
            "The reasoner uses graph-theoretic analytics including PageRank, degree centrality, "
            "betweenness, closeness, community detection, and bridge analysis. "
            "The graph remains a deterministic projection derived from immutable evidence; "
            "the reasoner does not mutate evidence or hypothesis confidence."
        )

        return ReasoningOutput(
            conclusion=conclusion,
            confidence=confidence,
            support_level=support_level,
            supporting_factors=supporting_factors,
            contradicting_factors=contradicting_factors,
            assumptions=[
                "The canonical investigation graph faithfully projects stored investigation evidence.",
                "Graph-theoretic centrality is a structural signal and does not by itself establish causality.",
                "Source diversity is a useful proxy for structural robustness.",
                "Detected graph communities describe structural neighborhoods rather than verified scientific categories.",
            ],
            limitations=limitations,
            recommended_evidence=recommended,
            evidence_ids=evidence_ids,
            metrics={
                **metrics,
                "supporting_weight": round(support, 4),
                "contradicting_weight": round(contradict, 4),
                "communities": len(communities),
                "bridge_nodes": bridge_nodes[:5],
                "top_semantic_nodes": semantic_central_nodes[:5],
                "graph_density": analytics.get("density", 0.0),
            },
            explanation=explanation,
        )
