# Agent Orchestration Layer

YetSee agents coordinate work above deterministic engines. They are not a replacement for Signal Lake, Feature Engine, Discovery Engine, or the Knowledge Graph.

## Architectural rule

**Evidence is immutable. Engines compute. Agents coordinate. Reasoners interpret. Humans decide.**

Agents operate through typed tasks and write only audited findings/results. The orchestration engine refuses agents that request canonical-data mutation permissions such as `write:observations`, `delete:evidence`, or `silent:entity_merge`.

## Initial roles

- `signal_steward` — connector and ingestion quality
- `entity_curator` — suspicious aliases/entities and merge proposals
- `discovery_analyst` — candidate review and promotion recommendations
- `evidence_critic` — counter-evidence and evidence-quality challenge
- `graph_analyst` — graph-neighborhood review
- `opportunity_analyst` — possible action paths, explicitly not recommendations
- `quality_agent` — traceability audit
- `investigation_agent` — synthesizes specialist findings into an investigation state recommendation

## Typed task contract

Tasks persist:

- agent role/version
- task type
- target type/id
- requested-by identity
- explicit constraints
- input/output JSON
- start/finish timestamps
- permissions used
- errors

Findings persist independently and may carry exact evidence IDs.

## Investigation team

`POST /api/v1/investigations/{id}/agents/run` executes a deterministic initial team sequence:

1. Evidence Critic
2. Graph Analyst
3. Opportunity Analyst
4. Quality Agent
5. Investigation Agent synthesis

This sequence is intentionally explicit rather than emergent free-form agent chat. Later versions can add planner agents while preserving the same typed task ledger.
