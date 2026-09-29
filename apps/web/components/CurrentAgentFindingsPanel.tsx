"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import { ResearchPanel } from "./ResearchWorkspace";

type Finding = {
  id:string; task_id:string; agent_id:string; target_type:string|null; target_id:string|null;
  category:string; severity:string; stance:string; confidence:number; title:string; detail:string;
  evidence_ids:string[]; metadata_json:Record<string,unknown>; created_at:string|null; updated_at:string|null;
};

type CurrentFindingsResponse = {
  investigation_id:string; current_findings:Finding[]; current_task_ids:string[]; history_count:number;
  policy:{current_view_uses_latest_completed_task_per_agent:boolean;historical_findings_preserved:boolean};
};

export default function CurrentAgentFindingsPanel({investigationId}:{investigationId:string}){
  const [data,setData]=useState<CurrentFindingsResponse|null>(null);
  const [status,setStatus]=useState<"loading"|"ready"|"error">("loading");

  useEffect(()=>{
    let active=true;
    apiGet<CurrentFindingsResponse>("/api/v1/investigations/"+investigationId+"/current-agent-findings")
      .then(result=>{if(active){setData(result);setStatus("ready")}})
      .catch(()=>{if(active)setStatus("error")});
    return()=>{active=false};
  },[investigationId]);

  if(status==="loading"){
    return <ResearchPanel title="Evidence challenges" subtitle="Loading current agent findings…"><p className="emptyText">Refreshing the latest completed agent assessment.</p></ResearchPanel>;
  }
  if(status==="error"){
    return <ResearchPanel title="Evidence challenges" subtitle="Current agent findings are temporarily unavailable."><p className="emptyText">Historical findings remain preserved in investigation history.</p></ResearchPanel>;
  }

  const findings=data?.current_findings??[];
  return <ResearchPanel title="Evidence challenges" subtitle="Current findings from the latest completed run of each agent. Historical findings remain preserved in investigation history.">
    {findings.length?<div className="findingListV2">{findings.map(f=><div key={f.id}>
      <span className={"findingDot "+f.severity}>!</span>
      <div><strong>{f.title}</strong><p>{f.detail}</p><small>{f.agent_id} · {f.category}</small></div>
      <div><b>{Math.round(f.confidence*100)}%</b><span>{f.evidence_ids.length} evidence</span></div>
    </div>)}</div>:<p className="emptyText">No current agent challenges. Historical findings remain available in investigation history.</p>}
  </ResearchPanel>;
}
