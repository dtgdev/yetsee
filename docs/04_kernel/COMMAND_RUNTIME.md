# Kernel Command Runtime

YetSee OS Alpha routes meaningful investigation mutations through a single command execution boundary.

## Stable command envelope

Each command records:

- `command_id`
- `command_type`
- actor type/id
- aggregate type/id
- payload
- correlation id
- causation id
- requested/start/finish timestamps
- status and error

## Alpha command types

- `CreateHypothesis`
- `LinkHypothesisEvidence`
- `RecalculateHypothesisConfidence`
- `TransitionInvestigation`
- `RunInvestigationAgent`
- `RefreshInvestigation`

## Execution lifecycle

`validate -> authorize -> execute -> events -> revisions -> audit`

The current Alpha runtime preserves the public REST contracts while moving these write paths behind `execute_command()`.

## Correlation and causation

The command runtime uses a context-local execution context. Existing event publishers inherit the command metadata automatically, so nested events preserve:

- `command_id`
- `command_type`
- `correlation_id`
- `causation_id` when present
- command actor metadata

This allows incremental migration of existing engines without bypassing traceability.

## Permission boundary

Human/system callers continue to use the existing API authorization boundary during Alpha. Agent-issued kernel commands are checked against the registered agent manifest. Agents cannot acquire canonical-data mutation privileges implicitly.

## Audit API

- `GET /api/v1/kernel/commands`
- `GET /api/v1/kernel/commands/{command_id}`
- `GET /api/v1/kernel/command-types`

Failed commands remain visible in the command ledger with their error details.

## Invariant

New investigation mutations should prefer kernel commands rather than adding direct service mutations. Existing unmigrated write paths are transitional and should be moved incrementally rather than through a risky all-at-once rewrite.
