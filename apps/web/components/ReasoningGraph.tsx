"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import GalileoGraph from "./GalileoGraph";
import { apiGet } from "../lib/api";

type Entity={id:string;canonical_name:string;kind:string};
type Relationship={id:string;source_entity_id:string;target_entity_id:string;kind:string;confidence:number;evidence_ids:string[]};

type InvestigationGraph = {
  investigation:{id:string;title:string;status:string};
  nodes:any[];
  edges:any[];
  metrics:{
    nodes:number;
    edges:number;
    entities:number;
    observations:number;
    hypotheses:number;
    independent_sources:number;
    sources:string[];
    connected_components:number;
    density:number;
    relationship_types:Record<string,number>;
  };
  analytics?:Record<string,any>;
  generated_at:string;
  derived:boolean;
};

const positions=[
  [50,50],[28,27],[73,24],[18,58],[83,55],[36,78],[68,80],[50,15],[9,35],[91,33]
];

const tone=(kind:string)=>{
  const k=kind.toLowerCase();
  if(k.includes("source")) return "source";
  if(k.includes("metric")) return "metric";
  if(k.includes("concept")) return "concept";
  return "entity";
};

function LegacyReasoningGraph({entities,relationships}:{entities:Entity[];relationships:Relationship[]}){
  const visible=entities.slice(0,10);
  const idx=new Map(visible.map((e,i)=>[e.id,i]));
  const edges=relationships.filter(r=>idx.has(r.source_entity_id)&&idx.has(r.target_entity_id)).slice(0,18);
  if(!visible.length)return <div className="graphEmpty">No evidence-backed graph neighborhood is available yet.</div>;
  return <div className="reasoningGraphWrap">
    <svg className="reasoningGraph" viewBox="0 0 100 100" role="img" aria-label="Evidence-backed investigation graph">
      {edges.map(e=>{const a=positions[idx.get(e.source_entity_id)!]??positions[0];const b=positions[idx.get(e.target_entity_id)!]??positions[1];return <g key={e.id}><line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="reasoningEdge"/><title>{e.kind} · {Math.round(e.confidence*100)}% · {e.evidence_ids.length} evidence</title></g>})}
      {visible.map((e,i)=>{const p=positions[i]??[50,50];return <g key={e.id} className={`reasoningNode ${tone(e.kind)}`} tabIndex={0}><circle cx={p[0]} cy={p[1]} r={i===0?4.4:3.4}/><text x={p[0]} y={p[1]+7} textAnchor="middle">{e.canonical_name.replaceAll("_"," ").slice(0,18)}</text><title>{e.canonical_name} · {e.kind}</title></g>})}
    </svg>
    <div className="graphLegend"><span><i className="entity"/>entity</span><span><i className="concept"/>concept</span><span><i className="metric"/>metric</span><span><i className="source"/>source</span></div>
  </div>;
}

export default function ReasoningGraph({entities,relationships}:{entities:Entity[];relationships:Relationship[]}){
  const pathname=usePathname();
  const [graph,setGraph]=useState<InvestigationGraph|null>(null);
  const [failed,setFailed]=useState(false);

  useEffect(()=>{
    const match=pathname?.match(/\/investigations\/([^/?]+)/);
    const investigationId=match?.[1];
    if(!investigationId){setFailed(true);return;}
    let cancelled=false;
    setFailed(false);
    apiGet<InvestigationGraph>(`/api/v1/investigations/${investigationId}/graph`)
      .then(data=>{if(!cancelled)setGraph(data)})
      .catch(()=>{if(!cancelled)setFailed(true)});
    return()=>{cancelled=true};
  },[pathname]);

  if(graph){
    return <div className="unifiedReasoningGraph">
      <div className="unifiedReasoningGraphLabel">
        <span>CANONICAL INVESTIGATION GRAPH</span>
        <small>Same evidence-derived structure used by the Structure lens · reasoning is an interpretation overlay</small>
      </div>
      <GalileoGraph graph={graph as any}/>
    </div>;
  }

  if(!failed){
    return <div className="unifiedReasoningGraphLoading">Loading canonical investigation graph…</div>;
  }

  return <LegacyReasoningGraph entities={entities} relationships={relationships}/>;
}
