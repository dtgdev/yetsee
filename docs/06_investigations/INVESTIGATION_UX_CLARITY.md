# 6.12 — Investigation Workspace Clarity

Built on 6.11's unified graph read model. This increment refines the shared graph component, investigation navigation, Structure lens, and Reasoning lens. It does not change evidence, projection, algorithm output, or confidence calculations.

## Behavior

- Simple and Scientific views show the same complete graph unless explicitly searched or filtered. Evidence nodes and edges are retained. Simple hides analytical panels and type filters; switching back resets advanced filters.
- Nodes use deterministic, spaced columns: Question, Evidence, Related items, Findings & gaps. Columns organize item types, not causal direction or chronology. Recorded relationships retain their endpoints.
- Labels wrap to two lines, with ellipsis for longer names. The inspector shows full labels, evidence, source counts, relationships, and provenance. Nodes support keyboard selection and visible focus.
- Structure dedicates the main area to the graph; supplementary summary and interpretation are collapsed initially.
- Reasoning leads with the recorded conclusion and expandable factors, assumptions, limitations, and recommendations. Its graph is accessible through a disclosure, rather than squeezed into a third column.
- Structural support is explained as a method score, not hypothesis probability or causal proof. Hypothesis confidence remains separate; the no-hypothesis state explains this limit.
- The primary action is “Analyze evidence”; unavailable future lenses no longer compete with working investigation navigation.
- Readable type sizes, responsive stacking, and graph-local scrolling support small screens.

## Validation

TypeScript and production build pass. Deterministic layout checks cover empty, small, and 100-node graphs, minimum spacing, label wrapping, and ellipsis. Server-rendered page checks passed against synthetic data through actual API routes: Simple view retained all 9 nodes and 17 edges, auto-projection was current, and the recorded reasoning result rendered with the structural score explanation, no-hypothesis context, and collapsed graph. Interactive browser/visual QA could not run here: no Chromium executable was installed, and the browser download failed. Local desktop/mobile review is required before release.

This is a scoped first refinement. The global investigations landscape and unrelated pages retain their surrounding layouts; their shared graph display is improved. Large graphs use scrolling rather than force layout or clustering. Complete labels remain available in the inspector.
