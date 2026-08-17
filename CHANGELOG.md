# Changelog

## Alpha 0.6 — Project Galileo G1–G3

- Added a deterministic, investigation-scoped canonical graph projection at `GET /api/v1/investigations/{id}/graph`.
- Canonical graph now connects investigations, hypotheses, observations, and evidence-backed knowledge entities without mutating source records.
- Added investigation-scoped degree centrality, connected components, density, source coverage, and relationship-type metrics.
- Added interactive Structure lens with search, node-type filtering, zoom controls, neighborhood highlighting, and persistent node inspector.
- Node inspector exposes evidence count, source count, degree, centrality, relationships, evidence path summary, and provenance metadata.
- Graph Reasoner v1.1 now consumes the same canonical investigation graph used by Studio, keeping visualization and reasoning on one shared representation.
- Added Galileo regression tests for deterministic, evidence-backed investigation graph construction.

## Alpha 0.4.1 — Interactive Reasoning Laboratory

- Reworked Reasoning into a three-pane scientific workbench.
- Added evidence-backed SVG graph explorer with relationship tooltips.
- Added investigation context, structural metrics, reasoning pipeline, and trust checklist.
- Added collapsible conclusion/factors/assumptions/limitations/recommended-evidence report.
- Added confidence evolution, model comparison placeholders, reasoning timeline, and kernel command trail.


## Alpha 0.3 - Real Evidence Connectors

- Added Reddit connector for configured investigation topics.
- Added Google Trends connector through an isolated pytrends adapter.
- Added connector health state to the Signal Lake API/Studio.
- Routed connector runs through the Kernel Command Runtime (`RunConnector`).
- Added `ObservationCreated`, `ConnectorRunStarted`, and `ConnectorRunCompleted` audit events.
- Added conservative exact-topic matching from new observations to existing investigations.
- Matched external observations are neutral investigation evidence; ingestion never silently changes hypothesis confidence.
- Automatically launches causally-linked investigation refresh commands after matching.
- Added connector/matching/kernel contract tests.


## Alpha 0.3 - Kernel Command Runtime

- Added typed `KernelCommand` envelope and centralized command executor.
- Added append-only/auditable `kernel_command_log` with migration `0011_kernel_command_runtime`.
- Added correlation and causation propagation into nested kernel events.
- Added centralized agent permission checks for kernel-issued mutation commands.
- Migrated hypothesis creation, directional evidence linking, confidence recalculation, investigation transitions, Evidence Agent execution, and investigation refresh behind the command runtime.
- Added kernel command ledger and command-type APIs.
- Added contract tests for success, failure audit, permission denial, and nested event correlation.

## Signal Lake milestone

- Added connector SDK and registry.
- Added demo and Hacker News connectors.
- Added connector run/state persistence.
- Added deterministic observation hashing and deduplication.
- Added provenance on accepted observations.
- Added observation replay API.
- Added Signal Lake summary and UI.
- Added optional scheduler process.
- Added additive Alembic migration `0002_signal_lake`.

## Discovery Engine milestone

- Added pluggable `DiscoveryDetector` contract and detector registry.
- Added velocity, acceleration, novelty, and semantic-cluster baseline detectors.
- Added detector-run audit records and recomputable discovery candidates.
- Added ensemble candidate synthesis with detector scores and exact evidence IDs.
- Added candidate-to-investigation promotion with evidence links.
- Added Discovery Engine and candidate-detail UI pages.
- Added additive Alembic migration `0003_discovery_engine`.

## Knowledge Graph Engine

- Added canonical entity resolution and aliases.
- Added evidence-backed temporal relationship metadata.
- Added graph rebuild audit runs.
- Added semantic similarity edges based on Feature Store representations.
- Added append-only graph degree, centrality and community features.
- Added graph-community discovery detector.
- Added graph summary, entities, relationships and neighborhood APIs.
- Added Knowledge Graph and entity-neighborhood UI pages.
- Added migration `0005_knowledge_graph` and graph tests.

## Agent Orchestration Layer

- Added typed `AgentTask`, `AgentRun`, and evidence-linked `AgentFinding` records.
- Added a stable agent registry with eight bounded roles.
- Added explicit permission manifests and canonical-data mutation guardrails.
- Added deterministic investigation-team orchestration.
- Added evidence critic, graph analyst, opportunity analyst, quality, entity curator, discovery analyst, signal steward, and investigation coordinator baselines.
- Added `/agents`, `/agent-plane/summary`, task/run/finding APIs, and investigation-team execution APIs.
- Added Agent Plane UI at `/agents`.
- Added Alembic migration `0006_agent_orchestration`.

## Semantic Engine

- Added append-only `SemanticConcept` and audited `SemanticRun` records.
- Added canonical concept extraction, alias/entity linking, theme rules, article-title fallback classification, and low-confidence keyphrases.
- Added `/semantics/recompute`, `/semantic-concepts`, `/semantic-runs`, and `/semantic-engine/summary` APIs.
- Integrated semantic concepts into Knowledge Graph edge extraction.
- Integrated semantic canonicalization into discovery synthesis so source-specific article titles can map to durable concepts.
- Added `WATCH` vs `CANDIDATE` quality gates using evidence count, source diversity, and detector agreement.
- Blocked direct promotion of WATCH candidates.
- Added Semantic Curator agent for audited semantic quality review.
- Added Semantic Engine UI at `/semantics` and discovery quality/status indicators.
- Added Alembic migration `0007_semantic_engine` and semantic engine tests.

