"use client";

import { useMemo, useState } from "react";

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
  investigation: "#245fd3",
  hypothesis: "#7c5ce7",
  observation: "#d99a2b",
  source: "#0b8fad",
  metric: "#805ad5",
  concept: "#16835e",
  entity: "#4772d9",
  organization: "#4772d9",
  company: "#4772d9",
};

const communityPalette = ["#dce8fb", "#e6f4ed", "#f4ead9", "#eee8fb", "#e6f1f4", "#f5e8ed"];
const semanticKinds = new Set(["concept", "entity", "organization", "company", "person", "topic"]);

function color(kind: string) {
  return palette[kind.toLowerCase()] ?? palette.entity;
}

function short(label: string) {
  return label.replaceAll("_", " ").slice(0, 24);
}

function positions(nodes: GraphNode[]) {
  const center = nodes.find((n) => n.kind === "investigation") ?? nodes[0];
  const rest = nodes.filter((n) => n.id !== center?.id);
  const map = new Map<string, { x: number; y: number }>();
  if (center) map.set(center.id, { x: 50, y: 50 });

  const rings: Record<string, GraphNode[]> = { hypothesis: [], observation: [], entity: [] };
  rest.forEach((n) => {
    if (n.kind === "hypothesis") rings.hypothesis.push(n);
    else if (n.kind === "observation") rings.observation.push(n);
    else rings.entity.push(n);
  });

  const place = (items: GraphNode[], radius: number, offset: number) =>
    items.forEach((n, i) => {
      const angle = (Math.PI * 2 * i) / Math.max(1, items.length) + offset;
      map.set(n.id, { x: 50 + Math.cos(angle) * radius, y: 50 + Math.sin(angle) * radius });
    });

  place(rings.hypothesis, 15, -Math.PI / 2);
  place(rings.entity, 29, -Math.PI / 2 + 0.3);
  place(rings.observation, 42, -Math.PI / 2 + 0.15);
  return map;
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
    [graph.nodes, query, kind, communityFilter, communityByNode],
  );

  const visibleIds = new Set(visible.map((n) => n.id));
  const edges = graph.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));
  const pos = positions(visible);
  const kinds = [...new Set(graph.nodes.map((n) => n.kind))].sort();
  const relatedEdges = graph.edges.filter((e) => e.source === selectedId || e.target === selectedId);
  const evidenceIds = [...new Set(relatedEdges.flatMap((e) => e.evidence_ids))];
  const selectedCommunity = selected ? communityByNode.get(selected.id) : undefined;
  const isBridge = selected ? bridgeNodes.find((item) => item.node_id === selected.id) : undefined;

  return (
    <div className="galileoWorkbench scientificStructureLens">
      <section className="galileoCanvas">
        <div className="galileoToolbar">
          <div className="galileoSearch">
            <span>⌕</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search concepts, evidence, sources…" />
          </div>
          <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Filter graph by node type">
            <option value="all">All node types</option>
            {kinds.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
          <div className="galileoZoom">
            <button onClick={() => setZoom((z) => Math.max(0.65, z - 0.15))}>−</button>
            <button onClick={() => setZoom(1)}>Fit</button>
            <button onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))}>+</button>
          </div>
        </div>

        <div className="structureAnalyticsStrip">
          <div><span>Semantic concepts</span><strong>{semanticCentral.length}</strong></div>
          <div><span>Communities</span><strong>{communities.length}</strong></div>
          <div><span>Bridge concepts</span><strong>{bridgeNodes.length}</strong></div>
          <div><span>Independent sources</span><strong>{graph.metrics.independent_sources}</strong></div>
          <div><span>Density</span><strong>{(analytics.density ?? graph.metrics.density).toFixed(3)}</strong></div>
        </div>

        <div className="galileoGraphStage">
          {!visible.length ? (
            <div className="graphEmpty">No nodes match this scientific view.</div>
          ) : (
            <svg
              viewBox="0 0 100 100"
              className="galileoSvg"
              style={{ transform: `scale(${zoom})` }}
              aria-label="Canonical investigation graph"
            >
              {edges.map((edge) => {
                const a = pos.get(edge.source);
                const b = pos.get(edge.target);
                if (!a || !b) return null;
                const active = edge.source === selectedId || edge.target === selectedId;
                return (
                  <g key={edge.id} className={active ? "activeEdge" : ""}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
                    <title>{edge.kind} · {Math.round(edge.confidence * 100)}% · {edge.evidence_ids.length} evidence</title>
                  </g>
                );
              })}

              {visible.map((node) => {
                const p = pos.get(node.id)!;
                const active = node.id === selectedId;
                const connected = neighbors.has(node.id);
                const community = communityByNode.get(node.id);
                const bridge = bridgeNodes.some((item) => item.node_id === node.id);
                const influence = pagerank[node.id] ?? node.degree_centrality;
                const radius = node.kind === "investigation" ? 4.5 : node.kind === "hypothesis" ? 3.7 : Math.max(2.15, Math.min(3.6, 2.15 + influence * 8));
                return (
                  <g
                    key={node.id}
                    className={`galileoNode ${active ? "selected" : ""} ${connected ? "neighbor" : ""} ${bridge ? "bridgeNode" : ""}`}
                    onClick={() => setSelectedId(node.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") setSelectedId(node.id);
                    }}
                  >
                    {community !== undefined && semanticKinds.has(node.kind.toLowerCase()) && (
                      <circle cx={p.x} cy={p.y} r={radius + 1.35} fill={communityPalette[community % communityPalette.length]} className="communityHalo" />
                    )}
                    <circle cx={p.x} cy={p.y} r={radius} fill={color(node.kind)} />
                    {bridge && <circle cx={p.x} cy={p.y} r={radius + 0.8} className="bridgeRing" />}
                    <text x={p.x} y={p.y + radius + 4.3} textAnchor="middle">{short(node.label)}</text>
                    <title>{node.label} · {node.kind} · PageRank {scorePercent(pagerank[node.id])} · {node.evidence_count} evidence</title>
                  </g>
                );
              })}
            </svg>
          )}
        </div>

        <div className="galileoLegend">
          {kinds.map((k) => <span key={k}><i style={{ background: color(k) }} />{k}</span>)}
          {bridgeNodes.length > 0 && <span><i className="bridgeLegend" />bridge concept</span>}
        </div>

        <div className="scientificGraphPanels">
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
        </div>
      </section>

      <aside className="galileoInspector scientificNodeInspector">
        {selected ? (
          <>
            <div className="inspectorEyebrow">Scientific node inspector</div>
            <div className="inspectorTitle">
              <i style={{ background: color(selected.kind) }} />
              <div><h3>{selected.label}</h3><span>{selected.kind}</span></div>
            </div>
            {selected.description && <p className="inspectorDescription">{selected.description}</p>}

            <div className="inspectorBadges">
              {selectedCommunity !== undefined && <span>Community {selectedCommunity + 1}</span>}
              {isBridge && <span className="bridgeBadge">Bridge concept</span>}
              {selected.metadata?.status && <span>{String(selected.metadata.status).replaceAll("_", " ")}</span>}
            </div>

            <dl className="inspectorStats analyticsStats">
              <div><dt>PageRank</dt><dd>{scorePercent(pagerank[selected.id])}</dd></div>
              <div><dt>Betweenness</dt><dd>{scorePercent(betweenness[selected.id])}</dd></div>
              <div><dt>Closeness</dt><dd>{scorePercent(closeness[selected.id])}</dd></div>
              <div><dt>Degree centrality</dt><dd>{scorePercent(standardDegree[selected.id])}</dd></div>
              <div><dt>Evidence</dt><dd>{selected.evidence_count}</dd></div>
              <div><dt>Sources</dt><dd>{selected.source_count}</dd></div>
            </dl>

            <section className="inspectorSection">
              <span>Why this node matters</span>
              <p className="scientificInterpretation">
                {isBridge
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
                    <div><strong>{edge.kind.replaceAll("_", " ")}</strong><small>{other?.label ?? otherId}</small></div>
                    <em>{Math.round(edge.confidence * 100)}%</em>
                  </button>
                );
              }) : <p>No relationships in this projection.</p>}
            </section>

            <section className="inspectorSection">
              <span>Evidence path</span>
              <div className="evidencePath">
                <b>{selected.kind}</b><i>→</i><b>{evidenceIds.length} evidence</b><i>→</i><b>{selected.source_count} sources</b>
              </div>
            </section>

            <section className="inspectorSection">
              <span>Scientific provenance</span>
              <pre>{JSON.stringify(selected.metadata, null, 2)}</pre>
            </section>
          </>
        ) : (
          <p className="emptyText">Select a node to inspect its evidence, structural role, and relationships.</p>
        )}
      </aside>
    </div>
  );
}
