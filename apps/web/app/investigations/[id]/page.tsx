import Link from "next/link";
import { apiGet } from "../../../lib/api";
import InvestigationAgentActions from "../../../components/InvestigationAgentActions";
import { RunGraphReasoner } from "../../../components/ReasoningActions";
import ReasoningGraph from "../../../components/ReasoningGraph";
import GalileoGraph from "../../../components/GalileoGraph";
import { StudioFrame } from "../../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../../components/ResearchWorkspace";

export const dynamic = "force-dynamic";

type Observation = { id:string; source:string; source_ref:string; topic:string; metric:string; value:number|null; observed_at:string; payload:Record<string,unknown> };
type Hypothesis = { id:string; title:string; description:string|null; status:string; prior_confidence:number; confidence:number };
type Workspace = {
  investigation:{id:string;title:string;status:string;confidence:number;summary:string|null;slug?:string};
  lifecycle:{current:string;allowed_transitions:string[]};
  hypotheses:Hypothesis[];
  hypothesis_evidence:{id:string;hypothesis_id:string;observation_id:string;stance:string;weight:number;rationale:string|null}[];
  confidence_history:{id:string;hypothesis_id:string;old_confidence:number;new_confidence:number;supporting_weight:number;contradicting_weight:number;neutral_weight:number;reason:string;trigger:string;created_at:string}[];
  evidence:{id:string;observation_id:string|null;stance:string;weight:number}[];
  observations:Observation[];
  timeline:{id:string;event_type:string;sequence:number;payload:Record<string,unknown>;occurred_at:string}[];
  revisions:{id:string;revision_number:number;change_type:string;message:string;created_at:string}[];
  agent_findings:{id:string;agent_id:string;category:string;severity:string;stance:string;confidence:number;title:string;detail:string;evidence_ids:string[];metadata_json:Record<string,unknown>;created_at:string}[];
  agent_tasks:{id:string;agent_id:string;task_type:string;status:string;result_json:Record<string,unknown>;created_at:string}[];
};
type Command = {id:string;command_type:string;aggregate_id:string|null;correlation_id:string;causation_id:string|null;status:string;requested_at:string};
type Entity = {id:string;canonical_name:string;kind:string};
type Relationship = {id:string;source_entity_id:string;target_entity_id:string;kind:string;confidence:number;evidence_ids:string[]};
type ReasoningResult = {id:string;run_id:string;investigation_id:string;reasoner_id:string;conclusion:string;confidence:number;support_level:string;supporting_factors:any[];contradicting_factors:any[];assumptions:string[];limitations:string[];recommended_evidence:string[];metrics:Record<string,any>;evidence_ids:string[];explanation:string;created_at:string};
type ReasoningRun = {id:string;reasoner_id:string;status:string;started_at:string|null;finished_at:string|null;created_at:string};
type Manifest = {id:string;name:string;version:string;scientific_question:string;deterministic:boolean};
type InvestigationGraph = {
  investigation:{id:string;title:string;status:string};
  nodes:{id:string;domain_id:string;kind:string;label:string;description?:string|null;confidence:number;evidence_count:number;source_count:number;degree:number;degree_centrality:number;metadata:Record<string,any>}[];
  edges:{id:string;source:string;target:string;kind:string;confidence:number;evidence_ids:string[];metadata:Record<string,any>}[];
  metrics:{nodes:number;edges:number;entities:number;observations:number;hypotheses:number;independent_sources:number;sources:string[];connected_components:number;density:number;relationship_types:Record<string,number>};
  generated_at:string;derived:boolean;
};

type Lens = "overview"|"evidence"|"structure"|"reasoning"|"history"|"compare";
const lenses:{id:Lens;label:string;question:string}[] = [
  {id:"overview",label:"Overview",question:"What is happening?"},
  {id:"evidence",label:"Evidence",question:"What supports or contradicts this?"},
  {id:"structure",label:"Structure",question:"How is everything connected?"},
  {id:"reasoning",label:"Reasoning",question:"What does the evidence imply?"},
  {id:"history",label:"History",question:"How has understanding evolved?"},
  {id:"compare",label:"Compare",question:"Where do models agree or disagree?"},
];

