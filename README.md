# YetSee OS Alpha

**See What's Next.**

YetSee OS Alpha is the first reference implementation of **Investigation-Centric Computing**: immutable evidence, reusable intelligence extensions, living investigations, append-only events and reproducible workflows.


## Real evidence connectors

Configure topics in `.env` with `EXTERNAL_SIGNAL_TOPICS`, then run:

```bash
curl -X POST http://localhost:8100/api/v1/connectors/reddit/run
curl -X POST http://localhost:8100/api/v1/connectors/google_trends/run
```

Connector execution now goes through the Kernel. New observations that exactly match an existing investigation title are attached as **neutral** investigation evidence and trigger an audited refresh. See `docs/REAL_EVIDENCE_CONNECTORS.md`.

## Kernel boundary

The Alpha kernel is deliberately small:

```text
Evidence / Observation Store
        ↓
Append-only Intelligence Event Log
        ↓
Versioned Investigations
        ↓
Workflow Runtime
        ↓
Plugin Registry / Contracts
```

Signal ingestion, feature extraction, semantics, graph construction, discovery and agents remain extensions around the kernel.

## Included

Everything from the existing YetSee platform foundation plus:

- `KernelEvent` append-only event log
- per-aggregate event sequence and replay
- immutable `InvestigationRevision` snapshots
- automatic first commit when a discovery candidate is promoted
- unified plugin registry over connectors, feature extractors, discovery models and agents
- reference `intelligence-refresh` workflow
- workflow execution history
- `yetsee` CLI entry point
- `yetsee.ai/v1alpha1` kernel compatibility namespace
- OS Alpha page at `/os`
- additive Alembic migration `0008_yetsee_os_kernel`
- constitution, theory, kernel, runtime and protocol docs


## Project Galileo — Investigation Graph

Every Living Investigation now exposes a deterministic, read-only graph projection:

```bash
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/graph
```

The projection connects the investigation, hypotheses, observations, and evidence-backed knowledge entities. It is derived from immutable records and includes investigation-scoped graph metrics such as degree centrality, connected components, density, and source diversity.

Open the Structure lens in Studio:

```text
http://localhost:3000/investigations/<INVESTIGATION_ID>?lens=structure
```

Select a node to inspect its relationships, evidence count, source count, centrality, and provenance without leaving the investigation workspace. Graph Reasoner v1.1 consumes this same canonical projection.

## Ports

- Studio/Web: http://localhost:3000
- OS Alpha: http://localhost:3000/os
- API: http://localhost:8100
- Swagger: http://localhost:8100/docs

## Run

```bash
cp .env.example .env
docker compose up --build
```

Existing YetSee PostgreSQL volumes are upgraded additively by Alembic.

## Exercise the reference runtime

Ingest deterministic evidence:

```bash
curl -X POST http://localhost:8100/api/v1/connectors/demo/run
```

Run the entire intelligence refresh as one reproducible workflow:

```bash
curl -X POST 'http://localhost:8100/api/v1/workflows/intelligence-refresh/run?hours=720'
```

Inspect the kernel:

```bash
curl http://localhost:8100/api/v1/kernel/status
curl http://localhost:8100/api/v1/plugins
curl http://localhost:8100/api/v1/events
curl http://localhost:8100/api/v1/workflow-runs
```

Inspect discovery candidates:

```bash
curl http://localhost:8100/api/v1/discovery/candidates
```

Promote a qualifying candidate:

```bash
curl -X POST http://localhost:8100/api/v1/discovery/candidates/<CANDIDATE_ID>/promote
```

The returned investigation now has a stable `id`. Inspect its version history:

```bash
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/history
```

Commit the current investigation state:

```bash
curl -X POST 'http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/commit?message=Reviewed%20new%20evidence'
```

Replay its kernel events:

```bash
curl http://localhost:8100/api/v1/events/investigation/<INVESTIGATION_ID>
```

## CLI

The API package installs a dependency-light CLI using Python's standard library:

```bash
export YETSEE_API_URL=http://localhost:8100/api/v1
yetsee status
yetsee plugins
yetsee events
yetsee run intelligence-refresh --hours 720
yetsee history <INVESTIGATION_ID>
```

## Frozen invariants

1. Evidence is immutable.
2. Knowledge is canonical and reusable.
3. Reasoning is replaceable.
4. Investigations are the unit of intelligence.
5. Extensions do not mutate the kernel contract.
6. Every conclusion retains lineage to evidence.

## Next reference slice

The next implementation should deepen the **Investigation Runtime** itself: hypothesis revisions, supporting vs. contradicting evidence, lifecycle transitions, investigation timelines and reasoner results—all built on the event/revision kernel added here.

## Living Investigation Runtime

After promoting a qualifying discovery candidate, open the investigation workspace:

```bash
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/workspace
```

Add a hypothesis:

```bash
curl -X POST http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/hypotheses \
  -H 'Content-Type: application/json' \
  -d '{"title":"Demand will continue accelerating","confidence":0.62}'
```

