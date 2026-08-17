# Feature Engine

The Feature Engine sits between the immutable Signal Lake and replaceable Discovery Engine models.

## Invariant

Observations are source evidence. Features are derived, versioned, append-only representations. Recomputing a feature never mutates prior feature history.

## Pipeline

```text
Signal Lake
  -> Feature Extractors
     -> temporal
     -> statistical
     -> source
     -> semantic fingerprint
  -> Feature Store
  -> Discovery Models
```

Each feature records its subject, type, name, scalar or vector value, extractor/version, confidence, computation time, evidence IDs, and run metadata.

## Extractor contract

Every extractor exposes a manifest and an `extract(observations)` method. Production embedding models, entity features, graph features, geospatial features, and forecasting inputs can be added without changing feature storage or discovery candidate schemas.

The included semantic representation is deliberately dependency-light: a deterministic 24-dimensional hashed fingerprint. It is a contract baseline, not the final embedding model.

## Discovery integration

A discovery run recomputes a window-specific feature snapshot, then supplies those features to detectors. Velocity and acceleration v1.1 consume shared temporal features when present and retain raw-observation fallback behavior.

## API

- `GET /api/v1/feature-extractors`
- `POST /api/v1/features/recompute?hours=720`
- `GET /api/v1/features`
- `GET /api/v1/features/subject/{subject}`
- `GET /api/v1/feature-runs`
- `GET /api/v1/feature-store/summary`

## Next extensions

- production semantic embeddings
- HDBSCAN/BERTopic-ready embedding snapshots
- entity/co-occurrence features
- graph centrality/community features
- geographic spread features
- feature materialization policies and retention tiers