async function safe<T>(path:string, fallback:T){try{return await apiGet<T>(path)}catch{return fallback}}
const pct=(n:number)=>`${Math.round(n*100)}%`;
const val=(v:number|null)=>v===null?"—":Number.isInteger(v)?v.toFixed(0):v.toFixed(2);
const fmt=(d:string|undefined|null)=>d?new Date(d).toLocaleString():"—";

function WorkspaceNav({id,active}:{id:string;active:Lens}){
  return <nav className="investigationLensNav" aria-label="Investigation lenses">
    {lenses.map(l=><Link key={l.id} className={active===l.id?"active":""} href={`/investigations/${id}?lens=${l.id}`}><strong>{l.label}</strong><small>{l.question}</small></Link>)}
    <span className="futureLens"><strong>Forecast</strong><small>What is likely next?</small></span>
    <span className="futureLens"><strong>Simulation</strong><small>What if conditions change?</small></span>
  </nav>
}

function ObservationTable({w}:{w:Workspace}){
  return <div className="observationTableV2"><div className="tableHeader"><span>Observed</span><span>Source</span><span>Metric</span><span>Value</span></div>{w.observations.map(o=>{const h=w.hypothesis_evidence.find(e=>e.observation_id===o.id);const ie=w.evidence.find(e=>e.observation_id===o.id);const stance=h?.stance??ie?.stance??"unclassified";return <div className="tableRow" key={o.id}><span>{new Date(o.observed_at).toLocaleString()}</span><div><StatusPill tone={o.source==="google_trends"?"green":"blue"}>{o.source}</StatusPill></div><div><strong>{o.metric}</strong><small>{o.topic} · {stance}</small></div><b>{val(o.value)}</b></div>})}</div>
}

