# Living Investigation Runtime

An Investigation is YetSee OS's persistent unit of understanding.

## Lifecycle

`new -> collecting -> under_review -> active -> monitoring`

Active investigations may enter `simulating`, `recommending`, and `learning`; archived investigations may be reopened into monitoring. Invalid state jumps are rejected by the runtime.

Legacy `emerging`, `watch`, `candidate`, and `resolved` values are normalized at the runtime boundary for compatibility.

## Hypotheses

Hypotheses are first-class, versioned-by-history objects. They have a confidence value, status, author provenance and optional supersession pointer. Evidence is linked directionally as `supporting`, `contradicting`, or `neutral`.

## Timeline and commits

Every meaningful runtime action emits an append-only kernel event and creates an InvestigationRevision commit. The workspace is therefore replayable and diffable without rewriting evidence.

## API

- `GET /api/v1/investigations/{id}/workspace`
- `POST /api/v1/investigations/{id}/transition`
- `POST /api/v1/investigations/{id}/hypotheses`
- `GET /api/v1/investigations/{id}/hypotheses`
- `POST /api/v1/investigations/{id}/hypotheses/{hypothesis_id}/evidence`
- `GET /api/v1/investigations/{id}/timeline`
- `GET /api/v1/investigations/{id}/diff?from_revision=1&to_revision=2`

The runtime never mutates observations. It only links them into evolving interpretations.
