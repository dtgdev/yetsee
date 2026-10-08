# 6.14 — Guided Hypothesis Setup

## Researcher flow

In the Evidence lens, record a testable claim and its initial confidence. Choose an observation already present in the investigation, classify it as supporting, contradicting, or context only, and record why. The existing Kernel commands create the hypothesis and link the observation; the confidence engine recalculates from the fixed prior and records events and revisions. The Overview and Reasoning lenses link directly to this flow when a hypothesis is missing.

## Boundaries

- No claim is generated or accepted automatically. The researcher writes and submits the claim and rationale.
- The UI offers only observations from the investigation workspace and prevents a second link of the same observation to the selected hypothesis. Its link weight is the existing default of 1. Existing links and changed confidence are visible after refresh.
- Scientific passages remain canonical investigation evidence and are displayed elsewhere in Evidence. The current `HypothesisEvidenceLink` model accepts observation IDs only. This increment does not count passages in hypothesis confidence or imply that literature was attributed to a hypothesis. A later schema and calculation design must handle passage independence before that extension.
- Structural support from Graph Reasoner remains separate from hypothesis confidence. The initial confidence is an explicit researcher input rather than a graph score.

## Verification

Production web build and TypeScript validation. Backend confidence engine tests require a Python environment with pytest and SQLAlchemy; they could not run in this workspace. Live validation should create one hypothesis, classify one supporting and one contradicting observation, confirm the recorded rationale and confidence history, and refresh the Evidence, Overview, and Reasoning lenses.