## YetSee OS Alpha — Intelligence Kernel

- Added append-only kernel event log and replay.
- Added immutable investigation revision history.
- Added automatic investigation commit on candidate promotion.
- Added unified plugin registry facade.
- Added deterministic intelligence-refresh workflow runtime and audit history.
- Added dependency-light `yetsee` CLI.
- Added `/os` frontend status surface.
- Added `yetsee.ai/v1alpha1` compatibility namespace and architecture constitution/docs.
- Added Alembic migration `0008_yetsee_os_kernel`.

## YetSee OS Alpha — Living Investigation Runtime

- Added explicit investigation lifecycle state machine.
- Added first-class hypotheses with confidence and authorship.
- Added directional hypothesis evidence: supporting, contradicting, neutral.
- Added investigation workspace API aggregating lifecycle, hypotheses, evidence, timeline and revisions.
- Added investigation diff API between immutable revisions.
- Added kernel events for state changes, hypotheses and evidence links.
- Added `/investigations` and `/investigations/[id]` Studio surfaces.
- Added additive Alembic migration `0009_living_investigation`.

## YetSee OS Alpha - Investigation Usability

- Added development-only manual promotion override for WATCH discovery candidates.
- Manual overrides require a reason and emit `CandidatePromotionOverridden`.
- Promotion metadata preserves the original quality-gate failure.
- Production environments always reject manual override.
- Added investigation lookup by UUID and slug.
- Added `yetsee investigate list`, `open`, and `promote` CLI commands.

## Confidence Engine Alpha

- Added `prior_confidence` to hypotheses so recalculation is deterministic and does not drift.
- Added append-only `hypothesis_confidence_history`.
- Directional hypothesis evidence now automatically recalculates confidence.
- Added `EvidenceLinked`, `HypothesisConfidenceChanged`, and `HypothesisRecalculated` event flow.
- Investigation commits now snapshot hypotheses and hypothesis evidence for meaningful diffs/replay.
- Added confidence/current/history/recalculate APIs and CLI commands.
- Updated Investigation Studio to show prior vs current confidence, evidence weights, and confidence history.

## Investigation Agents Alpha

- Added deterministic `evidence_agent` specialist role.
- Added source-diversity, repeated-evidence, missing-source, and counter-evidence audits.
- Added `AgentRunStarted`, `AgentFindingCreated`, `AgentRunCompleted`, and `InvestigationRefreshed` kernel events.
- Added `POST /api/v1/investigations/{id}/agents/evidence/run`.
- Added `POST /api/v1/investigations/{id}/refresh` to run evidence audit plus deterministic confidence recalculation.
- Added agent findings/tasks to the Living Investigation workspace.
- Added Studio controls and findings panel.
- Added CLI `yetsee investigate evidence-agent` and `yetsee investigate refresh` commands.

## Studio v2 — Scientific Research Dashboard
- Replaced the marketing-style homepage with an investigation-first scientific operating system dashboard.
- Added persistent research navigation, command search, system health, live agent activity, quick actions and recent findings.
- Added live platform metrics backed by investigations, Signal Lake, Knowledge Graph, agents and connectors.
- Added a featured Living Investigation card with confidence, evidence, independent sources and agent findings.
- Added Evidence Flow and Source Diversity visualizations with scientific, restrained visual language.
- Preserved the white research-journal aesthetic while adding blue information accents and semantic status colors.

## Studio v2.1 — Unified Scientific Workspace
- Migrated Investigations, Investigation detail, Discovery, Candidate detail, Agents, Operations, Evidence Lake, Knowledge Graph, Entity detail, Feature Store, Semantics and Kernel pages into the same Studio shell as Home.
- Added shared scientific page header, metric cards, research panels, status pills, evidence tables and audited ledger visuals.
- Removed legacy oversized editorial hero treatment from primary research workflows.
- Preserved live API-backed content while unifying navigation, spacing, typography and status semantics.

## Alpha 0.4 — Reasoning Runtime
- Added persistent `ReasoningRun` and `ReasoningResult` scientific artifacts.
- Added `RunReasoner` kernel command with command/correlation traceability.
- Added deterministic Graph Reasoner v1 (`What does the structure imply?`).
- Added `ReasoningStarted`, `ReasoningCompleted`, and `ReasoningFailed` investigation events.
- Added reasoner registry and reasoning REST APIs.
- Added Reasoning Laboratory to the unified scientific Studio shell.
- Investigation workspace now includes reasoning runs and results.
- Added migration `0012_reasoning_runtime` and focused reasoning regression tests.

## Alpha 0.5 — Unified Investigation Workspace

- Made the investigation the primary scientific workspace.
- Added Overview, Evidence, Structure, Reasoning, History, and Compare lenses.
- Embedded the interactive graph and Reasoning Runtime directly inside an investigation.
- Added investigation-wide context strip and scientific lens navigation.
- Added cross-lens evidence, confidence, timeline, revisions, agent findings, and kernel audit views.
- Reduced global navigation so Evidence/Graph/Reasoning are capabilities inside investigations rather than separate destinations.
- Added documented workspace routing contract under `docs/06_investigations/UNIFIED_WORKSPACE.md`.
