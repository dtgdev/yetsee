"use client";

import { useEffect, useState } from "react";

type Decision={id:string;mission_id:string;action_type:string;status:string;priority:string;confidence:number;rationale:string;proposed_objective:string;source_agent_ids:string[];source_finding_ids:string[];evidence_ids:string[];next_mission_id?:string|null;created_at?:string};

function humanize(value:string){return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}

export default function ScientificDecisionPanel({investigationId,missionId,onMissionCreated}:{investigationId:string;missionId:string;onMissionCreated:(missionId:string)=>Promise<void>}){
  const [decision,setDecision]=useState<Decision|null>(null);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState<string|null>(null);

  async function load(){
    const response=await fetch(`/api/investigations/${investigationId}/decisions`,{cache:"no-store"});
    if(!response.ok)return;
    const body=await response.json();
    const items=Array.isArray(body)?body:[];
    setDecision(items.find((item:Decision)=>item.mission_id===missionId)??null);
  }
  useEffect(()=>{void load()},[investigationId,missionId]);

  async function propose(){
    setBusy(true);setMessage(null);
    try{
      const response=await fetch(`/api/missions/${missionId}/decision`,{method:"POST"});
      const body=await response.json();
      if(!response.ok)throw new Error(body?.detail??"Could not create scientific decision");
      setDecision(body);setMessage("Decision persisted from the mission synthesis. Review it before creating another mission.");
    }catch(error){setMessage(error instanceof Error?error.message:"Could not create scientific decision")}
    finally{setBusy(false)}
  }

  async function createNextMission(){
    if(!decision)return;
    setBusy(true);setMessage(null);
    try{
      const response=await fetch(`/api/decisions/${decision.id}/mission`,{method:"POST"});
      const body=await response.json();
      if(!response.ok)throw new Error(body?.detail??"Could not create next mission");
      setDecision(current=>current?{...current,status:"accepted",next_mission_id:body.id}:current);
      setMessage("Next mission planned and persisted. It has not been executed.");
      await onMissionCreated(body.id);
    }catch(error){setMessage(error instanceof Error?error.message:"Could not create next mission")}
    finally{setBusy(false)}
  }

  if(!decision)return <section className="scientificDecisionPanel empty"><div><span className="labLabel">Scientific decision</span><h3>Convert synthesis into an explicit next action</h3><p>The mission has produced a cross-agent synthesis. Persist its recommendation as a reviewable decision before planning any follow-up work.</p></div><button disabled={busy} onClick={propose}>{busy?"Deriving…":"Derive Decision"}</button>{message&&<small>{message}</small>}</section>;

  return <section className="scientificDecisionPanel"><header><div><span className="labLabel">Scientific decision</span><h3>{humanize(decision.action_type)}</h3><p>Persisted from mission {decision.mission_id.slice(0,8)} · {decision.source_agent_ids.length} agents · {decision.evidence_ids.length} evidence links</p></div><div className="decisionConfidence"><span>{humanize(decision.priority)} priority</span><strong>{Math.round(decision.confidence*100)}%</strong><small>decision confidence</small></div></header><div className="decisionBody"><article><span>Why this action?</span><p>{decision.rationale}</p></article><article><span>Proposed next mission</span><strong>{decision.proposed_objective}</strong></article><article><span>Provenance</span><div className="decisionProvenance"><b>{decision.source_agent_ids.map(humanize).join(" · ")}</b><small>{decision.source_finding_ids.length} findings · {decision.evidence_ids.length} evidence links · decision {decision.id.slice(0,8)}</small></div></article></div><footer><p>{decision.next_mission_id?`Follow-up mission ${decision.next_mission_id.slice(0,8)} is planned but remains unexecuted.`:"Human approval boundary: creating the mission records the plan only. Execution remains a separate action."}</p>{decision.next_mission_id?<span className="decisionAccepted">Mission planned</span>:<button disabled={busy} onClick={createNextMission}>{busy?"Planning…":"Create Next Mission"}</button>}</footer>{message&&<small className="decisionMessage">{message}</small>}</section>;
}
