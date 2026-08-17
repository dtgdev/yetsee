# Project Galileo — Investigation Graph

## Scientific question

**How is this investigation structurally connected?**

Galileo introduces a canonical, deterministic graph projection for every Living Investigation. The projection is derived from immutable investigation evidence and does not become a second source of truth.

## Graph projection

`GET /api/v1/investigations/{investigation_id}/graph`

The projection contains four first-class node families:

- investigation
- hypotheses
- observations
- evidence-backed knowledge entities/concepts/sources/metrics

Edges preserve scientific meaning, including `HAS_EVIDENCE`, `HAS_HYPOTHESIS`, `SUPPORTS`, `CONTRADICTS`, `CONTEXT_FOR`, `EVIDENCES_ENTITY`, and canonical knowledge-graph relationships.

## Invariants

1. The graph is derived; canonical observations remain immutable.
2. Every evidence-backed edge retains observation identifiers.
3. Structural metrics are scoped to one investigation.
4. Studio and Graph Reasoner consume the same projection.
5. The graph can be rebuilt deterministically from stored investigation state.

## Galileo G1–G3

- G1: canonical investigation graph engine and API
- G2: interactive Structure lens with search/filter/zoom/selection
- G3: persistent node inspector with relationships, evidence, sources, centrality, and provenance

Later Galileo milestones add richer centrality, community detection, bridge concepts, evidence paths, temporal graph evolution, and replay.
