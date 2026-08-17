from __future__ import annotations

from app.knowledge_graph.investigation import investigation_graph
from app.reasoning_runtime.contracts import ReasonerManifest, ReasoningOutput


class GraphReasoner:
    def manifest(self) -> ReasonerManifest:
        return ReasonerManifest(
            id="graph",
            name="Graph Reasoner",
            version="1.1.0",
            scientific_question="What does the structure imply?",
            evidence_types=("investigation_graph", "entities", "relationships", "evidence_links"),
            deterministic=True,
        )

    def execute(self, db, investigation_id: str) -> ReasoningOutput:
        graph = investigation_graph(db, investigation_id)
        metrics = graph["metrics"]
        nodes = graph["nodes"]
        edges = graph["edges"]

        observations = [node for node in nodes if node["kind"] == "observation"]
        entity_nodes = [
            node
            for node in nodes
            if node["kind"] not in {"investigation", "hypothesis", "observation"}
        ]
        evidence_ids = sorted({node["domain_id"] for node in observations})
        sources = metrics["sources"]

        entity_nodes.sort(
            key=lambda item: (
                -float(item.get("degree_centrality", 0.0)),
                -int(item.get("evidence_count", 0)),
                item["label"],
            )
        )

        supporting_factors = [
            {
                "entity": node["label"],
                "entity_kind": node["kind"],
                "relationship": "INVESTIGATION_GRAPH_CENTRALITY",
                "confidence": round(float(node.get("degree_centrality", 0.0)), 4),
                "evidence_count": node.get("evidence_count", 0),
            }
            for node in entity_nodes[:5]
        ]
        if sources:
            supporting_factors.append(
                {
                    "factor": "independent_sources",
                    "value": len(sources),
                    "sources": sources,
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
        entity_factor = min(1.0, len(entity_nodes) / 8.0)
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
        if len(entity_nodes) < 4:
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
        if len(entity_nodes) < 6:
            recommended.append("Expand semantic/entity extraction to strengthen the investigation graph.")

        central_names = [item["label"] for item in entity_nodes[:3]]
        investigation_title = graph["investigation"]["title"]
        conclusion = (
            f"The canonical investigation graph provides {support_level} structural support for the "
            f"{investigation_title} investigation"
            + (
                f", with the most central evidence-backed concepts including {', '.join(central_names)}."
                if central_names
                else "."
            )
        )
        explanation = (
            f"Graph Reasoner v1.1 evaluated the canonical investigation graph containing "
            f"{metrics['nodes']} node(s), {metrics['edges']} edge(s), {len(evidence_ids)} observation(s), "
            f"and {len(sources)} independent source(s). The graph is a deterministic projection derived "
            "from immutable evidence; the reasoner does not mutate evidence or hypothesis confidence."
        )

        return ReasoningOutput(
            conclusion=conclusion,
            confidence=confidence,
            support_level=support_level,
            supporting_factors=supporting_factors,
            contradicting_factors=contradicting_factors,
            assumptions=[
                "The canonical investigation graph faithfully projects stored investigation evidence.",
                "Degree centrality inside the investigation projection is a useful first-order structural signal.",
                "Source diversity is a useful proxy for structural robustness.",
            ],
            limitations=limitations,
            recommended_evidence=recommended,
            evidence_ids=evidence_ids,
            metrics={
                **metrics,
                "supporting_weight": round(support, 4),
                "contradicting_weight": round(contradict, 4),
                "top_central_nodes": [
                    {
                        "label": node["label"],
                        "kind": node["kind"],
                        "degree": node["degree"],
                        "degree_centrality": node["degree_centrality"],
                    }
                    for node in entity_nodes[:5]
                ],
            },
            explanation=explanation,
        )