export default async function Page({params,searchParams}:{params:Promise<{id:string}>;searchParams:Promise<{lens?:string}>}){
  const {id}=await params;
  const query=await searchParams;
  const active=(lenses.some(l=>l.id===query.lens)?query.lens:"overview") as Lens;
  const [w,allCommands,reasoningResults,reasoningRuns,reasoners,entities,relationships,investigationGraph]=await Promise.all([
    apiGet<Workspace>(`/api/v1/investigations/${id}/workspace`),
    safe<Command[]>("/api/v1/kernel/commands?limit=150",[]),
    safe<ReasoningResult[]>(`/api/v1/investigations/${id}/reasoning/results`,[]),
    safe<ReasoningRun[]>(`/api/v1/investigations/${id}/reasoning/runs`,[]),
    safe<Manifest[]>("/api/v1/reasoners",[]),
    safe<Entity[]>("/api/v1/graph/entities?limit=120",[]),
    safe<Relationship[]>("/api/v1/graph/relationships?limit=180",[]),
    safe<InvestigationGraph>(`/api/v1/investigations/${id}/graph`,{investigation:{id,title:"",status:""},nodes:[],edges:[],metrics:{nodes:0,edges:0,entities:0,observations:0,hypotheses:0,independent_sources:0,sources:[],connected_components:0,density:0,relationship_types:{}},generated_at:"",derived:true}),
  ]);

  const inv=w.investigation;
  const commands=allCommands.filter(c=>c.aggregate_id===id);
  const sources=[...new Set(w.observations.map(o=>o.source))];
  const primary=w.hypotheses[0];
  const supporting=w.hypothesis_evidence.filter(e=>e.stance==="supporting");
  const contradicting=w.hypothesis_evidence.filter(e=>e.stance==="contradicting");
  const neutral=w.hypothesis_evidence.filter(e=>e.stance==="neutral");
  const latestReasoning=reasoningResults[0];
  const graphManifest=reasoners.find(r=>r.id==="graph");
  const evidenceSet=new Set(latestReasoning?.evidence_ids??w.observations.map(o=>o.id));
  const relevantRelationships=relationships.filter(r=>r.evidence_ids.some(eid=>evidenceSet.has(eid)));
  const relevantEntityIds=new Set(relevantRelationships.flatMap(r=>[r.source_entity_id,r.target_entity_id]));
  const relevantEntities=entities.filter(e=>relevantEntityIds.has(e.id));
  const latestFindings=w.agent_findings.slice(0,6);
  const currentConfidence=primary?.confidence??inv.confidence;

  const commonHeader=<>
    <div className="investigationContextStrip">
      <div><StatusPill tone={inv.status==="under_review"?"amber":"green"}>{inv.status.replaceAll("_"," ")}</StatusPill><span>Investigation <b>{id.slice(0,8)}…</b></span></div>
      <div><span><b>{pct(currentConfidence)}</b> confidence</span><span><b>{w.observations.length}</b> evidence</span><span><b>{sources.length}</b> sources</span><span><b>{w.timeline.length}</b> events</span><span><b>{reasoningRuns.length}</b> reasoning runs</span></div>
    </div>
    <WorkspaceNav id={id} active={active}/>
  </>;

  let body:React.ReactNode;

  if(active==="evidence"){
    body=<div className="lensWorkspace">
      <ResearchMetrics><Metric label="Observations" value={w.observations.length} note="immutable source records"/><Metric label="Independent sources" value={sources.length} note={sources.join(" · ")||"none"} tone="violet"/><Metric label="Supporting" value={supporting.length} note="linked to hypotheses" tone="green"/><Metric label="Contradicting" value={contradicting.length} note={`${neutral.length} neutral links`} tone="red"/></ResearchMetrics>
      <div className="researchTwoCol wideLeft"><ResearchPanel title="Evidence ledger" subtitle="Every observation keeps its source identity, timestamp and provenance."><ObservationTable w={w}/></ResearchPanel><ResearchPanel title="Source diversity" subtitle="Independent evidence families, not raw observation volume." className="stickyPanel"><div className="sourceDiversityV2">{sources.map((s,i)=>{const n=w.observations.filter(o=>o.source===s).length;return <div key={s}><span><i className={`srcTone s${i%5}`}/>{s}</span><b><i style={{width:`${Math.max(12,n/w.observations.length*100)}%`}}/></b><em>{n}</em></div>})}</div><div className="lensInsight"><span>Scientific question</span><strong>What supports or contradicts this investigation?</strong><p>Evidence remains immutable. Classification and interpretation are recorded separately.</p></div></ResearchPanel></div>
      <ResearchPanel title="Evidence challenges" subtitle="Agent findings that expose repetition, missing sources and counter-evidence gaps."><div className="findingListV2">{latestFindings.map(f=><div key={f.id}><span className={`findingDot ${f.severity}`}>!</span><div><strong>{f.title}</strong><p>{f.detail}</p><small>{f.agent_id} · {f.category}</small></div><div><b>{Math.round(f.confidence*100)}%</b><span>{f.evidence_ids.length} evidence</span></div></div>)}</div></ResearchPanel>
    </div>;
  } else if(active==="structure"){
    body=<div className="lensWorkspace">
      <ResearchPanel title="Investigation Graph" subtitle="A canonical, evidence-derived projection of this investigation. Select any node to inspect its scientific context." action={<StatusPill tone="green">derived · deterministic</StatusPill>}>
        <GalileoGraph graph={investigationGraph}/>
      </ResearchPanel>
      <div className="researchTwoCol">
        <ResearchPanel title="Graph health" subtitle="Structural measurements are scoped to this investigation, not the global knowledge graph.">
          <div className="graphHealthGrid"><div><span>Entities</span><strong>{investigationGraph.metrics.entities}</strong></div><div><span>Observations</span><strong>{investigationGraph.metrics.observations}</strong></div><div><span>Hypotheses</span><strong>{investigationGraph.metrics.hypotheses}</strong></div><div><span>Sources</span><strong>{investigationGraph.metrics.independent_sources}</strong></div><div><span>Components</span><strong>{investigationGraph.metrics.connected_components}</strong></div><div><span>Density</span><strong>{investigationGraph.metrics.density.toFixed(3)}</strong></div></div>
        </ResearchPanel>
        <ResearchPanel title="Structural interpretation" subtitle="Graph Reasoner remains a separate scientific lens over the same canonical projection.">
          {latestReasoning?<><div className="overviewReasoning"><strong>{pct(latestReasoning.confidence)}</strong><div><StatusPill tone={latestReasoning.confidence>=.75?"green":"amber"}>{latestReasoning.support_level}</StatusPill><p>{latestReasoning.conclusion}</p></div></div><Link className="tinyLink" href={`/investigations/${id}?lens=reasoning`}>Open reasoning lens →</Link></>:<><p className="emptyText">No reasoning result yet.</p><RunGraphReasoner investigationId={id}/></>}
        </ResearchPanel>
      </div>
    </div>;
  } else if(active==="reasoning"){
    body=<div className="lensWorkspace"><div className="reasoningWorkbench embeddedReasoning"><aside className="reasoningContextPane"><section><span className="labLabel">Primary hypothesis</span><strong>{primary?.title??"No hypothesis yet"}</strong>{primary&&<div className="beliefTrack"><span>Prior {pct(primary.prior_confidence)}</span><b><i style={{width:pct(primary.confidence)}}/></b><span>Now {pct(primary.confidence)}</span></div>}</section><section><span className="labLabel">Available lenses</span><div className="reasonerRail">{[["Graph","What does the structure imply?","ready"],["Bayesian","How should belief change?","future"],["Causal","What causes what?","future"],["Forecast","What is likely next?","future"]].map(([n,q,s])=><div className={s==="ready"?"active":""} key={n}><i/><span><strong>{n}</strong><small>{q}</small></span><em>{s}</em></div>)}</div></section><section className="trustChecklist"><span className="labLabel">Why trust this result?</span>{["Deterministic","Replayable","Versioned","Evidence linked","Kernel recorded","Assumptions visible"].map(x=><div key={x}><i>✓</i>{x}</div>)}</section></aside><main className="reasoningCanvasPane"><div className="labPanelHead"><div><span className="labLabel">Active scientific lens</span><h2>{graphManifest?.name??"Graph Reasoner"}</h2></div><RunGraphReasoner investigationId={id}/></div><ReasoningGraph entities={relevantEntities.length?relevantEntities:entities.slice(0,8)} relationships={relevantRelationships.length?relevantRelationships:relationships.slice(0,12)}/><div className="reasoningPipeline"><span className="labLabel">Reasoning pipeline</span>{[["Evidence loaded",`${w.observations.length} observations`],["Graph constructed",`${relevantEntities.length} nodes · ${relevantRelationships.length} edges`],["Structure inspected",`${new Set(relevantRelationships.map(r=>r.kind)).size} relation types`],["Reasoning computed",latestReasoning?pct(latestReasoning.confidence):"Not run"],["Result recorded",latestReasoning?"Replayable":"Pending"]].map(([n,v],i)=><div key={n} className={latestReasoning||i<3?"done":""}><i>{i+1}</i><span><strong>{n}</strong><small>{v}</small></span></div>)}</div></main><aside className="reasoningReportPane">{latestReasoning?<><div className="reasoningHeroScore"><strong>{pct(latestReasoning.confidence)}</strong><StatusPill tone={latestReasoning.confidence>=.75?"green":"amber"}>{latestReasoning.support_level} support</StatusPill></div><details className="reasoningDisclosure" open><summary>Conclusion</summary><p>{latestReasoning.conclusion}</p></details><details className="reasoningDisclosure"><summary>Supporting factors <em>{latestReasoning.supporting_factors.length}</em></summary><div className="factorCards">{latestReasoning.supporting_factors.map((f:any,i:number)=><article key={i}><b>+</b><span>{f.entity??f.factor??"Structural signal"}<small>{f.relationship??(f.value!==undefined?String(f.value):"")}</small></span></article>)}</div></details><details className="reasoningDisclosure"><summary>Contradicting factors <em>{latestReasoning.contradicting_factors.length}</em></summary>{latestReasoning.contradicting_factors.length?<div className="factorCards negative">{latestReasoning.contradicting_factors.map((f:any,i:number)=><article key={i}><b>−</b><span>{f.entity??f.factor??String(f)}</span></article>)}</div>:<p className="quietNote">No explicit contradicting structural factors were found. This is not proof that none exist.</p>}</details><details className="reasoningDisclosure"><summary>Assumptions <em>{latestReasoning.assumptions.length}</em></summary>{latestReasoning.assumptions.map(x=><p key={x}>• {x}</p>)}</details><details className="reasoningDisclosure"><summary>Limitations <em>{latestReasoning.limitations.length}</em></summary>{latestReasoning.limitations.map(x=><p key={x}>• {x}</p>)}</details><details className="reasoningDisclosure"><summary>Recommended evidence <em>{latestReasoning.recommended_evidence.length}</em></summary>{latestReasoning.recommended_evidence.map(x=><p key={x}>→ {x}</p>)}</details></>:<p className="emptyText">No reasoning result yet. Run Graph Reasoner to create a permanent scientific interpretation.</p>}</aside></div></div>;
  } else if(active==="history"){
    body=<div className="lensWorkspace"><div className="researchTwoCol"><ResearchPanel title="Investigation timeline" subtitle="Immutable sequence of how understanding changed."><div>{[...w.timeline].reverse().map(e=><div className="timelineRowV2" key={e.id}><span className="timelineSeq">{e.sequence}</span><div><strong>{e.event_type}</strong><small>{fmt(e.occurred_at)}</small></div></div>)}</div></ResearchPanel><ResearchPanel title="Version history" subtitle="Every meaningful change becomes a revision."><div>{[...w.revisions].reverse().map(r=><div className="revisionRowV2" key={r.id}><span>#{r.revision_number}</span><div><strong>{r.message}</strong><small>{r.change_type} · {fmt(r.created_at)}</small></div></div>)}</div></ResearchPanel></div><div className="researchTwoCol"><ResearchPanel title="Confidence evolution" subtitle="Belief changes remain separate from reasoner output."><div className="confidenceJourney"><div><strong>{primary?pct(primary.prior_confidence):"—"}</strong><span>prior</span></div>{w.confidence_history.slice(-8).map(c=><div key={c.id}><i>→</i><strong>{pct(c.new_confidence)}</strong><span>{new Date(c.created_at).toLocaleDateString()}</span></div>)}{latestReasoning&&<div className="reasoningConfidence"><i>≠</i><strong>{pct(latestReasoning.confidence)}</strong><span>reasoner</span></div>}</div></ResearchPanel><ResearchPanel title="Kernel command trail" subtitle="Every action is centrally audited."><div className="ledgerList">{commands.slice(0,16).map(c=><div key={c.id}><div><strong>{c.command_type}</strong><span>corr {c.correlation_id.slice(0,8)}{c.causation_id?` · caused by ${c.causation_id.slice(0,8)}`:""}</span></div><div><StatusPill tone={c.status==="completed"?"green":"amber"}>{c.status}</StatusPill><time>{fmt(c.requested_at)}</time></div></div>)}</div></ResearchPanel></div></div>;
  } else if(active==="compare"){
    body=<div className="lensWorkspace"><ResearchPanel title="Multi-reasoner comparison" subtitle="Different scientific lenses are preserved side by side instead of averaged into a single opaque answer."><div className="comparisonMatrix"><div className="comparisonHead"><span>Lens</span><span>Confidence</span><span>Status</span><span>Scientific question</span></div>{[["Graph",latestReasoning?pct(latestReasoning.confidence):"—",latestReasoning?"active":"ready","What does the structure imply?"],["Bayesian","—","future","How should belief change?"],["Causal","—","future","What causes what?"],["Forecast","—","future","What is likely next?"],["Simulation","—","future","What happens if conditions change?"]].map(([n,c,s,q])=><div className="comparisonRow" key={n}><strong>{n}</strong><b>{c}</b><StatusPill tone={s==="active"?"green":"slate"}>{s}</StatusPill><span>{q}</span></div>)}</div></ResearchPanel><div className="researchTwoCol"><ResearchPanel title="Agreement" subtitle="Available once two or more reasoners have completed."><div className="futureCapability"><strong>Waiting for another scientific lens</strong><p>YetSee will compare conclusions, confidence, assumptions and evidence use without hiding disagreement.</p></div></ResearchPanel><ResearchPanel title="Disagreement" subtitle="Model disagreement is preserved as scientific information."><div className="futureCapability"><strong>No comparison yet</strong><p>Bayesian Reasoner is the next planned lens. Once available, differences from Graph Reasoner will be explained rather than averaged away.</p></div></ResearchPanel></div></div>;
  } else {
    body=<div className="lensWorkspace"><ResearchMetrics><Metric label="Hypothesis confidence" value={pct(currentConfidence)} note={primary?`Prior ${pct(primary.prior_confidence)}`:"discovery confidence"} tone="green"/><Metric label="Evidence" value={w.observations.length} note={`${supporting.length} supporting · ${contradicting.length} contradicting`}/><Metric label="Independent sources" value={sources.length} note={sources.join(" · ")} tone="violet"/><Metric label="Reasoning" value={latestReasoning?pct(latestReasoning.confidence):"—"} note={latestReasoning?`${latestReasoning.support_level} graph support`:"not yet run"} tone="blue"/></ResearchMetrics><div className="investigationSummaryGrid"><ResearchPanel title="Primary hypothesis" subtitle="The current belief being tested."><div className="hypothesisHero"><div><StatusPill tone="violet">{primary?.status??"pending"}</StatusPill><h3>{primary?.title??"No hypothesis yet"}</h3><p>{primary?.description??"Create a first-class hypothesis to begin evidence-based reasoning."}</p></div>{primary&&<div className="confidenceDial"><strong>{pct(primary.confidence)}</strong><span>confidence</span></div>}</div></ResearchPanel><ResearchPanel title="Attention required" subtitle="What should the investigator inspect next?"><div className="attentionList">{latestFindings.length?latestFindings.slice(0,4).map(f=><div key={f.id}><span className={`findingDot ${f.severity}`}>!</span><div><strong>{f.title}</strong><small>{f.agent_id} · {Math.round(f.confidence*100)}%</small></div></div>):<p className="emptyText">No outstanding agent findings.</p>}</div></ResearchPanel><ResearchPanel title="Latest activity" subtitle="Recent audited changes."><div className="timelineMini">{[...w.timeline].reverse().slice(0,6).map(e=><div key={e.id}><i/><time>{new Date(e.occurred_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</time><span>{e.event_type}</span></div>)}</div></ResearchPanel></div><div className="workspaceOverviewGrid"><ResearchPanel title="Evidence health" subtitle="Independence matters more than volume."><div className="sourceDiversityV2">{sources.map((s,i)=>{const n=w.observations.filter(o=>o.source===s).length;return <div key={s}><span><i className={`srcTone s${i%5}`}/>{s}</span><b><i style={{width:`${Math.max(12,n/w.observations.length*100)}%`}}/></b><em>{n}</em></div>})}</div><Link className="tinyLink" href={`/investigations/${id}?lens=evidence`}>Inspect evidence →</Link></ResearchPanel><ResearchPanel title="Current structural interpretation" subtitle="The latest permanent reasoning result.">{latestReasoning?<><div className="overviewReasoning"><strong>{pct(latestReasoning.confidence)}</strong><div><StatusPill tone={latestReasoning.confidence>=.75?"green":"amber"}>{latestReasoning.support_level}</StatusPill><p>{latestReasoning.conclusion}</p></div></div><Link className="tinyLink" href={`/investigations/${id}?lens=reasoning`}>Open reasoning lens →</Link></>:<><p className="emptyText">No reasoning result yet.</p><RunGraphReasoner investigationId={id}/></>}</ResearchPanel></div><ResearchPanel title="Scientific workflow" subtitle="One investigation, multiple lenses, one auditable history."><div className="investigationWorkflow">{lenses.slice(0,5).map((l,i)=><Link key={l.id} href={`/investigations/${id}?lens=${l.id}`}><span>{i+1}</span><div><strong>{l.label}</strong><small>{l.question}</small></div><b>→</b></Link>)}</div></ResearchPanel></div>;
  }

  return <StudioFrame active="Investigations"><ResearchPage eyebrow="Living Investigation" title={inv.title} subtitle={inv.summary??"Evidence-backed, versioned and continuously reviewable."} actions={<InvestigationAgentActions investigationId={id}/>}>{commonHeader}{body}</ResearchPage></StudioFrame>;
}
