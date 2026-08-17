# Knowledge Graph Engine

The Knowledge Graph Engine turns immutable observations and reusable semantic features into an evidence-backed temporal graph.

## Invariant

**Knowledge is canonical; graph inferences remain traceable to evidence.**

The graph does not replace the Signal Lake. Every derived edge stores the observation IDs that support it.

## Pipeline

```text
Signal Lake + Feature Store
        ↓
Canonical entity resolution
        ↓
Typed relationship extraction
        ↓
Evidence-backed temporal edges
        ↓
Graph structure
        ↓
Graph features
        ↓
Discovery models / investigations
```

## Entity resolution

The baseline resolver is deterministic and dependency-light. It normalizes topic labels, supports aliases, and includes a small catalog for known companies, products, technologies and behaviors. It is intentionally replaceable by NER/embedding/entity-linking providers later.

Examples:

- `social running`, `run clubs` → `Running Clubs`
- `NVDA` → `NVIDIA`
- `agentic ai`, `autonomous agents` → `AI Agents`

## Relationship types in v1

- `OBSERVED_ON` — topic → source
- `MEASURED_BY` — topic → metric
- `MENTIONS` — topic → extracted entity
- `SEMANTICALLY_RELATED_TO` — subject → similar subject

Every relationship includes confidence, evidence IDs, first seen, last seen and provenance.

## Graph features

Each rebuild appends versioned graph features to the shared Feature Store:

- degree
- degree centrality
- connected-component community id

The current community implementation is deliberately simple. Louvain, Leiden, label propagation, Node2Vec and other graph methods can be added later without changing the graph schema.

## Discovery integration

`graph_community` is a discovery detector that consumes graph features. It can therefore agree or disagree with velocity, acceleration, novelty and semantic clustering. No graph algorithm owns the truth.

## APIs

```text
POST /api/v1/graph/rebuild?hours=720
GET  /api/v1/graph/summary
GET  /api/v1/graph/entities
GET  /api/v1/graph/entities/{id}
GET  /api/v1/graph/entities/{id}/neighborhood
GET  /api/v1/graph/relationships
GET  /api/v1/graph-runs
```

## Future extensions

- probabilistic entity resolution
- external identifiers (ticker, CIK, LEI, Wikidata, product IDs)
- temporal validity intervals
- directed and weighted community detection
- graph embeddings
- graph change detection
- relationship contradiction handling
- causal/precedence edges
- company/product/supply-chain enrichment
