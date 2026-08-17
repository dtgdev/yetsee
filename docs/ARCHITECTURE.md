# YetSee Architecture — Signal Lake

## Permanent invariant

**Evidence is canonical. Detection and reasoning are replaceable.**

Observations represent what a source reported at a point in time. They do not encode whether something is a trend or opportunity.

## Pipeline

```text
Sources
  ↓
Connector SDK
  ↓
RawItem
  ↓
Normalization
  ↓
Validation
  ↓
Canonical Observation + SHA-256 checksum
  ↓
Deduplication
  ↓
PostgreSQL Signal Lake
  ├── observation history
  ├── provenance
  ├── connector run audit
  └── connector cursor/state
        ↓
      Replay
        ↓
Future Discovery Detectors
```

## Connector contract

Every connector implements four operations:

1. `manifest()` — identity, version, schedule and capabilities.
2. `fetch(cursor)` — acquire raw source records.
3. `normalize(raw)` — map raw source data to `ObservationInput`.
4. `validate(observation)` — source-aware quality rules.

Connectors must not create Signals, Investigations, or Opportunities.

## Idempotency

The Signal Lake computes a deterministic SHA-256 checksum from canonical observation fields. A unique database constraint on `content_hash` prevents duplicate insertion.

## Provenance

Stored observation payloads include the producing connector ID, connector version and connector-run ID. Later milestones can normalize provenance into dedicated tables without changing observation identity.

## Replay

Detectors should be functions of an observation window plus detector configuration. Historical windows are queryable through the replay API, allowing future algorithms to be benchmarked against exactly the evidence YetSee possessed at that time.

## Scale path

v0 storage is PostgreSQL. The connector and observation contracts intentionally do not depend on PostgreSQL. High-volume history can later move to ClickHouse/object storage/lakehouse while Postgres retains metadata and operational state.

## Agent Plane

YetSee separates coordination from computation and evidence:

```text
Agent Plane
  Investigation Agent | Evidence Critic | Graph Analyst | Entity Curator | ...
                 |
                 v
Intelligence Plane
  Feature Engine | Discovery Engine | Knowledge Graph | future Reasoners
                 |
                 v
Evidence Plane
  immutable Observations | provenance | replay
```

Agents are versioned role implementations. They receive typed tasks, have explicit capability/permission manifests, emit audited results/findings, and cannot mutate canonical observations or delete evidence. Free-form agent-to-agent conversation is not a core protocol; typed task contracts are.
