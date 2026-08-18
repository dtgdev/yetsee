# Galileo G3 — Agentic Investigation

## G3.0 scope

G3.0 makes the existing investigation-scoped agent runtime visible inside the Living Investigation workspace.

It adds an **Agents** lens with:

- the registered scientific agent team,
- latest investigation task status per agent,
- latest evidence-linked finding per agent,
- a deterministic current-assessment panel,
- a next-best-action panel driven by current agent findings,
- an investigation task ledger,
- and a **Run Investigation Team** action backed by `POST /api/v1/investigations/{id}/agents/run`.

## Boundary

G3.0 does **not** introduce a persistent Mission model. The current team run uses the existing ordered, typed orchestration runtime. Persistent `InvestigationMission` / `InvestigationMissionStep` state, mission replay and per-step command linkage belong to G3.1.

The invariant remains:

> Agents investigate. Reasoners interpret. Humans decide. The Kernel records.

Agents may create findings and recommendations under explicit constraints. They do not silently rewrite canonical observations or turn recommendations into conclusions.
