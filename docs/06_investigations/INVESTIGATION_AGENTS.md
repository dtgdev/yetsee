# Investigation Agents Alpha

Investigation Agents are audited specialists that operate above canonical evidence. They may read observations, investigation evidence, hypotheses, graph state, and prior findings, but they do not rewrite raw observations.

## Evidence Agent

The first runtime-native agent is `evidence_agent`.

It checks:

- independent source count,
- repeated source/source-reference/metric patterns,
- missing source families,
- whether active hypotheses have explicit contradicting evidence.

Repeated observations remain valid history, but the agent explicitly distinguishes storage volume from independent confirmation.

## Run the Evidence Agent

```bash
curl -X POST \
  http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/agents/evidence/run
```

Or run a complete deterministic investigation refresh:

```bash
curl -X POST \
  http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/refresh
```

Refresh performs two steps:

1. Run the Evidence Agent and append audited findings.
2. Recalculate each hypothesis from its already-linked directional evidence.

The agent does not automatically promote suggested sources into evidence and does not invent observations.

## Events

Agent activity is visible in the investigation timeline through:

- `AgentRunStarted`
- `AgentFindingCreated`
- `AgentRunCompleted`
- `HypothesisRecalculated` / `HypothesisConfidenceChanged`
- `InvestigationRefreshed`

This preserves the invariant that agent behavior is inspectable and replayable.
