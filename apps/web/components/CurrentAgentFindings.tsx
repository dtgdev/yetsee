"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";

type Finding={id:string;agent_id:string;category:string;severity:string;stance:string;confidence:number;title:string;detail:string;evidence_ids:string[];metadata_json:Record<string,unknown>;created_at:string};
type CurrentFindings={investigation_id:string;current_findings:Finding[];current_task_ids:string[];history_count:number;policy:{current_view_uses_latest_completed_task_per_agent:boolean;historical_findings_preserved:boolean}};

export default function CurrentAgentFindings({investigationId}:{investigationId:string}){
  const [data,setData]=useState<CurrentFindings|null>(null);
  const [error,setError]=useState(false);
  useEffect(()=>{let active=true;apiGet<CurrentFindings>(`/api/v1/investigations/${investigationId}/current-agent-findings`).then(value=>{if(active)setData(value)}).catch(()=>{if(active)setError(true)});return()=>{active=false}},[investigationId]);
  if(error)return <p className="mechanicsNote">Current agent findings are temporarily unavailable. Historical findings remain preserved.</p>;
  if(!data)return <p className="mechanicsNote">Loading current agent findings…</p>;
  if(!data.current_findings.length)return <p className="mechanicsNote">No current agent challenges. Historical findings remain available in investigation history.</p>;
  return <div className="findingList">{data.current_findings.map(f=><article className={`finding ${f.severity}`} key={f.id}><span>!</span><div><strong>{f.title}</strong><p>{f.detail}</p><small>{f.agent_id} · {f.category}</small></div><b>{Math.round(f.confidence*100)}%<small>confidence</small></b></article>)}<p className="mechanicsNote">Current view: latest completed run per agent. {data.history_count} historical finding{data.history_count===1?"":"s"} preserved for audit/history.</p></div>;
}
