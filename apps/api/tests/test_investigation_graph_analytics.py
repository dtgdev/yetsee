from app.knowledge_graph.analytics import analyze_investigation_graph


def node(node_id: str, label: str, kind: str = "concept") -> dict:
    return {
        "id": node_id,
        "domain_id": node_id,
        "kind": kind,
        "label": label,
        "evidence_count": 1,
        "source_count": 1,
    }


def edge(
    edge_id: str,
    source: str,
    target: str,
    confidence: float = 1.0,
) -> dict:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "kind": "RELATES_TO",
        "confidence": confidence,
        "evidence_ids": [edge_id],
        "metadata": {},
    }


def test_graph_analytics_compute_standard_centrality_and_are_deterministic():
    graph = {
        "nodes": [
            node("a", "A"),
            node("b", "B"),
            node("c", "C"),
        ],
        "edges": [
            edge("ab", "a", "b"),
            edge("bc", "b", "c"),
        ],
    }

    first = analyze_investigation_graph(graph)
    second = analyze_investigation_graph(graph)

    assert first == second

    # Standard NetworkX degree centrality:
    # degree / (number_of_nodes - 1)
    assert first["degree_centrality"]["a"] == 0.5
    assert first["degree_centrality"]["b"] == 1.0
    assert first["degree_centrality"]["c"] == 0.5

    assert first["betweenness_centrality"]["b"] == 1.0
    assert first["closeness_centrality"]["b"] > first["closeness_centrality"]["a"]
    assert first["pagerank"]["b"] > first["pagerank"]["a"]

    assert first["density"] > 0
    assert first["top_semantic_nodes"][0]["label"] == "B"


def test_high_confidence_edges_are_shorter_structural_paths():
    graph = {
        "nodes": [
            node("a", "A"),
            node("b", "B"),
            node("c", "C"),
        ],
        "edges": [
            edge("ab", "a", "b", confidence=1.0),
            edge("bc", "b", "c", confidence=1.0),

            # Direct A -> C exists, but it is weak.
            # Its inverse-confidence distance is 10, while
            # A -> B -> C has total distance 2.
            edge("ac", "a", "c", confidence=0.1),
        ],
    }

    analytics = analyze_investigation_graph(graph)

    # If confidence were incorrectly treated as distance,
    # the weak direct A-C edge would look artificially short
    # and B would not sit on the preferred A-C path.
    assert analytics["betweenness_centrality"]["b"] > 0


def test_graph_analytics_detect_structural_communities_and_bridges():
    graph = {
        "nodes": [
            node("a", "Fitness"),
            node("b", "Running"),
            node("c", "Community"),
            node("d", "Lifestyle"),
            node("e", "Events"),
            node("f", "Commerce"),
        ],
        "edges": [
            # Left cluster
            edge("ab", "a", "b"),
            edge("ac", "a", "c"),
            edge("bc", "b", "c"),

            # Right cluster
            edge("de", "d", "e"),
            edge("df", "d", "f"),
            edge("ef", "e", "f"),

            # Structural bridge
            edge("cd", "c", "d"),
        ],
    }

    analytics = analyze_investigation_graph(graph)

    assert len(analytics["communities"]) >= 2

    bridge_labels = {
        item["label"]
        for item in analytics["bridge_nodes"]
    }

    assert "Community" in bridge_labels
    assert "Lifestyle" in bridge_labels

    articulation_labels = {
        item["label"]
        for item in analytics["bridge_nodes"]
        if item["articulation_point"]
    }

    assert "Community" in articulation_labels
    assert "Lifestyle" in articulation_labels


def test_system_and_metric_nodes_are_not_ranked_as_semantic_concepts():
    graph = {
        "nodes": [
            node("concept", "Community", "concept"),
            node("source", "Google Trends", "source"),
            node("metric", "Search Interest", "metric"),
            node("observation", "Observation", "observation"),
        ],
        "edges": [
            edge("1", "source", "metric"),
            edge("2", "metric", "observation"),
            edge("3", "observation", "concept"),
        ],
    }

    analytics = analyze_investigation_graph(graph)

    semantic_labels = [
        item["label"]
        for item in analytics["top_semantic_nodes"]
    ]

    assert semantic_labels == ["Community"]
