"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import GalileoGraph from "./GalileoGraph";

type MissionStep={id?:string;sequence?:number;position?:number;agent_id:string;task_type:string;status?:string;task_id?:string|null;finding_ids?:string[];error?:string|null};
type Mission={id:string;objective:string;status:string;created_at?:string;started_at?:string|null;finished_at?:string|null;completed_at?:string|null;error?:string|null;steps?:MissionStep[];metadata?:Record<string,unknown>};
type MissionDetail={mission?:Mission;steps?:MissionStep[]};
type SynthesisLink={evidence_id:string;agent_ids:string[];finding_ids:string[];stances:string[]};
type SynthesisGap={finding_id:string;agent_id:string;title:string;stance:string;confidence:number};
type CrossAgentSynthesis={finding_count:number;agent_count:number;agent_ids:string[];supporting_count:number;critical_count:number;neutral_count:number;evidence_backed_count:number;evidence_gap_count:number;evidence_ids:string[];agreement_count:number;contradiction_count:number;agreements:SynthesisLink[];contradictions:SynthesisLink[];evidence_gaps:SynthesisGap[];source_findings:{finding_id:string;agent_id:string;category:string;stance:string;confidence:number;evidence_ids:string[];title:string}[]};
type AgentFinding={id:string;agent_id:string;category?:string;title:string;detail:string;confidence:number;severity:string;stance:string;evidence_ids:string[];metadata_json?:{synthesis_type?:string;recommendation?:string;mission_id?:string;synthesis?:CrossAgentSynthesis}&Record<string,unknown>};
type GraphNode={id:string;domain_id:string;kind:string;label:string;description?:string|null;confidence:number;evidence_count:number;source_count:number;degree:number;degree_centrality:number;metadata:Record<string,unknown>};
type GraphData={investigation:{id:string;title:string;status:string};nodes:GraphNode[];edges:{id:string;source:string;target:string;kind:string;confidence:number;evidence_ids:string[];metadata:Record<string,unknown>}[];metrics:{nodes:number;edges:number;entities:number;observations:number;hypotheses:number;independent_sources:number;sources:string[];connected_components:number;density:number;relationship_types:Record<string,number>};analytics?:Record<string,unknown>;generated_at:string;derived:boolean;scope?:Record<string,unknown>};

const DEFAULT_OBJECTIVE="Run a bounded scientific investigation: inspect evidence quality, analyze structure, identify opportunities, validate findings, and synthesize the next best action.";

function humanize(value:string){return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}
function tone(status:string){return status==="completed"?"completed":status==="failed"?"failed":status==="running"?"running":"planned"}
function normalizeDetail(body:MissionDetail|Mission):Mission{if("mission" in body&&body.mission)return {...body.mission,steps:Array.isArray(body.steps)?body.steps:body.mission.steps??[]};return body as Mission}

