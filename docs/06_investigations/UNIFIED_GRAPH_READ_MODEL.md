# 6.11 — Unified Graph Read Model & Investigation Auto-Projection

Opening an investigation now prepares its literature, structured cross-domain,
temporal and evidence-state graph layers before loading the workspace. Users no
longer need to call four projection endpoints to populate the Structure lens.
The existing Galileo graph and page layout remain the presentation surface.

## Shared read contract

`GET /api/v1/investigations/{id}/graph/read-model` returns the existing
investigation graph shape plus:

- `read_model`: version, content-based graph ID, investigation scope and read-only policy.
- `auto_projection`: current/stale/not-prepared status, input fingerprint and preparation time.

The existing `GET /investigations/{id}/graph` returns the same contract. Path
queries, Graph Reasoner and evidence-filtered projections use the same service and report the
full graph's read-model identity. A filtered response identifies the full model
from which it was derived; its `scope` records the requested evidence filter.

Read operations do not commit transactions or invoke projectors. API clients can
prepare an investigation explicitly before reading or querying its graph:

```http
POST /api/v1/investigations/{id}/graph/auto-project
Content-Type: application/json

{}
```

`{"force": true}` rebuilds all layers even when the inputs are unchanged. The
investigation server page issues the normal command automatically, then loads
the shared model. Preparation failures produce a visible notice and preserve
access to the available graph. Graph read failures are surfaced, rather than
converted into an apparently empty graph.

## Projection lifecycle

`investigation_graph_projections` stores a derived freshness record and the
active entity/relationship membership for each investigation. The fingerprint
covers canonical evidence links, hypothesis links, observation payloads,
passages, publication metadata, candidate reviews and the projection/ontology
version, together with the effective research question. UTC normalization makes
it stable across database sessions.

Unchanged inputs skip all projectors. Changed inputs run the four layers in one
transaction. Existing manual projection commands retain their standalone
commit behavior; the coordinator calls them with `commit=False` and commits
their outputs and freshness record together. Any layer failure rolls back all
four layers and leaves the previous freshness record intact. PostgreSQL locks
the investigation row to serialize preparation for that investigation.

Canonical observations/passages, evidence links, investigation state and
hypothesis confidence are not rewritten. Graph assessment labels and confidence
reflect the current derived calculation, including confidence decreases.

Active membership excludes superseded temporal and assessment relationships
from investigation reads. Detached evidence does not remain visible solely
because historical provenance names the investigation. Temporal ordering needs
both events in scope. Investigation-owned assessments do not cross into another
investigation that shares a passage or observation. Historical derived rows can
remain in the global graph tables; this increment does not delete them globally.

## Rollout

Apply the additive migration before starting the updated API and web app:

```bash
cd apps/api
python -m alembic upgrade head
```

Existing investigations are prepared lazily on their next page load; no bulk
backfill or new source-evidence creation is required. Other API callers use the
preparation command themselves. A background event-driven projector and the
separate page-layout simplification are outside this increment.

## Verification

Regression coverage includes unchanged-input skips, forced idempotent rebuilds,
evidence/payload changes, fingerprint stability across sessions, rollback,
shared-source investigation isolation, obsolete temporal edges, detached
evidence, literature accounting, empty investigations and shared graph identity.
Existing graph/query/projector tests remain part of the backend regression suite.
