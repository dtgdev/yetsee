"use client";

import { useMemo, useState } from "react";

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
  generated_at: string;
  derived: boolean;
};

const palette: Record<string,string> = {
  investigation: "#225fd1",
  hypothesis: "#7c5ce7",
  observation: "#f59e0b",
  source: "#0ea5e9",
  metric: "#8b5cf6",
  concept: "#16a36a",
  entity: "#4772d9",
  organization: "#4772d9",
  company: "#4772d9",
};

function color(kind:string){ return palette[kind.toLowerCase()] ?? palette.entity; }
function short(label:string){ return label.replaceAll("_"," ").slice(0,24); }

function positions(nodes:GraphNode[]){
  const center = nodes.find(n=>n.kind==="investigation") ?? nodes[0];
  const rest = nodes.filter(n=>n.id!==center?.id);
  const map = new Map<string,{x:number;y:number}>();
  if(center) map.set(center.id,{x:50,y:50});
  const rings:Record<string,GraphNode[]> = {hypothesis:[],observation:[],entity:[]};
  rest.forEach(n=>{
    if(n.kind==="hypothesis") rings.hypothesis.push(n);
    else if(n.kind==="observation") rings.observation.push(n);
    else rings.entity.push(n);
  });
  const place=(items:GraphNode[], radius:number, offset:number)=>items.forEach((n,i)=>{
    const angle=((Math.PI*2*i)/Math.max(1,items.length))+offset;
    map.set(n.id,{x:50+Math.cos(angle)*radius,y:50+Math.sin(angle)*radius});
  });
  place(rings.hypothesis,15,-Math.PI/2);
  place(rings.entity,29,-Math.PI/2+.3);
  place(rings.observation,42,-Math.PI/2+.15);
  return map;
}

