"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type MissionStep={id?:string;sequence?:number;position?:number;agent_id:string;task_type:string;status?:string;task_id?:string|null;finding_ids?:string[];error?:string|null};
type Mission={id:string;objective:string;status:string;created_at?:string;started_at?:string|null;completed_at?:string|null;steps?:MissionStep[];metadata?:Record<string,unknown>};

const DEFAULT_OBJECTIVE="Run a bounded scientific investigation: inspect evidence quality, analyze structure, identify opportunities, validate findings, and synthesize the next best action.";

function humanize(value:string){return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}
function tone(status:string){return status==="completed"?"completed":status==="failed"?"failed":status==="running"?"running":"planned"}

export default function InvestigationMissionActions({ investigationId }: { investigationId: string }) {
  const router=useRouter();
  const [missions,setMissions]=useState<Mission[]>([]);
  const [selected,setSelected]=useState<Mission|null>(null);
  const [objective,setObjective]=useState(DEFAULT_OBJECTIVE);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState<string|null>(null);
  const [showComposer,setShowComposer]=useState(false);

  async function load(){
    try{const r=await fetch(`/api/investigations/${investigationId}/missions`,{cache:"no-store"});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Could not load missions");const list=Array.isArray(b)?b:[];setMissions(list);if(list.length)setSelected(current=>list.find((m:Mission)=>m.id===current?.id)??list[0]);}
    catch(error){setMessage(error instanceof Error?error.message:"Could not load missions")}
  }
  useEffect(()=>{void load()},[investigationId]);

  async function createMission(){setBusy(true);setMessage(null);try{const r=await fetch(`/api/investigations/${investigationId}/missions`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({objective,metadata:{created_from:"mission_control"}})});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Mission creation failed");setSelected(b);setShowComposer(false);setMessage("Mission planned and recorded by the Kernel.");await load();router.refresh();}catch(error){setMessage(error instanceof Error?error.message:"Mission creation failed")}finally{setBusy(false)}}
  async function runMission(missionId:string){setBusy(true);setMessage(null);try{const r=await fetch(`/api/missions/${missionId}/run`,{method:"POST"});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Mission execution failed");setSelected(b);setMessage("Mission execution completed. Tasks and findings are now auditable.");await load();router.refresh();}catch(error){setMessage(error instanceof Error?error.message:"Mission execution failed")}finally{setBusy(false)}}

  const steps=selected?.steps??[];
  const completed=steps.filter(s=>s.status==="completed").length;

  return <div className="missionControl">
    <div className="missionControlTop">
      <div><span className="labLabel">Mission control</span><strong>{selected?selected.objective:"No persisted mission yet"}</strong><small>{selected?`${completed}/${steps.length} steps completed · ${humanize(selected.status)}`:"Plan a bounded, auditable investigation mission."}</small></div>
      <div className="missionControlButtons"><button onClick={()=>setShowComposer(v=>!v)} disabled={busy}>{showComposer?"Cancel":"New Mission"}</button>{selected&&<button className="missionPrimaryAction" disabled={busy||selected.status==="running"} onClick={()=>runMission(selected.id)}>{busy?"Running…":selected.status==="completed"?"Replay Mission":"Run Mission"}</button>}</div>
    </div>
    {showComposer&&<div className="missionComposer"><label>Scientific objective<textarea value={objective} onChange={e=>setObjective(e.target.value)} rows={3}/></label><div><span>The runtime will create the ordered agent plan. Agents remain bounded by their registered capabilities.</span><button className="missionPrimaryAction" disabled={busy||!objective.trim()} onClick={createMission}>{busy?"Planning…":"Create Mission"}</button></div></div>}
    {missions.length>0&&<div className="missionHistory"><span className="labLabel">Mission history</span><div>{missions.slice(0,6).map(m=><button key={m.id} className={selected?.id===m.id?"active":""} onClick={()=>setSelected(m)}><i className={tone(m.status)}/><span><strong>{m.objective}</strong><small>{humanize(m.status)}{m.created_at?` · ${new Date(m.created_at).toLocaleString()}`:""}</small></span></button>)}</div></div>}
    {selected&&<div className="missionPlan"><div className="missionPlanHead"><span className="labLabel">Execution plan</span><span>{steps.length} ordered steps · mission {selected.id.slice(0,8)}</span></div>{steps.length?steps.map((step,index)=><article key={step.id??`${step.agent_id}-${index}`} className={`missionStep ${tone(step.status??"planned")}`}><b>{step.sequence??step.position??index+1}</b><div><strong>{humanize(step.agent_id)}</strong><span>{humanize(step.task_type)}</span>{step.task_id&&<small>task {step.task_id.slice(0,8)}{step.finding_ids?.length?` · ${step.finding_ids.length} finding${step.finding_ids.length===1?"":"s"}`:""}</small>}{step.error&&<small>{step.error}</small>}</div><em>{humanize(step.status??"planned")}</em></article>):<p className="missionEmpty">Mission plan will appear here after creation.</p>}</div>}
    {message&&<p className="missionActionMessage">{message}</p>}
  </div>;
}
