from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.analytics import analyze_investigation_graph

from app.models.entity import Entity
from app.models.graph import InvestigationGraphProjection
from app.models.evidence import EvidenceLink
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificPassage, ScientificPublication


def _node_id(kind: str, object_id: str) -> str:
    return f"{kind}:{object_id}"


def _stance_edge(stance: str) -> str:
    return {
        "supporting": "SUPPORTS",
        "contradicting": "CONTRADICTS",
        "neutral": "CONTEXT_FOR",
    }.get(stance, "CONTEXT_FOR")


_SEMANTIC_RELATIONSHIP_FAMILIES: dict[str, str] = {
    "reported_as_resistance_mechanism": "resistance_mechanism",
    "contributes_to": "resistance_mechanism",
    "MECHANISM_CONTRIBUTES_TO": "resistance_mechanism",
}


def _consolidate_semantic_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate-looking scientific assertions in the derived projection.

    Canonical relationship rows are never changed. Consolidation only affects the
    investigation projection and preserves every underlying relationship and its
    provenance in metadata.
    """
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    passthrough: list[dict[str, Any]] = []

    for edge in edges:
        family = _SEMANTIC_RELATIONSHIP_FAMILIES.get(edge["kind"])
        if family is None:
            passthrough.append(edge)
            continue
        grouped[(edge["source"], edge["target"], family)].append(edge)

    consolidated: list[dict[str, Any]] = []
    for (source, target, family), members in grouped.items():
        if len(members) == 1:
            consolidated.append(members[0])
            continue

        kinds = [member["kind"] for member in members]
        if "contributes_to" in kinds:
            display_kind = "contributes_to"
        elif "MECHANISM_CONTRIBUTES_TO" in kinds:
            display_kind = "MECHANISM_CONTRIBUTES_TO"
        else:
            display_kind = kinds[0]

        evidence_ids = sorted({
            evidence_id
            for member in members
            for evidence_id in member.get("evidence_ids", [])
        })
        raw_relationships = [
            {
                "id": member["id"],
                "kind": member["kind"],
                "confidence": member.get("confidence", 1.0),
                "evidence_ids": member.get("evidence_ids", []),
                "metadata": member.get("metadata", {}),
            }
            for member in members
        ]
        consolidated.append(
            {
                "id": "semantic:" + ":".join([family, source, target]),
                "source": source,
                "target": target,
                "kind": display_kind,
                "confidence": max(member.get("confidence", 1.0) for member in members),
                "evidence_ids": evidence_ids,
                "metadata": {
                    "semantic_consolidation": True,
                    "semantic_family": family,
                    "underlying_relationship_ids": [member["id"] for member in members],
                    "underlying_relationship_kinds": kinds,
                    "raw_relationships": raw_relationships,
                    "derived_projection": True,
                },
            }
        )

    return passthrough + consolidated


def _connected_components(node_ids: list[str], edges: list[dict[str, Any]]) -> int:
    if not node_ids:
        return 0
    neighbors: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        neighbors[source].add(target)
        neighbors[target].add(source)
    seen: set[str] = set()
    components = 0
    for node_id in node_ids:
        if node_id in seen:
            continue
        components += 1
        queue = deque([node_id])
        seen.add(node_id)
        while queue:
            current = queue.popleft()
            for other in neighbors[current]:
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
    return components


def investigation_graph(db: Session, investigation_id: str) -> dict[str, Any]:
    """Build a deterministic, evidence-derived graph for one investigation.

    The returned graph is a projection. Canonical observations, hypotheses, and
    knowledge-graph relationships remain unchanged.
    """
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError(investigation_id)

    hypotheses = list(
        db.scalars(
            select(Hypothesis)
            .where(Hypothesis.investigation_id == investigation_id)
            .order_by(Hypothesis.created_at.asc())
        )
    )
    hypothesis_ids = [item.id for item in hypotheses]
    hypothesis_links: list[HypothesisEvidenceLink] = []
    if hypothesis_ids:
        hypothesis_links = list(
            db.scalars(
                select(HypothesisEvidenceLink)
                .where(HypothesisEvidenceLink.hypothesis_id.in_(hypothesis_ids))
                .order_by(HypothesisEvidenceLink.created_at.asc())
            )
        )

    investigation_links = list(
        db.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.investigation_id == investigation_id)
            .order_by(EvidenceLink.created_at.asc())
        )
    )
    observation_ids = {
        link.observation_id for link in investigation_links if link.observation_id
    }
    observation_ids.update(
        link.observation_id for link in hypothesis_links if link.observation_id
    )
    literature_passage_ids = {
        link.scientific_passage_id
        for link in investigation_links
        if link.scientific_passage_id
    }

    literature_passages: list[ScientificPassage] = []
    if literature_passage_ids:
        literature_passages = list(
            db.scalars(
                select(ScientificPassage)
                .where(ScientificPassage.id.in_(literature_passage_ids))
                .order_by(ScientificPassage.id.asc())
            )
        )
    literature_passage_by_id = {item.id: item for item in literature_passages}
    literature_publication_ids = sorted({item.publication_id for item in literature_passages})
    literature_publications: list[ScientificPublication] = []
    if literature_publication_ids:
        literature_publications = list(
            db.scalars(
                select(ScientificPublication)
                .where(ScientificPublication.id.in_(literature_publication_ids))
                .order_by(ScientificPublication.id.asc())
            )
        )
    literature_publication_by_id = {item.id: item for item in literature_publications}

    observations: list[Observation] = []
    if observation_ids:
        observations = list(
            db.scalars(
                select(Observation)
                .where(Observation.id.in_(observation_ids))
                .order_by(Observation.observed_at.asc())
            )
        )
    observation_by_id = {item.id: item for item in observations}

    # Relationship evidence/provenance is stored as JSON, so use a bounded
    # in-memory filter to preserve SQLite/Postgres portability in the reference build.
    # Literature-derived graph relationships are scoped by canonical passage IDs
    # and explicit investigation provenance.
    all_relationships = list(
        db.scalars(select(Relationship).order_by(Relationship.confidence.desc()))
    )
    scoped_evidence_ids = set(observation_ids) | set(literature_passage_ids)
    projection_state = db.get(InvestigationGraphProjection, investigation_id)
    active_relationship_ids = set(
        projection_state.summary_json.get("relationship_ids", [])
    ) if projection_state else None

    def in_scope(item: Relationship) -> bool:
        provenance = item.provenance or {}
        evidence = set(item.evidence_ids or [])
        # Historical provenance alone must not retain detached evidence. Order
        # assertions need BOTH events in scope, rather than either endpoint.
        if evidence:
            if not evidence.intersection(scoped_evidence_ids):
                return False
            if item.kind == "EVENT_PRECEDES" and not evidence.issubset(scoped_evidence_ids):
                return False
        elif investigation_id not in provenance.get("investigation_ids", []):
            return False
        managed = (
            provenance.get("cross_domain_projection")
            or provenance.get("temporal_projection")
            or provenance.get("temporal_order_only")
            or provenance.get("derived_assessment")
            or provenance.get("derived_gap_assessment")
            or provenance.get("method") in {
                "scientific-literature-graph-projection-v1", "explicit-clinical-trial-id",
                "deterministic-scientific-context-v1", "deterministic-intervention-mention-v1",
                "evidence-state-graph-projection-v1",
            }
        )
        return not managed or active_relationship_ids is None or item.id in active_relationship_ids

    relationships: list[Relationship] = [
        item
        for item in all_relationships
        if in_scope(item)
    ]

    entity_ids: set[str] = set()
    for relationship in relationships:
        entity_ids.add(relationship.source_entity_id)
        entity_ids.add(relationship.target_entity_id)
    if projection_state:
        entity_ids.update(projection_state.summary_json.get("node_ids", []))
    entities: list[Entity] = []
    if entity_ids:
        entities = list(db.scalars(select(Entity).where(Entity.id.in_(entity_ids))))
    # Assessment objects belong to an investigation even if their source passage
    # or target entity is shared with another investigation.
    entities = [item for item in entities if (
        item.kind not in {"assessment", "evidence_gap"}
        or (item.attributes or {}).get("investigation_id") in {None, investigation_id}
    )]
    entity_by_id = {item.id: item for item in entities}
    relationships = [item for item in relationships if (
        item.source_entity_id in entity_by_id and item.target_entity_id in entity_by_id
    )]

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    inv_node = _node_id("investigation", investigation.id)
    nodes.append(
        {
            "id": inv_node,
            "domain_id": investigation.id,
            "kind": "investigation",
            "label": investigation.title,
            "description": investigation.summary,
            "confidence": investigation.confidence,
            "evidence_count": len(observations) + len(literature_passages),
            "source_count": len({item.source for item in observations}) + len(literature_publications),
            "metadata": {
                "status": investigation.status,
                "slug": investigation.slug,
            },
        }
    )

    for hypothesis in hypotheses:
        node_id = _node_id("hypothesis", hypothesis.id)
        related_links = [link for link in hypothesis_links if link.hypothesis_id == hypothesis.id]
        nodes.append(
            {
                "id": node_id,
                "domain_id": hypothesis.id,
                "kind": "hypothesis",
                "label": hypothesis.title,
                "description": hypothesis.description,
                "confidence": hypothesis.confidence,
                "evidence_count": len(related_links),
                "source_count": len(
                    {
                        observation_by_id[link.observation_id].source
                        for link in related_links
                        if link.observation_id in observation_by_id
                    }
                ),
                "metadata": {
                    "status": hypothesis.status,
                    "prior_confidence": hypothesis.prior_confidence,
                },
            }
        )
        edges.append(
            {
                "id": f"investigation-hypothesis:{hypothesis.id}",
                "source": inv_node,
                "target": node_id,
                "kind": "HAS_HYPOTHESIS",
                "confidence": 1.0,
                "evidence_ids": [link.observation_id for link in related_links],
                "metadata": {},
            }
        )

    for observation in observations:
        node_id = _node_id("observation", observation.id)
        nodes.append(
            {
                "id": node_id,
                "domain_id": observation.id,
                "kind": "observation",
                "label": f"{observation.source}: {observation.metric}",
                "description": observation.topic,
                "confidence": 1.0,
                "evidence_count": 1,
                "source_count": 1,
                "metadata": {
                    "source": observation.source,
                    "source_ref": observation.source_ref,
                    "metric": observation.metric,
                    "value": observation.value,
                    "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
                    "provenance": (observation.payload or {}).get("provenance", {}),
                },
            }
        )
        edges.append(
            {
                "id": f"investigation-observation:{observation.id}",
                "source": inv_node,
                "target": node_id,
                "kind": "HAS_EVIDENCE",
                "confidence": 1.0,
                "evidence_ids": [observation.id],
                "metadata": {"source": observation.source},
            }
        )

    for link in hypothesis_links:
        if link.observation_id not in observation_by_id:
            continue
        edges.append(
            {
                "id": f"hypothesis-evidence:{link.id}",
                "source": _node_id("observation", link.observation_id),
                "target": _node_id("hypothesis", link.hypothesis_id),
                "kind": _stance_edge(link.stance),
                "confidence": max(0.0, min(1.0, link.weight)),
                "evidence_ids": [link.observation_id],
                "metadata": {
                    "stance": link.stance,
                    "weight": link.weight,
                    "rationale": link.rationale,
                },
            }
        )

    evidence_by_entity: dict[str, set[str]] = defaultdict(set)
    relationship_count_by_entity: dict[str, int] = defaultdict(int)
    for relationship in relationships:
        evidence_by_entity[relationship.source_entity_id].update(relationship.evidence_ids or [])
        evidence_by_entity[relationship.target_entity_id].update(relationship.evidence_ids or [])
        relationship_count_by_entity[relationship.source_entity_id] += 1
        relationship_count_by_entity[relationship.target_entity_id] += 1

    for entity in entities:
        evidence_ids = sorted(evidence_by_entity[entity.id].intersection(scoped_evidence_ids))
        observation_sources = {
            observation_by_id[evidence_id].source
            for evidence_id in evidence_ids
            if evidence_id in observation_by_id
        }
        publication_sources = {
            literature_passage_by_id[evidence_id].publication_id
            for evidence_id in evidence_ids
            if evidence_id in literature_passage_by_id
        }
        source_count = len(observation_sources) + len(publication_sources)
        nodes.append(
            {
                "id": _node_id("entity", entity.id),
                "domain_id": entity.id,
                "kind": entity.kind or "entity",
                "label": entity.canonical_name,
                "description": entity.description,
                "confidence": 1.0,
                "evidence_count": len(evidence_ids),
                "source_count": source_count,
                "metadata": {
                    "canonical_key": entity.canonical_key,
                    "aliases": entity.aliases,
                    "attributes": entity.attributes,
                    "relationship_count": relationship_count_by_entity[entity.id],
                },
            }
        )

        for evidence_id in evidence_ids:
            if evidence_id not in observation_by_id:
                continue
            edges.append(
                {
                    "id": f"observation-entity:{evidence_id}:{entity.id}",
                    "source": _node_id("observation", evidence_id),
                    "target": _node_id("entity", entity.id),
                    "kind": "EVIDENCES_ENTITY",
                    "confidence": 1.0,
                    "evidence_ids": [evidence_id],
                    "metadata": {},
                }
            )

        if entity.kind == "publication":
            publication_id = (entity.attributes or {}).get("publication_id")
            publication_passage_ids = sorted(
                passage.id
                for passage in literature_passages
                if passage.publication_id == publication_id
            )
            if publication_passage_ids:
                edges.append(
                    {
                        "id": f"investigation-literature:{entity.id}",
                        "source": inv_node,
                        "target": _node_id("entity", entity.id),
                        "kind": "HAS_LITERATURE",
                        "confidence": 1.0,
                        "evidence_ids": publication_passage_ids,
                        "metadata": {
                            "publication_id": publication_id,
                            "canonical_evidence_kind": "scientific_passage",
                            "derived_projection": True,
                        },
                    }
                )

    for relationship in relationships:
        relevant_evidence = sorted(set(relationship.evidence_ids or []).intersection(scoped_evidence_ids))
        if not relevant_evidence and investigation_id not in (relationship.provenance or {}).get("investigation_ids", []):
            continue
        edges.append(
            {
                "id": f"relationship:{relationship.id}",
                "source": _node_id("entity", relationship.source_entity_id),
                "target": _node_id("entity", relationship.target_entity_id),
                "kind": relationship.kind,
                "confidence": relationship.confidence,
                "evidence_ids": relevant_evidence,
                "metadata": {
                    "first_seen": relationship.first_seen.isoformat() if relationship.first_seen else None,
                    "last_seen": relationship.last_seen.isoformat() if relationship.last_seen else None,
                    "provenance": relationship.provenance,
                },
            }
        )

    nodes.sort(key=lambda node: node["id"])
    edges = sorted(_consolidate_semantic_edges(edges), key=lambda edge: edge["id"])

    # Degree is deliberately calculated on the investigation projection, not on
    # the global graph. This makes the metric scientifically scoped and replayable.
    degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    max_degree = max(degree.values(), default=1) or 1
    for node in nodes:
        node["degree"] = degree[node["id"]]
        node["degree_centrality"] = round(degree[node["id"]] / max_degree, 6)

    node_ids = [node["id"] for node in nodes]
    components = _connected_components(node_ids, edges)
    possible_edges = len(nodes) * (len(nodes) - 1) / 2
    density = (len(edges) / possible_edges) if possible_edges else 0.0
    sources = sorted({item.source for item in observations})
    literature_source_labels = sorted(
        {
            f"PubMed {publication.pmid}" if publication.pmid else publication.title
            for publication in literature_publications
        }
    )
    all_source_labels = sorted(set([*sources, *literature_source_labels]))

    projection = {
        "investigation": {
            "id": investigation.id,
            "title": investigation.title,
            "status": investigation.status,
        },
        "nodes": nodes,
        "edges": edges,
        "metrics": {
            "nodes": len(nodes),
            "edges": len(edges),
            "entities": len(entities),
            "observations": len(observations),
            "literature_passages": len(literature_passages),
            "literature_publications": len(literature_publications),
            "hypotheses": len(hypotheses),
            "independent_sources": len(all_source_labels),
            "sources": all_source_labels,
            "connected_components": components,
            "density": round(density, 6),
            "relationship_types": dict(
                sorted(
                    {
                        kind: sum(1 for edge in edges if edge["kind"] == kind)
                        for kind in {edge["kind"] for edge in edges}
                    }.items()
                )
            ),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "derived": True,
    }

    projection["analytics"] = analyze_investigation_graph(projection)
    return projection

