# Discovery Engine

The Discovery Engine consumes immutable Signal Lake observations and emits **candidate investigations**. It does not rewrite source evidence and it does not declare an opportunity to be true.

## Invariant

> Algorithms propose. Evidence persists. Investigations remain inspectable.

## Detector contract

Every detector exposes a manifest and a `detect(observations)` operation. Detector output contains a subject, kind, strength, confidence, explanation, evidence IDs and attributes.

The first baseline detectors are intentionally dependency-light:

- **Velocity** — looks for increased observation rate.
- **Acceleration** — looks for increasing signal intensity.
- **Novelty** — rewards fresh topics with little accumulated history.
- **Semantic cluster** — a deterministic token/Jaccard baseline that groups related topic labels.

The semantic detector is an interface-compatible baseline, not the final semantic stack. Future implementations can replace it with embeddings, HDBSCAN, BERTopic or other clustering methods while preserving the contract.

## Synthesis

Independent detections are grouped by canonical subject. The synthesizer records detector-level scores, exact evidence IDs, detector agreement, ensemble score and confidence. The current candidate view is recomputable; source observations remain immutable.

A candidate can be promoted into an `Investigation`. Promotion copies the evidence references into `EvidenceLink` rows so the hypothesis remains traceable to the observations that caused it to surface.

## API

- `GET /api/v1/detectors`
- `POST /api/v1/discovery/run?hours=720`
- `GET /api/v1/discovery/candidates`
- `GET /api/v1/discovery/candidates/{id}`
- `POST /api/v1/discovery/candidates/{id}/promote`
- `GET /api/v1/detector-runs`

## Future detectors

The contract is designed for semantic embeddings, HDBSCAN, BERTopic, change-point detection, graph community detection, entity co-occurrence, Bayesian aggregation, forecast divergence and narrative shift detection.
