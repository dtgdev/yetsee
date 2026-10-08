"use client";

import { useMemo, useState } from "react";
import { graphLayout, graphLabelLines } from "../lib/graph-layout";

type RankedNode = {
  node_id: string;
  domain_id?: string;
  label: string;
  kind: string;
  score: number;
  evidence_count: number;
  source_count: number;
};

type BridgeNode = {
  node_id: string;
  domain_id?: string;
  label: string;
  kind: string;
  betweenness: number;
  communities_connected: number;
  articulation_point: boolean;
  evidence_count?: number;
};

type Community = {
  id: number;
  size: number;
  node_ids: string[];
  semantic_nodes?: { node_id: string; domain_id?: string; label: string; kind: string }[];
  kinds: Record<string, number>;
};

type GraphNode = {
  id: string;
  domain_id: string;
  kind: string;
  label: string;
  description?: string | null;
  confidence: number;
  evidence_count: number;
  source_count: number;
  degree: number;
  degree_centrality: number;
  metadata: Record<string, any>;
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  kind: string;
  confidence: number;
  evidence_ids: string[];
  metadata: Record<string, any>;
};

type EvidencePathResult = {
  result_count: number;
  paths: {
    hop_count: number;
    nodes: { id: string; kind: string; label: string }[];
    relationships: { id: string; kind: string; direction: string; evidence_ids: string[] }[];
    evidence: { evidence_id: string; kind: string; source?: string; source_ref?: string; publication_title?: string; pmid?: string }[];
  }[];
};

type GraphData = {
  investigation: { id: string; title: string; status: string };
  nodes: GraphNode[];
  edges: GraphEdge[];
  metrics: {
    nodes: number;
    edges: number;
    entities: number;
    observations: number;
    hypotheses: number;
    independent_sources: number;
    sources: string[];
    connected_components: number;
    density: number;
    relationship_types: Record<string, number>;
  };
  analytics?: {
    degree_centrality?: Record<string, number>;
    betweenness_centrality?: Record<string, number>;
    closeness_centrality?: Record<string, number>;
    pagerank?: Record<string, number>;
    communities?: Community[];
    bridge_nodes?: BridgeNode[];
    articulation_points?: string[];
    connected_components?: string[][];
    central_nodes?: RankedNode[];
    semantic_central_nodes?: RankedNode[];
    top_nodes?: RankedNode[];
    top_semantic_nodes?: RankedNode[];
    density?: number;
  };
  generated_at: string;
  derived: boolean;
};

const palette: Record<string, string> = {
  investigation: "#315f73",
  hypothesis: "#776399",
  observation: "#d99a2b",
  source: "#0b8fad",
  metric: "#805ad5",
  concept: "#16835e",
  entity: "#4772d9",
  organization: "#4772d9",
  company: "#537c76",
  technology: "#537c76",
  market: "#667b92",
  publication: "#a37834",
  study: "#a37834",
  clinical_trial: "#a37834",
  evidence_gap: "#a66a55",
  assessment: "#776399",
  drug: "#537c76",
  population: "#667b92",
};

const communityPalette = ["#dce8fb", "#e6f4ed", "#f4ead9", "#eee8fb", "#e6f1f4", "#f5e8ed"];
const semanticKinds = new Set(["concept", "entity", "organization", "company", "person", "topic"]);

const kindLabels: Record<string, string> = {
  investigation: "Investigation",
  hypothesis: "Hypothesis",
  publication: "Publication",
  clinical_trial: "Clinical trial",
  study: "Study",
  population: "Patient group",
  drug: "Treatment",
  genomic_alteration: "Genomic finding",
  drug_resistance: "Resistance outcome",
  mechanism: "Mechanism",
  outcome: "Outcome",
  assay: "Method",
  source: "Source passage",
  company: "Company",
  product: "Product",
  technology: "Technology",
  market: "Market",
  funding_round: "Funding round",
  patent: "Patent",
  event: "Event",
  regulatory_event: "Regulatory event",
  assessment: "Evidence assessment",
  evidence_gap: "Evidence gap",
};

