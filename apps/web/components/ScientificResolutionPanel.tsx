"use client";

import { useEffect, useState } from "react";

type Snapshot={confidence:number;agreement_count:number;contradiction_count:number;evidence_gap_count:number;evidence_backed_count:number;finding_count:number;evidence_coverage:number;evidence_ids:string[]};
type Resolution={id:string;decision_id:string;parent_mission_id:string;followup_mission_id:string;status:string;objective_satisfied:boolean;resolution_score:number;summary:string;before_json:Snapshot;after_json:Snapshot;delta_json:Record<string,number>;evidence_added_ids:string[];evidence_removed_ids:string[]};

function humanize(value:string){return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}
function pct(value:number){return `${Math.round((value||0)*100)}%`}

export default function ScientificResolutionPanel({investigationId,decisionId,followupMissionId,followupStatus}:{investigationId:string;decisionId:string;followupMissionId:string;followupStatus?:string}){
  const [resolution,setResolution]=useState<Resolution|null>(null);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState<string|null>(null);

  async function load(){
    const response=await fetch(`/api/investigations/${investigationId}/resolutions`,{cache:"no-store"});
    if(!response.ok)return;
    const body=await response.json();
    const items=Array.isArray(body)?body:[];
    setResolution(items.find((item:Resolution)=>item.decision_id===decisionId)??null);
  }
  useEffect(()=>{void load()},[investigationId,decisionId]);

  async function assess(){
    setBusy(true);setMessage(null);
    try{
      const response=await fetch(`/api/decisions/${decisionId}/resolution`,{method:"POST"});
      const body=await response.json();
      if(!response.ok)throw new Error(body?.detail??"Could not assess scientific resolution");
      setResolution(body);
    }catch(error){setMessage(error instanceof Error?error.message:"Could not assess scientific resolution")}
    finally{setBusy(false)}
  }

  if(!resolution)return <section className="scientificResolutionPanel pending"><div><span className="labLabel">Closed-loop scientific resolution</span><h3>Did the follow-up mission resolve the uncertainty?</h3><p>Mission {followupMissionId.slice(0,8)} was created from this decision. Resolution compares its persisted synthesis with the parent mission rather than relying on a hidden model judgment.</p></div>{followupStatus==="completed"?<button disabled={busy} onClick={assess}>{busy?"Comparing…":"Assess Resolution"}</button>:<span className="resolutionWaiting">Follow-up {humanize(followupStatus??"pending")}</span>}{message&&<small>{message}</small>}</section>;

  const before=resolution.before_json, after=resolution.after_json;
  const rows=[
    ["Contradictions",before.contradiction_count,after.contradiction_count],
    ["Evidence gaps",before.evidence_gap_count,after.evidence_gap_count],
    ["Evidence coverage",pct(before.evidence_coverage),pct(after.evidence_coverage)],
    ["Synthesis confidence",pct(before.confidence),pct(after.confidence)],
  ];
  return <section className={`scientificResolutionPanel ${resolution.status}`}><header><div><span className="labLabel">Closed-loop scientific resolution</span><h3>{humanize(resolution.status)}</h3><p>Mission {resolution.parent_mission_id.slice(0,8)} → decision {resolution.decision_id.slice(0,8)} → mission {resolution.followup_mission_id.slice(0,8)}</p></div><div className="resolutionScore"><span>Objective</span><strong>{resolution.objective_satisfied?"Satisfied":"Unresolved"}</strong><small>delta score {resolution.resolution_score>0?"+":""}{resolution.resolution_score.toFixed(2)}</small></div></header><p className="resolutionSummary">{resolution.summary}</p><div className="resolutionComparison"><div className="resolutionComparisonHead"><span>Scientific signal</span><b>Before</b><b>After</b></div>{rows.map(([label,beforeValue,afterValue])=><div className="resolutionComparisonRow" key={String(label)}><span>{label}</span><b>{beforeValue}</b><strong>{afterValue}</strong></div>)}</div><footer><div><span>New evidence</span><strong>{resolution.evidence_added_ids.length}</strong><small>{resolution.evidence_added_ids.length?resolution.evidence_added_ids.map(id=>id.slice(0,8)).join(" · "):"No new evidence links"}</small></div><div><span>Scientific interpretation</span><strong>{resolution.objective_satisfied?"The decision objective was met.":resolution.status==="improved"?"Uncertainty decreased, but the objective remains open.":resolution.status==="worsened"?"The follow-up exposed additional uncertainty.":"The original uncertainty persists."}</strong></div></footer></section>;
}