Advance lifecycle state:

```bash
curl -X POST http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/transition \
  -H 'Content-Type: application/json' \
  -d '{"state":"under_review","reason":"Evidence package ready for review"}'
```

Studio: `http://localhost:3000/investigations`

## Create your first investigation during development

Production quality gates remain strict. During local development you can explicitly promote a WATCH candidate so you can exercise the Living Investigation Runtime before additional real connectors are configured.

```bash
curl http://localhost:8100/api/v1/discovery/candidates

curl -X POST \
  'http://localhost:8100/api/v1/discovery/candidates/<CANDIDATE_ID>/promote?override=true&reason=Local%20runtime%20testing'

curl http://localhost:8100/api/v1/investigations
```

The response from promotion contains the persistent investigation `id`. Manual overrides are audited and are disabled automatically when `YETSEE_ENVIRONMENT=production`.

CLI equivalents:

```bash
yetsee investigate list
yetsee investigate promote <CANDIDATE_ID> --override --reason "Local runtime testing"
yetsee investigate open running-clubs
```

## Confidence Engine Alpha

After creating a hypothesis, link directional evidence to it. The Confidence Engine automatically records an append-only confidence update and investigation revision.

```bash
# Inspect observations and choose an observation id
curl 'http://localhost:8100/api/v1/observations?topic=running%20clubs'

# Link supporting evidence
curl -X POST \
  http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/hypotheses/<HYPOTHESIS_ID>/evidence \
  -H 'Content-Type: application/json' \
  -d '{"observation_id":"<OBSERVATION_ID>","stance":"supporting","weight":1.0,"rationale":"Independent evidence supports the hypothesis"}'

# Inspect current confidence and evidence weights
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/hypotheses/<HYPOTHESIS_ID>/confidence

# Inspect append-only confidence history
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/hypotheses/<HYPOTHESIS_ID>/confidence/history
```

The Alpha confidence calculator is deterministic: the same hypothesis prior and the same directional evidence always produce the same posterior. See `docs/06_investigations/CONFIDENCE_ENGINE.md`.

## Investigation Agents Alpha

Run the first runtime-native Evidence Agent against a living investigation:

```bash
curl -X POST http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/agents/evidence/run
```

Run the full investigation refresh loop (Evidence Agent + deterministic hypothesis confidence recalculation):

```bash
curl -X POST http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/refresh
```

The Evidence Agent audits source independence, repeated evidence patterns, missing source families, and missing counter-evidence. Findings are appended to the investigation timeline; raw observations are never rewritten.

## Kernel Command Runtime

Alpha 0.3 introduces a single audited command boundary for core investigation mutations. Current command types can be inspected with:

```bash
curl http://localhost:8100/api/v1/kernel/command-types
curl http://localhost:8100/api/v1/kernel/commands
```

Events emitted during a command carry command/correlation/causation metadata, making the full operation traceable across investigation revisions, confidence updates, and agent runs. See `docs/04_kernel/COMMAND_RUNTIME.md`.


## Scientific Studio v2

The root Studio page has been redesigned as a scientific investigation operating system. It uses live YetSee APIs for investigations, signal-lake metrics, graph metrics, agent activity, findings and connector health while keeping graceful fallbacks for a fresh install.

Canonical frontend files for this redesign:

- `apps/web/app/page.tsx`
- `apps/web/components/StudioChrome.tsx`
- `apps/web/app/styles.css`

Rebuild after upgrading:

```bash
docker compose down
docker compose up --build -d
```

Open `http://localhost:3000`.

## Scientific Reasoning Runtime (Alpha 0.4)

YetSee now stores reasoning as a first-class, replayable scientific artifact. The first reasoner is the deterministic Graph Reasoner v1.

```bash
curl http://localhost:8100/api/v1/reasoners
curl -X POST http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/reasoning/graph/run
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/reasoning/results
```

Studio: `http://localhost:3000/reasoning`

Reasoners interpret evidence but never mutate canonical observations or hypothesis confidence. Every run is routed through the Kernel and recorded in the investigation timeline.

## Alpha 0.5 — Unified Investigation Workspace

The Investigation is now the primary user-facing object in YetSee. Open any investigation and move between scientific lenses without leaving its context:

- `?lens=overview` — current scientific state and attention required
- `?lens=evidence` — immutable observations, source diversity, evidence challenges
- `?lens=structure` — evidence-backed graph neighborhood and structural interpretation
- `?lens=reasoning` — Graph Reasoner, reasoning pipeline, assumptions and limitations
- `?lens=history` — timeline, revisions, confidence evolution and kernel audit trail
- `?lens=compare` — cross-reasoner comparison surface (Graph active; additional lenses forthcoming)

Example:

`http://localhost:3000/investigations/<INVESTIGATION_ID>?lens=reasoning`

Forecast and Simulation are intentionally reserved as future lenses rather than new top-level product pages.
