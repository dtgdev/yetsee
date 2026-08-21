"use client";

import { useEffect, useState } from "react";

type Resolution={
  followup_mission_id:string;
  status:string;
  objective_satisfied:boolean;
  resolution_score:number;
  summary:string;
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function MissionScientificOutcome({investigationId,missionId,executionStatus}:{investigationId:string;missionId:string;executionStatus:string}){
  const [resolution,setResolution]=useState<Resolution|null>(null);

  useEffect(()=>{
    let active=true;
    async function load(){
      const response=await fetch(`/api/investigations/${investigationId}/resolutions`,{cache:"no-store"});
      if(!response.ok||!active)return;
      const body=await response.json();
      const items=Array.isArray(body)?body:[];
      setResolution(items.find((item:Resolution)=>item.followup_mission_id===missionId)??null);
    }
    void load();
    const refresh=()=>{if(document.visibilityState==="visible")void load()};
    window.addEventListener("focus",refresh);
    document.addEventListener("visibilitychange",refresh);
    return()=>{active=false;window.removeEventListener("focus",refresh);document.removeEventListener("visibilitychange",refresh)};
  },[investigationId,missionId]);

  if(executionStatus!=="completed")return null;

  const outcome=resolution?humanize(resolution.status):"Not Assessed";
  const objective=resolution?(resolution.objective_satisfied?"Objective satisfied":"Objective unresolved"):"Scientific outcome pending assessment";
  const interpretation=resolution?.summary??"Execution completed successfully. Scientific success is evaluated separately from step completion.";

  return <section className={`missionScientificOutcome ${resolution?.status??"pending"}`}>
    <div>
      <span>Execution</span>
      <strong>Completed</strong>
      <small>All bounded mission steps finished.</small>
    </div>
    <i aria-hidden="true">≠</i>
    <div>
      <span>Scientific outcome</span>
      <strong>{outcome}</strong>
      <small>{objective}</small>
    </div>
    <p>{interpretation}</p>
  </section>;
}
