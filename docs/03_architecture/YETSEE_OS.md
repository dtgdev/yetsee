# YetSee OS Alpha Architecture

## Kernel

The Alpha kernel contains only:

- append-only kernel event log
- investigation versioning
- workflow runtime
- plugin registry contracts
- identity / permissions inherited from the platform foundation

## Extension plane

Existing capabilities are exposed as extension classes:

- connectors
- feature extractors
- semantic processors
- graph construction
- discovery models
- agents

Future reasoners, recommendations, learning models and visualizations should enter through the same extension philosophy.

## Invariant

**Evidence is immutable. Knowledge is reusable. Reasoning is replaceable. Investigations preserve understanding.**