export default function GalileoGraph({graph}:{graph:GraphData}){
  const [selectedId,setSelectedId]=useState(graph.nodes.find(n=>n.kind==="investigation")?.id ?? graph.nodes[0]?.id ?? "");
  const [query,setQuery]=useState("");
  const [kind,setKind]=useState("all");
  const [zoom,setZoom]=useState(1);
  const selected=graph.nodes.find(n=>n.id===selectedId) ?? graph.nodes[0];
  const neighbors=useMemo(()=>new Set(graph.edges.flatMap(e=>e.source===selectedId?[e.target]:e.target===selectedId?[e.source]:[])),[graph.edges,selectedId]);
  const visible=useMemo(()=>graph.nodes.filter(n=>{
    const q=query.trim().toLowerCase();
    return (kind==="all"||n.kind===kind) && (!q || n.label.toLowerCase().includes(q) || n.kind.toLowerCase().includes(q));
  }),[graph.nodes,query,kind]);
  const visibleIds=new Set(visible.map(n=>n.id));
  const edges=graph.edges.filter(e=>visibleIds.has(e.source)&&visibleIds.has(e.target));
  const pos=positions(visible);
  const kinds=[...new Set(graph.nodes.map(n=>n.kind))].sort();
  const relatedEdges=graph.edges.filter(e=>e.source===selectedId||e.target===selectedId);
  const evidenceIds=[...new Set(relatedEdges.flatMap(e=>e.evidence_ids))];

  return <div className="galileoWorkbench">
    <section className="galileoCanvas">
      <div className="galileoToolbar">
        <div className="galileoSearch"><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search nodes…"/></div>
        <select value={kind} onChange={e=>setKind(e.target.value)} aria-label="Filter graph by node type"><option value="all">All node types</option>{kinds.map(k=><option key={k} value={k}>{k}</option>)}</select>
        <div className="galileoZoom"><button onClick={()=>setZoom(z=>Math.max(.65,z-.15))}>−</button><button onClick={()=>setZoom(1)}>Fit</button><button onClick={()=>setZoom(z=>Math.min(1.8,z+.15))}>+</button></div>
      </div>
      <div className="galileoGraphStage">
        {!visible.length?<div className="graphEmpty">No nodes match this view.</div>:<svg viewBox="0 0 100 100" className="galileoSvg" style={{transform:`scale(${zoom})`}} aria-label="Canonical investigation graph">
          {edges.map(e=>{const a=pos.get(e.source),b=pos.get(e.target);if(!a||!b)return null;const active=e.source===selectedId||e.target===selectedId;return <g key={e.id} className={active?"activeEdge":""}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y}/><title>{e.kind} · {Math.round(e.confidence*100)}% · {e.evidence_ids.length} evidence</title></g>})}
          {visible.map(n=>{const p=pos.get(n.id)!;const active=n.id===selectedId;const connected=neighbors.has(n.id);const r=n.kind==="investigation"?4.3:n.kind==="hypothesis"?3.6:Math.max(2.2,Math.min(3.3,2.1+n.degree_centrality));return <g key={n.id} className={`galileoNode ${active?"selected":""} ${connected?"neighbor":""}`} onClick={()=>setSelectedId(n.id)} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==="Enter"||e.key===" ")setSelectedId(n.id)}}><circle cx={p.x} cy={p.y} r={r} fill={color(n.kind)}/><text x={p.x} y={p.y+r+4.3} textAnchor="middle">{short(n.label)}</text><title>{n.label} · {n.kind} · {n.evidence_count} evidence</title></g>})}
        </svg>}
      </div>
      <div className="galileoLegend">{kinds.map(k=><span key={k}><i style={{background:color(k)}}/>{k}</span>)}</div>
      <div className="galileoMetrics">
        <div><span>Nodes</span><strong>{graph.metrics.nodes}</strong></div>
        <div><span>Edges</span><strong>{graph.metrics.edges}</strong></div>
        <div><span>Components</span><strong>{graph.metrics.connected_components}</strong></div>
        <div><span>Density</span><strong>{graph.metrics.density.toFixed(3)}</strong></div>
        <div><span>Sources</span><strong>{graph.metrics.independent_sources}</strong></div>
      </div>
    </section>
    <aside className="galileoInspector">
      {selected?<>
        <div className="inspectorEyebrow">Selected node</div>
        <div className="inspectorTitle"><i style={{background:color(selected.kind)}}/><div><h3>{selected.label}</h3><span>{selected.kind}</span></div></div>
        {selected.description&&<p className="inspectorDescription">{selected.description}</p>}
        <dl className="inspectorStats">
          <div><dt>Degree</dt><dd>{selected.degree}</dd></div>
          <div><dt>Centrality</dt><dd>{Math.round(selected.degree_centrality*100)}%</dd></div>
          <div><dt>Evidence</dt><dd>{selected.evidence_count}</dd></div>
          <div><dt>Sources</dt><dd>{selected.source_count}</dd></div>
          <div><dt>Confidence</dt><dd>{Math.round(selected.confidence*100)}%</dd></div>
        </dl>
        <section className="inspectorSection"><span>Relationships</span>{relatedEdges.length?relatedEdges.slice(0,12).map(e=>{const otherId=e.source===selectedId?e.target:e.source;const other=graph.nodes.find(n=>n.id===otherId);return <button key={e.id} onClick={()=>other&&setSelectedId(other.id)}><div><strong>{e.kind.replaceAll("_"," ")}</strong><small>{other?.label??otherId}</small></div><em>{Math.round(e.confidence*100)}%</em></button>}):<p>No relationships in this projection.</p>}</section>
        <section className="inspectorSection"><span>Evidence path</span><div className="evidencePath"><b>{selected.kind}</b><i>→</i><b>{evidenceIds.length} evidence</b><i>→</i><b>{selected.source_count} sources</b></div></section>
        <section className="inspectorSection"><span>Metadata</span><pre>{JSON.stringify(selected.metadata,null,2)}</pre></section>
      </>:<p className="emptyText">Select a node to inspect its evidence and relationships.</p>}
    </aside>
  </div>
}
