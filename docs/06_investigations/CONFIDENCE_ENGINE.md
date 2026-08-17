# Confidence Engine

Status: Alpha (`0010_confidence_engine`)

The Confidence Engine makes hypothesis confidence versioned, directional, deterministic, and explainable.

## Invariant

A hypothesis keeps its original `prior_confidence`. Recalculation never compounds from the latest confidence value. The same prior plus the same evidence links therefore produces the same posterior.

## Evidence directions

- `supporting`: increases the posterior according to its weight.
- `contradicting`: decreases the posterior according to its weight.
- `neutral`: is preserved for coverage/audit but does not move the posterior.

The Alpha calculator uses a weighted Beta-style update with a prior strength of 4. This is intentionally simple and replaceable by future Bayesian reasoners without changing the evidence/history contract.

## Events

Linking evidence and recalculating confidence emits:

- `EvidenceLinked`
- `HypothesisConfidenceChanged` or `HypothesisRecalculated`
- `InvestigationCommitted`

Every confidence calculation writes `hypothesis_confidence_history` with old/new values, evidence weights, trigger, reason, and optional observation ID.

## APIs

```text
POST /api/v1/investigations/{investigation_id}/hypotheses/{hypothesis_id}/evidence
GET  /api/v1/investigations/{investigation_id}/hypotheses/{hypothesis_id}/confidence
GET  /api/v1/investigations/{investigation_id}/hypotheses/{hypothesis_id}/confidence/history
POST /api/v1/investigations/{investigation_id}/hypotheses/{hypothesis_id}/confidence/recalculate
```

Investigation revisions now snapshot first-class hypotheses and directional hypothesis evidence, so revision diffs can show belief changes rather than only top-level investigation fields.