export default function InvestigationMissionActions({ investigationId }: { investigationId: string }) {
  const router=useRouter();
  const [missions,setMissions]=useState<Mission[]>([]);
  const [selected,setSelected]=useState<Mission|null>(null);
  const [selectedStepId,setSelectedStepId]=useState<string|null>(null);
  const [selectedFindingId,setSelectedFindingId]=useState<string|null>(null);
  const [objective,setObjective]=useState(DEFAULT_OBJECTIVE);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState<string|null>(null);
  const [showComposer,setShowComposer]=useState(false);
  const [graph,setGraph]=useState<GraphData|null>(null);
  const [focusedGraph,setFocusedGraph]=useState<GraphData|null>(null);
  const [findings,setFindings]=useState<AgentFinding[]>([]);
  const [projectionLoading,setProjectionLoading]=useState(false);
  const [projectionError,setProjectionError]=useState<string|null>(null);

  async function hydrateMission(mission:Mission){const r=await fetch(`/api/missions/${mission.id}`,{cache:"no-store"});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Could not load mission plan");return normalizeDetail(b)}
  async function loadScienceContext(){try{const [graphResponse,findingResponse]=await Promise.all([fetch(`/api/investigations/${investigationId}/graph`,{cache:"no-store"}),fetch(`/api/investigations/${investigationId}/agent-findings`,{cache:"no-store"})]);if(graphResponse.ok){const body=await graphResponse.json();setGraph(body);setFocusedGraph(body)}if(findingResponse.ok){const body=await findingResponse.json();setFindings(Array.isArray(body)?body:[])}}catch(error){setProjectionError(error instanceof Error?error.message:"Could not load scientific graph context")}}
  async function load(preferredId?:string){try{const r=await fetch(`/api/investigations/${investigationId}/missions`,{cache:"no-store"});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Could not load missions");const list=Array.isArray(b)?b:[];setMissions(list);if(!list.length){setSelected(null);setSelectedStepId(null);setSelectedFindingId(null);return}const target=list.find((m:Mission)=>m.id===(preferredId??selected?.id))??list[0];const detail=await hydrateMission(target);setSelected(detail);const detailSteps=detail.steps??[];const defaultStep=detailSteps.find(s=>s.status==="running")??detailSteps.at(-1)??detailSteps[0];setSelectedStepId(defaultStep?.id??(defaultStep?`${defaultStep.agent_id}-${defaultStep.sequence??defaultStep.position??0}`:null));setSelectedFindingId(null)}catch(error){setMessage(error instanceof Error?error.message:"Could not load missions")}}
  useEffect(()=>{void load();void loadScienceContext()},[investigationId]);

  async function selectMission(mission:Mission){setMessage(null);try{const detail=await hydrateMission(mission);setSelected(detail);const first=detail.steps?.at(-1)??detail.steps?.[0];setSelectedStepId(first?.id??(first?`${first.agent_id}-${first.sequence??first.position??0}`:null));setSelectedFindingId(null)}catch(error){setMessage(error instanceof Error?error.message:"Could not load mission")}}
  async function createMission(){setBusy(true);setMessage(null);try{const r=await fetch(`/api/investigations/${investigationId}/missions`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({objective,metadata:{created_from:"mission_control"}})});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Mission creation failed");const mission=normalizeDetail(b);setShowComposer(false);setMessage("Mission planned and recorded by the Kernel.");await load(mission.id);await loadScienceContext();router.refresh()}catch(error){setMessage(error instanceof Error?error.message:"Mission creation failed")}finally{setBusy(false)}}
  async function runMission(missionId:string){setBusy(true);setMessage(null);try{const r=await fetch(`/api/missions/${missionId}/run`,{method:"POST"});const b=await r.json();if(!r.ok)throw new Error(b?.detail??"Mission execution failed");const mission=normalizeDetail(b);setSelected(mission);setSelectedFindingId(null);setMessage(mission.status==="completed"?"Mission completed. Every step is linked to its audited task and findings.":`Mission ended with status ${humanize(mission.status)}.`);await load(mission.id);await loadScienceContext();router.refresh()}catch(error){setMessage(error instanceof Error?error.message:"Mission execution failed")}finally{setBusy(false)}}

  const steps=selected?.steps??[];
  const completed=steps.filter(s=>s.status==="completed").length;
  const currentStep=steps.find(s=>s.status==="running")??steps.find(s=>s.status!=="completed")??steps.at(-1);
  const progress=steps.length?Math.round((completed/steps.length)*100):0;
  const totalFindings=useMemo(()=>steps.reduce((sum,step)=>sum+(step.finding_ids?.length??0),0),[steps]);
  const selectedStep=steps.find((step,index)=>(step.id??`${step.agent_id}-${step.sequence??step.position??index}`)===selectedStepId)??currentStep;
  const selectedFindings=useMemo(()=>{const ids=new Set(selectedStep?.finding_ids??[]);return findings.filter(f=>ids.has(f.id))},[findings,selectedStepId,selectedStep?.finding_ids]);
  const selectedFinding=selectedFindings.find(f=>f.id===selectedFindingId)??null;
  const scopedFindings=selectedFinding?[selectedFinding]:selectedFindings;
  const selectedEvidenceIds=useMemo(()=>[...new Set(scopedFindings.flatMap(f=>f.evidence_ids??[]))].sort(),[selectedFindingId,selectedFindings]);
  const evidenceKey=selectedEvidenceIds.join(",");
  const selectedFindingHasNoEvidence=Boolean(selectedFinding&&selectedFinding.evidence_ids.length===0);

  const synthesisFinding=useMemo(()=>{
    const finalStep=steps.find(step=>step.agent_id==="investigation_agent");
    const ids=new Set(finalStep?.finding_ids??[]);
    return findings.find(f=>ids.has(f.id)&&f.category==="investigation_synthesis"&&f.metadata_json?.synthesis_type==="cross_agent")??null;
  },[findings,steps]);
  const synthesis=synthesisFinding?.metadata_json?.synthesis;
  const recommendation=synthesisFinding?.metadata_json?.recommendation;

  useEffect(()=>{
    let cancelled=false;
    async function loadProjection(){
      if(!graph||!selectedStep){if(!cancelled)setFocusedGraph(graph);return}
      if(!selectedEvidenceIds.length){if(!cancelled){setFocusedGraph(graph);setProjectionError(null);setProjectionLoading(false)}return}
      setProjectionLoading(true);setProjectionError(null);
      try{
        const response=await fetch(`/api/investigations/${investigationId}/graph/project`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({evidence_ids:selectedEvidenceIds}),cache:"no-store"});
        const body=await response.json();
        if(!response.ok)throw new Error(body?.detail??"Could not compute evidence-scoped graph projection");
        if(!cancelled)setFocusedGraph(body);
      }catch(error){if(!cancelled){setFocusedGraph(graph);setProjectionError(error instanceof Error?error.message:"Could not compute evidence-scoped graph projection")}}
      finally{if(!cancelled)setProjectionLoading(false)}
    }
    void loadProjection();
    return()=>{cancelled=true};
  },[investigationId,graph,selectedStepId,selectedFindingId,evidenceKey]);

  function chooseStep(key:string){setSelectedStepId(key);setSelectedFindingId(null)}
  function focusFinding(findingId:string){const stepIndex=steps.findIndex(step=>(step.finding_ids??[]).includes(findingId));if(stepIndex<0)return;const step=steps[stepIndex];setSelectedStepId(step.id??`${step.agent_id}-${step.sequence??step.position??stepIndex}`);setSelectedFindingId(findingId);setTimeout(()=>document.querySelector(".missionGraphFocus")?.scrollIntoView({behavior:"smooth",block:"start"}),0)}

  return <div className="missionGraphWorkspace">
    <div className="missionControlConsole">
      <div className="missionConsoleHeader"><div className="missionIdentity"><span className="labLabel">Mission control</span><div className="missionTitleRow"><h3>{selected?selected.objective:"Plan the next scientific mission"}</h3>{selected&&<span className={`missionStatus ${tone(selected.status)}`}>{humanize(selected.status)}</span>}</div><p>{selected?"A bounded, ordered investigation executed by registered agents and recorded by the Kernel.":"Create a persisted objective and let the mission runtime generate the auditable execution plan."}</p></div><div className="missionConsoleActions"><button onClick={()=>setShowComposer(v=>!v)} disabled={busy}>{showComposer?"Cancel":"New Mission"}</button>{selected&&<button className="missionPrimaryAction" disabled={busy||selected.status==="running"} onClick={()=>runMission(selected.id)}>{busy?"Running…":selected.status==="completed"?"Replay Mission":"Run Mission"}</button>}</div></div>
      {showComposer&&<div className="missionComposer"><label><span>Scientific objective</span><textarea value={objective} onChange={e=>setObjective(e.target.value)} rows={3}/></label><div><small>The runtime creates the ordered agent plan. Agents remain bounded by registered capabilities and every action is Kernel-recorded.</small><button className="missionPrimaryAction" disabled={busy||!objective.trim()} onClick={createMission}>{busy?"Planning…":"Create Mission"}</button></div></div>}
      {selected&&<><div className="missionProgressBand"><div><span>Mission progress</span><strong>{completed} / {steps.length}</strong><small>steps completed</small></div><div className="missionProgressTrack"><i style={{width:`${progress}%`}}/></div><div className="missionProgressMeta"><span>{progress}%</span><small>{selected.id.slice(0,8)} · {totalFindings} findings</small></div></div><div className="missionStepRail">{steps.length?steps.map((step,index)=>{const key=step.id??`${step.agent_id}-${step.sequence??step.position??index}`;return <button key={key} className={`missionRailStep ${tone(step.status??"pending")} ${key===selectedStepId?"selected":""}`} title={`Inspect ${humanize(step.agent_id)} on the canonical graph`} onClick={()=>chooseStep(key)}><i>{step.status==="completed"?"✓":step.status==="failed"?"!":step.sequence??index+1}</i><span><strong>{humanize(step.agent_id)}</strong><small>{humanize(step.status??"pending")}</small></span></button>}):<div className="missionPlanLoading"><strong>Execution plan unavailable</strong><span>The mission exists, but its ordered steps could not be loaded.</span></div>}</div><div className="missionConsoleLower"><section className="missionCurrentStep"><span className="labLabel">Selected graph step</span>{selectedStep?<><div className="missionCurrentHead"><b>{selectedStep.sequence??selectedStep.position??1}</b><div><h4>{humanize(selectedStep.agent_id)}</h4><p>{humanize(selectedStep.task_type)}</p></div><span className={`missionStatus ${tone(selectedStep.status??"pending")}`}>{humanize(selectedStep.status??"pending")}</span></div><div className="missionStepEvidence"><div><span>Task</span><strong>{selectedStep.task_id?selectedStep.task_id.slice(0,8):"Not created"}</strong></div><div><span>Findings</span><strong>{selectedStep.finding_ids?.length??0}</strong></div><div><span>Evidence links</span><strong>{selectedEvidenceIds.length}</strong></div></div>{selectedStep.error&&<p className="missionStepError">{selectedStep.error}</p>}</>:<p className="missionEmpty">No mission step selected.</p>}</section><section className="missionHistoryPanel"><div className="missionHistoryHead"><span className="labLabel">Mission history</span><small>{missions.length} persisted</small></div><div className="missionHistoryList">{missions.slice(0,5).map(m=><button key={m.id} className={selected.id===m.id?"active":""} onClick={()=>void selectMission(m)}><i className={tone(m.status)}/><span><strong>{m.objective}</strong><small>{humanize(m.status)}{m.created_at?` · ${new Date(m.created_at).toLocaleString()}`:""}</small></span><em>{m.id.slice(0,8)}</em></button>)}</div></section></div></>}
      {!selected&&!showComposer&&<div className="missionZeroState"><strong>No persisted mission yet</strong><p>Create a scientific objective to generate an ordered, auditable agent plan.</p></div>}
      {message&&<p className="missionActionMessage">{message}</p>}
    </div>

    {synthesis&&<section className="crossAgentSynthesis"><header><div><span className="labLabel">Cross-agent scientific synthesis</span><h3>What does the investigation team collectively say?</h3><p>{synthesis.agent_count} specialist agents · {synthesis.finding_count} source findings · {synthesis.evidence_ids.length} linked evidence</p></div><div className={`synthesisRecommendation ${recommendation??""}`}><span>Recommended next action</span><strong>{humanize(recommendation??"review_synthesis")}</strong></div></header><div className="synthesisSummaryGrid"><article className="consensus"><span>Consensus</span><strong>{synthesis.agreement_count}</strong><small>shared-evidence agreement{synthesis.agreement_count===1?"":"s"}</small></article><article className="disagreement"><span>Disagreement</span><strong>{synthesis.contradiction_count}</strong><small>shared-evidence contradiction{synthesis.contradiction_count===1?"":"s"}</small></article><article className="gaps"><span>Evidence gaps</span><strong>{synthesis.evidence_gap_count}</strong><small>finding{synthesis.evidence_gap_count===1?"":"s"} without direct evidence</small></article><article><span>Evidence backed</span><strong>{synthesis.evidence_backed_count}</strong><small>of {synthesis.finding_count} specialist findings</small></article></div><div className="synthesisColumns"><section><div className="synthesisColumnHead"><span>Consensus</span><em>{synthesis.agreements.length}</em></div>{synthesis.agreements.length?synthesis.agreements.map(item=><button key={`a-${item.evidence_id}`} onClick={()=>item.finding_ids[0]&&focusFinding(item.finding_ids[0])}><strong>{item.agent_ids.map(humanize).join(" + ")}</strong><span>{item.stances.map(humanize).join(" · ")}</span><small>Evidence {item.evidence_id.slice(0,8)} · {item.finding_ids.length} findings → inspect provenance</small></button>):<p className="synthesisEmpty">No shared-evidence consensus detected yet.</p>}</section><section><div className="synthesisColumnHead"><span>Disagreement</span><em>{synthesis.contradictions.length}</em></div>{synthesis.contradictions.length?synthesis.contradictions.map(item=><button className="critical" key={`c-${item.evidence_id}`} onClick={()=>item.finding_ids[0]&&focusFinding(item.finding_ids[0])}><strong>{item.agent_ids.map(humanize).join(" ↔ ")}</strong><span>{item.stances.map(humanize).join(" vs ")}</span><small>Evidence {item.evidence_id.slice(0,8)} · inspect conflicting provenance</small></button>):<p className="synthesisEmpty">No explicit shared-evidence contradictions detected.</p>}</section><section><div className="synthesisColumnHead"><span>Evidence gaps</span><em>{synthesis.evidence_gaps.length}</em></div>{synthesis.evidence_gaps.length?synthesis.evidence_gaps.map(gap=><button className="gap" key={gap.finding_id} onClick={()=>focusFinding(gap.finding_id)}><strong>{gap.title}</strong><span>{humanize(gap.agent_id)} · {humanize(gap.stance)}</span><small>{Math.round(gap.confidence*100)}% confidence · no direct evidence → inspect finding</small></button>):<p className="synthesisEmpty">Every specialist finding has direct evidence attached.</p>}</section></div></section>}

    {focusedGraph&&selectedStep&&<section className="missionGraphFocus"><div className="missionGraphFocusHeader"><div><span className="labLabel">{selectedFindingHasNoEvidence?"Mission → canonical context":"Mission → canonical graph"}</span><h3>{selectedFinding?selectedFinding.title:`${humanize(selectedStep.agent_id)} evidence footprint`}</h3><p>{projectionLoading?"Recomputing graph analytics for this evidence scope…":projectionError?`Projection unavailable; showing canonical graph fallback. ${projectionError}`:selectedFindingHasNoEvidence?"No direct evidence is attached to this finding. The canonical investigation graph is shown for scientific context, not as evidence supporting the finding.":selectedFinding?`Finding-level projection: ${selectedFinding.evidence_ids.length} evidence link(s), ${Math.round(selectedFinding.confidence*100)}% confidence, ${humanize(selectedFinding.stance)} stance.`:selectedEvidenceIds.length?`Showing a backend-recomputed graph projection backed by ${selectedEvidenceIds.length} evidence link(s) referenced by this step's ${selectedFindings.length} finding(s).`:"This step has no explicit evidence-linked findings yet, so the full canonical investigation graph remains visible."}</p></div><div className="missionGraphFocusStats"><span><b>{scopedFindings.length}</b> findings</span><span><b>{selectedEvidenceIds.length}</b> evidence</span><span><b>{focusedGraph.nodes.length}</b> nodes</span><span><b>{focusedGraph.edges.length}</b> edges</span></div></div>
      {selectedFindingHasNoEvidence&&<div className="missionNoEvidenceContext"><strong>No direct evidence attached</strong><span>Finding</span><i>→</i><span>No direct evidence</span><i>→</i><span>Canonical context</span><p>The graph below provides investigation context only. It should not be interpreted as evidence supporting this selected finding.</p></div>}
      {selectedFindings.length>0&&<div className="missionFindingProvenance"><div className="missionFindingHead"><div><span className="labLabel">Finding provenance</span><strong>{selectedFinding?"One finding selected":"All findings in this agent step"}</strong></div>{selectedFinding&&<button onClick={()=>setSelectedFindingId(null)}>Show all step findings</button>}</div><div className="missionFindingList">{selectedFindings.map(finding=><button key={finding.id} className={finding.id===selectedFindingId?"selected":""} onClick={()=>setSelectedFindingId(finding.id)}><span className="missionFindingTone">{humanize(finding.stance)}</span><strong>{finding.title}</strong><p>{finding.detail}</p><small>{finding.evidence_ids.length} evidence · {Math.round(finding.confidence*100)}% confidence · {humanize(finding.severity)}</small></button>)}</div></div>}
      <GalileoGraph graph={focusedGraph as any}/></section>}
  </div>;
}