const relationshipLabels: Record<string, string> = {
  HAS_LITERATURE: "supported by publication",
  PUBLICATION_CONTAINS_PASSAGE: "contains source passage",
  PUBLICATION_REPORTS_STUDY: "reports results from",
  STUDY_HAS_POPULATION: "studied in",
  STUDY_USES_INTERVENTION: "uses treatment",
  STUDY_USES_ASSAY: "uses method",
  STUDY_MEASURES_OUTCOME: "measures",
  reported_as_resistance_mechanism: "reported as resistance mechanism",
  contributes_to: "may contribute to",
  MECHANISM_CONTRIBUTES_TO: "may contribute to",
  EVENT_INVOLVES: "involves",
  EVENT_PRECEDES: "happened before",
  ASSESSMENT_CONCERNS: "assesses",
  EVIDENCE_GAP_CONCERNS: "needs more evidence about",
  SUPPORTS: "supports",
  CONTRADICTS: "contradicts",
  CONTEXT_FOR: "provides context for",
  COMPANY_LAUNCHED_PRODUCT: "launched",
  COMPANY_RAISED_FUNDING: "raised funding",
  COMPANY_DEVELOPS_TECHNOLOGY: "develops",
};

function kindLabel(kind: string) {
  return kindLabels[kind] ?? kind.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function relationshipLabel(kind: string) {
  return relationshipLabels[kind] ?? kind.replaceAll("_", " ").toLowerCase();
}

function color(kind: string) {
  return palette[kind.toLowerCase()] ?? palette.entity;
}

function scorePercent(value: number | undefined) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export default function GalileoGraph({ graph }: { graph: GraphData }) {
  const [selectedId, setSelectedId] = useState(
    graph.nodes.find((n) => n.kind === "investigation")?.id ?? graph.nodes[0]?.id ?? "",
  );
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const [communityFilter, setCommunityFilter] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [viewMode, setViewMode] = useState<"simple" | "scientific">("simple");
  const [showDetails, setShowDetails] = useState(false);
  const [pathResult, setPathResult] = useState<EvidencePathResult | null>(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState("");

  const analytics = graph.analytics ?? {};
  const communities = analytics.communities ?? [];
  const bridgeNodes = analytics.bridge_nodes ?? [];
  const semanticCentral = analytics.semantic_central_nodes ?? analytics.top_semantic_nodes ?? [];
  const pagerank = analytics.pagerank ?? {};
  const betweenness = analytics.betweenness_centrality ?? {};
  const closeness = analytics.closeness_centrality ?? {};
  const standardDegree = analytics.degree_centrality ?? {};

  const communityByNode = useMemo(() => {
    const map = new Map<string, number>();
    communities.forEach((community) => community.node_ids.forEach((nodeId) => map.set(nodeId, community.id)));
    return map;
  }, [communities]);

  const selected = graph.nodes.find((n) => n.id === selectedId) ?? graph.nodes[0];
  const neighbors = useMemo(
    () =>
      new Set(
        graph.edges.flatMap((edge) =>
          edge.source === selectedId ? [edge.target] : edge.target === selectedId ? [edge.source] : [],
        ),
      ),
    [graph.edges, selectedId],
  );

  const visible = useMemo(
    () =>
      graph.nodes.filter((node) => {
        const q = query.trim().toLowerCase();
        const matchesCommunity = communityFilter === null || communityByNode.get(node.id) === communityFilter;

        return (
          matchesCommunity &&
          (kind === "all" || node.kind === kind) &&
          (!q || node.label.toLowerCase().includes(q) || node.kind.toLowerCase().includes(q))
        );
      }),
    [graph.nodes, query, kind, communityFilter, communityByNode, viewMode],
  );

  const visibleIds = new Set(visible.map((n) => n.id));
  const edges = graph.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));
  const layout = graphLayout(visible);
  const pos = layout.positions;
  const kinds = [...new Set(graph.nodes.map((n) => n.kind))].sort();
  const relatedEdges = graph.edges.filter((e) => e.source === selectedId || e.target === selectedId);
  const evidenceIds = [...new Set(relatedEdges.flatMap((e) => e.evidence_ids))];
  const selectedCommunity = selected ? communityByNode.get(selected.id) : undefined;
  const isBridge = selected ? bridgeNodes.find((item) => item.node_id === selected.id) : undefined;

  async function runEvidencePath(queryType: "why" | "before") {
    if (!selected) return;
    setPathLoading(true);
    setPathError("");
    setPathResult(null);
    try {
      const response = await fetch(`/api/investigations/${graph.investigation.id}/graph/query`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query_type: queryType, node_ref: selected.id, limit: 5 }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.detail ?? "Could not load evidence path");
      setPathResult(body);
    } catch (error) {
      setPathError(error instanceof Error ? error.message : "Could not load evidence path");
    } finally {
      setPathLoading(false);
    }
  }

  return (
    <div className="galileoWorkbench scientificStructureLens refinedGraph">
      <section className="galileoCanvas">
        <div className="galileoToolbar">
          <div className="galileoViewToggle" aria-label="Graph detail level">
            <button aria-pressed={viewMode === "simple"} className={viewMode === "simple" ? "active" : ""} onClick={() => { setViewMode("simple"); setKind("all"); setCommunityFilter(null); }}>Simple view</button>
            <button aria-pressed={viewMode === "scientific"} className={viewMode === "scientific" ? "active" : ""} onClick={() => setViewMode("scientific")}>Scientific view</button>
          </div>
          <div className="galileoSearch">
            <span>⌕</span>
            <input aria-label="Search graph items" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search concepts, evidence, sources…" />
          </div>
          {viewMode === "scientific" && <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Filter graph by node type">
            <option value="all">All types</option>
            {kinds.map((k) => (
              <option key={k} value={k}>{kindLabel(k)}</option>
            ))}
          </select>}
          <div className="galileoZoom">
            <button onClick={() => setZoom((z) => Math.max(0.65, z - 0.15))}>−</button>
            <button onClick={() => setZoom(1)}>Fit</button>
            <button onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))}>+</button>
          </div>
        </div>

        {viewMode === "simple" ? (
          <div className="simpleGraphSummary">
            <div><span>Key items</span><strong>{visible.length}</strong></div>
            <div><span>Evidence sources</span><strong>{graph.metrics.independent_sources}</strong></div>
            <div><span>Connections</span><strong>{edges.length}</strong></div>
          </div>
        ) : (
          <div className="structureAnalyticsStrip">
            <div><span>Semantic concepts</span><strong>{semanticCentral.length}</strong></div>
            <div><span>Communities</span><strong>{communities.length}</strong></div>
            <div><span>Bridge concepts</span><strong>{bridgeNodes.length}</strong></div>
            <div><span>Distinct sources</span><strong>{graph.metrics.independent_sources}</strong></div>
            <div><span>Density</span><strong>{(analytics.density ?? graph.metrics.density).toFixed(3)}</strong></div>
          </div>
        )}

        <div className="galileoGraphStage">
          {!visible.length ? (
            <div className="graphEmpty">No nodes match this scientific view.</div>
          ) : (
            <svg
              viewBox={`0 0 ${layout.width} ${layout.height}`}
              className="galileoSvg"
              style={{ width: `${zoom * 100}%`, height: layout.height * zoom }}
              role="group"
              aria-label="Investigation graph. Select an item to see its evidence."
            >
              {layout.columns.map((column) => <text key={column.label} className="graphColumnLabel" x={column.x} y={30} textAnchor="middle">{column.label}</text>)}
              {edges.map((edge) => {
                const a = pos.get(edge.source);
                const b = pos.get(edge.target);
                if (!a || !b) return null;
                const active = edge.source === selectedId || edge.target === selectedId;
                return (
                  <g key={edge.id} className={active ? "activeEdge" : ""}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
                    <title>{relationshipLabel(edge.kind)} · {edge.evidence_ids.length} evidence item(s)</title>
                  </g>
                );
              })}

              {visible.map((node) => {
                const p = pos.get(node.id)!;
                const active = node.id === selectedId;
                const connected = neighbors.has(node.id);
                const community = communityByNode.get(node.id);
                const bridge = viewMode === "scientific" && bridgeNodes.some((item) => item.node_id === node.id);
                const influence = viewMode === "scientific" ? pagerank[node.id] ?? node.degree_centrality : 0;
                const radius = node.kind === "investigation" ? 19 : node.kind === "hypothesis" ? 16 : Math.max(11, Math.min(16, 11 + influence * 30));
                return (
                  <g
                    key={node.id}
                    className={`galileoNode ${active ? "selected" : ""} ${connected ? "neighbor" : ""} ${bridge ? "bridgeNode" : ""}`}
                    onClick={() => setSelectedId(node.id)}
                    role="button"
                    aria-label={`${node.label}, ${kindLabel(node.kind)}`}
                    aria-pressed={active}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedId(node.id); }
                    }}
                  >
                    {viewMode === "scientific" && community !== undefined && semanticKinds.has(node.kind.toLowerCase()) && (
                      <circle cx={p.x} cy={p.y} r={radius + 6} fill={communityPalette[community % communityPalette.length]} className="communityHalo" />
                    )}
                    <circle cx={p.x} cy={p.y} r={radius} fill={color(node.kind)} />
                    {bridge && <circle cx={p.x} cy={p.y} r={radius + 4} className="bridgeRing" />}
                    <text x={p.x} y={p.y + radius + 20} textAnchor="middle">{graphLabelLines(node.label).map((line, index) => <tspan key={index} x={p.x} dy={index ? 17 : 0}>{line}</tspan>)}</text>
                    <title>{node.label} · {kindLabel(node.kind)} · {node.evidence_count} evidence item(s)</title>
                  </g>
                );
              })}
            </svg>
          )}
        </div>

        <div className="galileoLegend">
          {kinds.map((k) => <span key={k}><i style={{ background: color(k) }} />{kindLabel(k)}</span>)}
          {viewMode === "scientific" && bridgeNodes.length > 0 && <span><i className="bridgeLegend" />bridge concept</span>}
        </div>
        <div className="galileoViewNote">
          <strong>{viewMode === "simple" ? "Simple view" : "Scientific view"}</strong>
          <span>{viewMode === "simple" ? "All evidence connections are preserved. Columns group item types; they do not imply causation or time order. Select an item for its full name and evidence." : "Shows the complete evidence-derived graph, structural metrics and provenance."}</span>
        </div>

        {viewMode === "scientific" && <div className="scientificGraphPanels">
          <section>
            <div className="graphPanelHeading"><span>Central concepts</span><small>PageRank · semantic nodes only</small></div>
            <div className="rankedConceptList">
              {semanticCentral.slice(0, 5).map((item, index) => (
                <button key={item.node_id} onClick={() => setSelectedId(item.node_id)}>
                  <em>{index + 1}</em><span><strong>{item.label}</strong><small>{item.kind} · {item.evidence_count} evidence</small></span><b>{scorePercent(item.score)}</b>
                </button>
              ))}
              {!semanticCentral.length && <p className="emptyText">Semantic extraction has not produced ranked concepts yet.</p>}
            </div>
          </section>

          <section>
            <div className="graphPanelHeading"><span>Communities</span><small>Structural neighborhoods</small></div>
            <div className="communityExplorer">
              <button className={communityFilter === null ? "active" : ""} onClick={() => setCommunityFilter(null)}>
                <i className="communitySwatch all" /><span><strong>All communities</strong><small>{graph.metrics.nodes} nodes</small></span>
              </button>
              {communities.slice(0, 6).map((community) => (
                <button key={community.id} className={communityFilter === community.id ? "active" : ""} onClick={() => setCommunityFilter(communityFilter === community.id ? null : community.id)}>
                  <i className="communitySwatch" style={{ background: communityPalette[community.id % communityPalette.length] }} />
                  <span><strong>Community {community.id + 1}</strong><small>{community.size} nodes · {Object.keys(community.kinds).slice(0, 3).join(" · ")}</small></span>
                </button>
              ))}
            </div>
          </section>

          <section>
            <div className="graphPanelHeading"><span>Bridge concepts</span><small>Connect structural regions</small></div>
            <div className="bridgeConceptList">
              {bridgeNodes.slice(0, 5).map((bridge) => (
                <button key={bridge.node_id} onClick={() => setSelectedId(bridge.node_id)}>
                  <span><strong>{bridge.label}</strong><small>{bridge.communities_connected} communities · betweenness {scorePercent(bridge.betweenness)}</small></span>
                  {bridge.articulation_point && <em>critical</em>}
                </button>
              ))}
              {!bridgeNodes.length && <p className="emptyText">No evidence-backed semantic bridge concepts detected.</p>}
            </div>
          </section>
        </div>}
      </section>

      <aside className="galileoInspector scientificNodeInspector">
        {selected ? (
          <>
            <div className="inspectorEyebrow">Selected item</div>
            <div className="inspectorTitle">
              <i style={{ background: color(selected.kind) }} />
              <div><h3>{selected.label}</h3><span>{kindLabel(selected.kind)}</span></div>
            </div>
            {selected.description && <p className="inspectorDescription">{selected.description}</p>}

            <div className="inspectorBadges">
              {viewMode === "scientific" && selectedCommunity !== undefined && <span>Community {selectedCommunity + 1}</span>}
              {viewMode === "scientific" && isBridge && <span className="bridgeBadge">Bridge concept</span>}
              {selected.metadata?.status && <span>{String(selected.metadata.status).replaceAll("_", " ")}</span>}
            </div>

            <dl className="inspectorStats analyticsStats">
              <div><dt>Evidence</dt><dd>{selected.evidence_count}</dd></div>
              <div><dt>Sources</dt><dd>{selected.source_count}</dd></div>
              {viewMode === "scientific" && <><div><dt>PageRank</dt><dd>{scorePercent(pagerank[selected.id])}</dd></div>
              <div><dt>Betweenness</dt><dd>{scorePercent(betweenness[selected.id])}</dd></div>
              <div><dt>Closeness</dt><dd>{scorePercent(closeness[selected.id])}</dd></div>
              <div><dt>Degree centrality</dt><dd>{scorePercent(standardDegree[selected.id])}</dd></div></>}
            </dl>

            <section className="inspectorSection">
              <span>What connects this item</span>
              <p className="scientificInterpretation">
                {viewMode === "simple"
                  ? `${selected.label} has ${relatedEdges.length} relationship(s) in this investigation and is backed by ${selected.evidence_count} evidence item(s) from ${selected.source_count} source(s).`
                  : isBridge
                    ? `${selected.label} links ${isBridge.communities_connected} structural neighborhoods and carries ${scorePercent(isBridge.betweenness)} betweenness centrality.`
                    : `${selected.label} has ${scorePercent(pagerank[selected.id])} PageRank within this investigation-scoped projection and is backed by ${selected.evidence_count} evidence item(s).`}
              </p>
            </section>

            <section className="inspectorSection">
              <span>Relationships</span>
              {relatedEdges.length ? relatedEdges.slice(0, 12).map((edge) => {
                const otherId = edge.source === selectedId ? edge.target : edge.source;
                const other = graph.nodes.find((n) => n.id === otherId);
                return (
                  <button key={edge.id} onClick={() => other && setSelectedId(other.id)}>
                    <div><strong>{relationshipLabel(edge.kind)}</strong><small>{other?.label ?? otherId}</small></div>
                    {viewMode === "scientific" && <em>{Math.round(edge.confidence * 100)}%</em>}
                  </button>
                );
              }) : <p>No relationships in this projection.</p>}
            </section>

            <section className="inspectorSection">
              <span>Evidence path</span>
              <div className="evidencePath">
                <b>{kindLabel(selected.kind)}</b><i>→</i><b>{evidenceIds.length} evidence</b><i>→</i><b>{selected.source_count} sources</b>
              </div>
              <div className="evidencePathActions">
                <button onClick={() => runEvidencePath("why")} disabled={pathLoading}>
                  {pathLoading ? "Checking…" : "Show supporting evidence"}
                </button>
                {selected.kind === "event" && (
                  <button onClick={() => runEvidencePath("before")} disabled={pathLoading}>What happened before?</button>
                )}
              </div>
              {pathError && <p className="evidencePathError">{pathError}</p>}
              {pathResult && (
                <div className="evidencePathResults">
                  {pathResult.result_count === 0 ? (
                    <p>No evidence path was found in this investigation.</p>
                  ) : pathResult.paths.map((path, index) => (
                    <article key={index}>
                      <div className="evidencePathChain">
                        {path.nodes.map((node, nodeIndex) => (
                          <span key={node.id}>
                            {nodeIndex > 0 && <i>→</i>}
                            <b>{node.label}</b>
                          </span>
                        ))}
                      </div>
                      <small>
                        {path.evidence.length
                          ? path.evidence.map((item) => item.publication_title || item.source_ref || item.source || item.kind).join(" · ")
                          : "Derived graph path; inspect scientific details for provenance."}
                      </small>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="inspectorSection">
              <button className="detailsToggle" aria-expanded={showDetails} onClick={() => setShowDetails((value) => !value)}>
                <div><strong>{showDetails ? "Hide technical details" : "Show technical details"}</strong><small>Provenance, ontology metadata and graph identifiers</small></div>
                <em>{showDetails ? "−" : "+"}</em>
              </button>
              {showDetails && <pre>{JSON.stringify(selected.metadata, null, 2)}</pre>}
            </section>
          </>
        ) : (
          <p className="emptyText">Select a node to inspect its evidence, structural role, and relationships.</p>
        )}
      </aside>
    </div>
  );
}

