"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type MissionStep={id?:string;sequence?:number;position?:number;agent_id:string;task_type:string;status?:string;task_id?:string|null;finding_ids?:string[];error?:string|null};
type Mission={id:string;objective:string;status:string;created_at?:string;started_at?:string|null;finished_at?:string|null;completed_at?:string|null;error?:string|null;steps?:MissionStep[];metadata?:Record<string,unknown>};
type MissionDetail={mission?:Mission;steps?:MissionStep[]};

const DEFAULT_OBJECTIVE="Run a bounded scientific investigation: inspect evidence quality, analyze structure, identify opportunities, validate findings, and synthesize the next best action.";

function humanize(value:string){return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}
function tone(status:string){return status==="completed"?"completed":status==="failed"?"failed":status==="running"?"running":"planned"}
function normalizeDetail(body:MissionDetail|Mission):Mission{
  if("mission" in body&&body.mission)return {...body.mission,steps:Array.isArray(body.steps)?body.steps:body.mission.steps??[]};
  return body as Mission;
}

export default function InvestigationMissionActions({ investigationId }: { investigationId: string }) {
  const router=useRouter();
  const [missions,setMissions]=useState<Mission[]>([]);
  const [selected,setSelected]=useState<Mission|null>(null);
  const [objective,setObjective]=useState(DEFAULT_OBJECTIVE);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState<string|null>(null);
  const [showComposer,setShowComposer]=useState(false);

  async function hydrateMission(mission:Mission){
    const r=await fetch(`/api/missions/${mission.id}`,{cache:"no-store"});
    const b=await r.json();
    if(!r.ok)throw new Error(b?.detail??"Could not load mission plan");
    return normalizeDetail(b);
  }

  async function load(preferredId?:string){
    try{
      const r=await fetch(`/api/investigations/${investigationId}/missions`,{cache:"no-store"});
      const b=await r.json();
      if(!r.ok)throw new Error(b?.detail??"Could not load missions");
      const list=Array.isArray(b)?b:[];
      setMissions(list);
      if(!list.length){setSelected(null);return;}
      const target=list.find((m:Mission)=>m.id===(preferredId??selected?.id))??list[0];
      setSelected(await hydrateMission(target));
    }catch(error){setMessage(error instanceof Error?error.message:"Could not load missions")}
  }
  useEffect(()=>{void load()},[investigationId]);

  async function selectMission(mission:Mission){setMessage(null);try{setSelected(await hydrateMission(mission))}catch(error){setMessage(error instanceof Error?error.message:"Could not load mission")}}
  async function createMission(){setBusy(true);setMessage(null);try{const r=await fetch(`/api/investigations/${investigationId}/missions`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({objective,metadata:{created_from:"mission_control"}})});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Mission creation failed");const mission=normalizeDetail(b);setShowComposer(false);setMessage("Mission planned and recorded by the Kernel.");await load(mission.id);router.refresh();}catch(error){setMessage(error instanceof Error?error.message:"Mission creation failed")}finally{setBusy(false)}}
  async function runMission(missionId:string){setBusy(true);setMessage(null);try{const r=await fetch(`/api/missions/${missionId}/run`,{method:"POST"});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Mission execution failed");const mission=normalizeDetail(b);setSelected(mission);setMessage(mission.status==="completed"?"Mission completed. Every step is linked to its audited task and findings.":`Mission ended with status ${humanize(mission.status)}.`);await load(mission.id);router.refresh();}catch(error){setMessage(error instanceof Error?error.message:"Mission execution failed")}finally{setBusy(false)}}

  const steps=selected?.steps??[];
  const completed=steps.filter(s=>s.status==="completed").length;
  const currentStep=steps.find(s=>s.status==="running")??steps.find(s=>s.status!=="completed")??steps.at(-1);
  const progress=steps.length?Math.round((completed/steps.length)*100):0;
  const totalFindings=useMemo(()=>steps.reduce((sum,step)=>sum+(step.finding_ids?.length??0),0),[steps]);

  return <div className="missionControlConsole">
    <div className="missionConsoleHeader">
      <div className="missionIdentity"><span className="labLabel">Mission control</span><div className="missionTitleRow"><h3>{selected?selected.objective:"Plan the next scientific mission"}</h3>{selected&&<span className={`missionStatus ${tone(selected.status)}`}>{humanize(selected.status)}</span>}</div><p>{selected?"A bounded, ordered investigation executed by registered agents and recorded by the Kernel.":"Create a persisted objective and let the mission runtime generate the auditable execution plan."}</p></div>
      <div className="missionConsoleActions"><button onClick={()=>setShowComposer(v=>!v)} disabled={busy}>{showComposer?"Cancel":"New Mission"}</button>{selected&&<button className="missionPrimaryAction" disabled={busy||selected.status==="running"} onClick={()=>runMission(selected.id)}>{busy?"Running…":selected.status==="completed"?"Replay Mission":"Run Mission"}</button>}</div>
    </div>

    {showComposer&&<div className="missionComposer"><label><span>Scientific objective</span><textarea value={objective} onChange={e=>setObjective(e.target.value)} rows={3}/></label><div><small>The runtime creates the ordered agent plan. Agents remain bounded by registered capabilities and every action is Kernel-recorded.</small><button className="missionPrimaryAction" disabled={busy||!objective.trim()} onClick={createMission}>{busy?"Planning…":"Create Mission"}</button></div></div>}

    {selected&&<>
      <div className="missionProgressBand"><div><span>Mission progress</span><strong>{completed} / {steps.length}</strong><small>steps completed</small></div><div className="missionProgressTrack"><i style={{width:`${progress}%`}}/></div><div className="missionProgressMeta"><span>{progress}%</span><small>{selected.id.slice(0,8)} · {totalFindings} findings</small></div></div>
      <div className="missionStepRail">{steps.length?steps.map((step,index)=><button key={step.id??`${step.agent_id}-${index}`} className={`missionRailStep ${tone(step.status??"pending")}`} title={humanize(step.task_type)}><i>{step.status==="completed"?"✓":step.status==="failed"?"!":step.sequence??index+1}</i><span><strong>{humanize(step.agent_id)}</strong><small>{humanize(step.status??"pending")}</small></span></button>):<div className="missionPlanLoading"><strong>Execution plan unavailable</strong><span>The mission exists, but its ordered steps could not be loaded.</span></div>}</div>
      <div className="missionConsoleLower">
        <section className="missionCurrentStep"><span className="labLabel">{selected.status==="completed"?"Final step":"Current step"}</span>{currentStep?<><div className="missionCurrentHead"><b>{currentStep.sequence??currentStep.position??1}</b><div><h4>{humanize(currentStep.agent_id)}</h4><p>{humanize(currentStep.task_type)}</p></div><span className={`missionStatus ${tone(currentStep.status??"pending")}`}>{humanize(currentStep.status??"pending")}</span></div><div className="missionStepEvidence"><div><span>Task</span><strong>{currentStep.task_id?currentStep.task_id.slice(0,8):"Not created"}</strong></div><div><span>Findings</span><strong>{currentStep.finding_ids?.length??0}</strong></div><div><span>Kernel state</span><strong>{currentStep.task_id?"Recorded":"Pending"}</strong></div></div>{currentStep.error&&<p className="missionStepError">{currentStep.error}</p>}</>:<p className="missionEmpty">No mission step selected.</p>}</section>
        <section className="missionHistoryPanel"><div className="missionHistoryHead"><span className="labLabel">Mission history</span><small>{missions.length} persisted</small></div><div className="missionHistoryList">{missions.slice(0,5).map(m=><button key={m.id} className={selected.id===m.id?"active":""} onClick={()=>void selectMission(m)}><i className={tone(m.status)}/><span><strong>{m.objective}</strong><small>{humanize(m.status)}{m.created_at?` · ${new Date(m.created_at).toLocaleString()}`:""}</small></span><em>{m.id.slice(0,8)}</em></button>)}</div></section>
      </div>
    </>}
    {!selected&&!showComposer&&<div className="missionZeroState"><strong>No persisted mission yet</strong><p>Create a scientific objective to generate an ordered, auditable agent plan.</p></div>}
    {message&&<p className="missionActionMessage">{message}</p>}
  </div>;
}
