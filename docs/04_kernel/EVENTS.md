# Intelligence Event Log

Kernel events are append-only records of meaningful platform state transitions.

Initial events:

- `WorkflowStarted`
- `WorkflowStepCompleted`
- `WorkflowCompleted`
- `WorkflowFailed`
- `InvestigationCommitted`

Each event has an aggregate type/id and a per-aggregate sequence number so an investigation or workflow can be replayed deterministically.
