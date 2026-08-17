import Link from "next/link";
import { apiGet } from "../../lib/api";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";
import { RunGraphReasoner } from "../../components/ReasoningActions";
import ReasoningGraph from "../../components/ReasoningGraph";

export const dynamic="force-dynamic";
type Investigation={id:string;title:string;status:string;confidence:number;summary?:string|null};
type Manifest={id:string;name:string;version:string;scientific_question:string;deterministic:boolean};
type Result={id:string;run_id:string;investigation_id:string;reasoner_id:string;conclusion:string;confidence:number;support_level:string;supporting_factors:any[];contradicting_factors:any[];assumptions:string[];limitations:string[];recommended_evidence:string[];metrics:Record<string,any>;evidence_ids:string[];explanation:string;created_at:string};
type Run={id:string;reasoner_id:string;status:string;started_at:string|null;finished_at:string|null;created_at:string};
type Observation={id:string;source:string;topic:string;metric:string;value:number|null;observed_at:string};
type Workspace={investigation:Investigation;hypotheses:{id:string;title:string;confidence:number;prior_confidence:number;status:string}[];observations:Observation[];timeline:{id:string;event_type:string;occurred_at:string}[];confidence_history:{id:string;old_confidence:number;new_confidence:number;created_at:string}[];agent_findings:{id:string;severity:string;title:string}[];revisions:{id:string;revision_number:number;message:string;created_at:string}[]};
type Entity={id:string;canonical_name:string;kind:string};
type Relationship={id:string;source_entity_id:string;target_entity_id:string;kind:string;confidence:number;evidence_ids:string[]};
type Command={id:string;command_type:string;aggregate_id:string|null;correlation_id:string;status:string;requested_at:string};
async function safe<T>(p:string,f:T){try{return await apiGet<T>(p)}catch{return f}}
const pct=(n:number)=>`${Math.round(n*100)}%`;
const fmt=(d:string|null|undefined)=>d?new Date(d).toLocaleString():"—";

export default async function ReasoningPage(){
 const investigations=await safe<Investigation[]>("/api/v1/investigations",[]); const featured=investigations[0];
 const reasoners=await safe<Manifest[]>("/api/v1/reasoners",[]); const graph=reasoners.find(r=>r.id==="graph");
 if(!featured)return <StudioFrame active="Reasoning"><ResearchPage eyebrow="Scientific Reasoning" title="Reasoning Laboratory" subtitle="Transparent, replayable mathematical lenses over living investigations."><ResearchPanel title="No investigations" subtitle="Create or promote an investigation before running scientific reasoning."><Link className="primaryAction" href="/discovery">Open Discovery →</Link></ResearchPanel></ResearchPage></StudioFrame>;
 const [results,runs,workspace,entities,relationships,commands]=await Promise.all([
   safe<Result[]>(`/api/v1/investigations/${featured.id}/reasoning/results`,[]),
   safe<Run[]>(`/api/v1/investigations/${featured.id}/reasoning/runs`,[]),
   safe<Workspace|null>(`/api/v1/investigations/${featured.id}/workspace`,null),
   safe<Entity[]>("/api/v1/graph/entities?limit=80",[]),
   safe<Relationship[]>("/api/v1/graph/relationships?limit=120",[]),
   safe<Command[]>("/api/v1/kernel/commands?limit=100",[])
 ]);
 const latest=results[0]; const primary=workspace?.hypotheses?.[0];
 const evidenceSet=new Set(latest?.evidence_ids??workspace?.observations.map(o=>o.id)??[]);
 const relevantRelationships=relationships.filter(r=>r.evidence_ids.some(id=>evidenceSet.has(id)));
 const relevantEntityIds=new Set(relevantRelationships.flatMap(r=>[r.source_entity_id,r.target_entity_id]));
 const relevantEntities=entities.filter(e=>relevantEntityIds.has(e.id));
 const invCommands=commands.filter(c=>c.aggregate_id===featured.id);
 const sources=[...new Set(workspace?.observations.map(o=>o.source)??[])];
 const relTypes=latest?.metrics?.relationship_types??{};
 const confidencePath=workspace?.confidence_history??[];
 const pipeline=[
   ["Evidence loaded",workspace?.observations.length?`${workspace.observations.length} observations`:"Waiting"],
   ["Graph constructed",`${latest?.metrics?.entities??relevantEntities.length} nodes · ${latest?.metrics?.relationships??relevantRelationships.length} edges`],
   ["Structure inspected",Object.keys(relTypes).length?`${Object.keys(relTypes).length} relation types`:"Waiting"],
   ["Reasoning computed",latest?`${pct(latest.confidence)} confidence`:"Not run"],
   ["Result recorded",latest?"Replayable":"Pending"]
 ];
 return <StudioFrame active="Reasoning"><ResearchPage eyebrow="Scientific Reasoning" title="Reasoning Laboratory" subtitle="Explore how evidence becomes a structured interpretation. Reasoners compute; canonical evidence remains unchanged." actions={<RunGraphReasoner investigationId={featured.id}/> }>
   <div className="reasoningContextBar"><div><StatusPill tone={featured.status==="under_review"?"amber":"green"}>{featured.status.replaceAll("_"," ")}</StatusPill><strong>{featured.title}</strong><span>{primary?.title??"No primary hypothesis"}</span></div><div><span>{workspace?.observations.length??0} evidence</span><span>{sources.length} sources</span><span>{workspace?.timeline.length??0} timeline events</span><span>{runs.length} reasoning runs</span></div></div>
   <ResearchMetrics><Metric label="Reasoning confidence" value={latest?pct(latest.confidence):"—"} note={latest?`${latest.support_level} structural support`:"Run a reasoner"} tone={latest&&latest.confidence>=.75?"green":"amber"}/><Metric label="Graph nodes" value={latest?.metrics?.entities??relevantEntities.length} note="evidence-backed neighborhood"/><Metric label="Graph edges" value={latest?.metrics?.relationships??relevantRelationships.length} note={`${Object.keys(relTypes).length} relationship types`} tone="violet"/><Metric label="Independent sources" value={latest?.metrics?.independent_sources??sources.length} note={sources.join(" · ")||"none"} tone="blue"/><Metric label="Reasoning runs" value={runs.length} note={graph?.deterministic?"deterministic · replayable":"replayable"} tone="green"/></ResearchMetrics>
   <div className="reasoningWorkbench">
     <aside className="reasoningContextPane">
       <section><span className="labLabel">Investigation</span><h3>{featured.title}</h3><p>{featured.summary??"Evidence-backed living investigation."}</p></section>
       <section><span className="labLabel">Primary hypothesis</span><strong>{primary?.title??"No hypothesis yet"}</strong>{primary&&<div className="beliefTrack"><span>Prior {pct(primary.prior_confidence)}</span><b><i style={{width:pct(primary.confidence)}}/></b><span>Now {pct(primary.confidence)}</span></div>}</section>
       <section><span className="labLabel">Available lenses</span><div className="reasonerRail">{reasoners.map(r=><div className={r.id==="graph"?"active":""} key={r.id}><i/> <span><strong>{r.name}</strong><small>{r.scientific_question}</small></span><em>{r.id==="graph"?"ready":"future"}</em></div>)}</div></section>
       <section className="trustChecklist"><span className="labLabel">Why trust this result?</span>{["Deterministic","Replayable","Versioned","Evidence linked","Kernel recorded","Assumptions visible"].map(x=><div key={x}><i>✓</i>{x}</div>)}</section>
     </aside>

     <main className="reasoningCanvasPane">
       <div className="labPanelHead"><div><span className="labLabel">Interactive structure</span><h2>Investigation Graph</h2></div><div className="labBadges"><StatusPill tone="blue">{latest?.reasoner_id??"graph"}</StatusPill><StatusPill tone="green">{graph?.deterministic?"deterministic":"recorded"}</StatusPill></div></div>
       <ReasoningGraph entities={relevantEntities.length?relevantEntities:entities.slice(0,8)} relationships={relevantRelationships.length?relevantRelationships:relationships.slice(0,12)}/>
       <div className="structuralMetrics"><div><span>Nodes</span><strong>{latest?.metrics?.entities??relevantEntities.length}</strong></div><div><span>Edges</span><strong>{latest?.metrics?.relationships??relevantRelationships.length}</strong></div><div><span>Sources</span><strong>{latest?.metrics?.independent_sources??sources.length}</strong></div><div><span>Support weight</span><strong>{latest?.metrics?.supporting_weight??0}</strong></div><div><span>Contradict weight</span><strong>{latest?.metrics?.contradicting_weight??0}</strong></div></div>
       <div className="reasoningPipeline"><span className="labLabel">Reasoning pipeline</span>{pipeline.map(([name,value],i)=><div key={name} className={latest||i<3?"done":""}><i>{i+1}</i><span><strong>{name}</strong><small>{value}</small></span></div>)}</div>
     </main>

     <aside className="reasoningReportPane">
       <div className="reasonerTitle"><span className="reasonerGlyph">⌘</span><div><span className="labLabel">Active lens</span><h2>{graph?.name??"Graph Reasoner"}</h2><p>{graph?.scientific_question??"What does the structure imply?"}</p></div></div>
       {latest?<><div className="reasoningHeroScore"><strong>{pct(latest.confidence)}</strong><StatusPill tone={latest.confidence>=.75?"green":"amber"}>{latest.support_level} support</StatusPill></div>
       <details className="reasoningDisclosure" open><summary>Conclusion</summary><p>{latest.conclusion}</p></details>
       <details className="reasoningDisclosure"><summary>Supporting factors <em>{latest.supporting_factors.length}</em></summary><div className="factorCards">{latest.supporting_factors.map((f,i)=><article key={i}><b>+</b><span>{f.entity??f.factor??"Structural signal"}<small>{f.relationship??(f.value!==undefined?String(f.value):"")}</small></span></article>)}</div></details>
       <details className="reasoningDisclosure"><summary>Contradicting factors <em>{latest.contradicting_factors.length}</em></summary>{latest.contradicting_factors.length?<div className="factorCards negative">{latest.contradicting_factors.map((f:any,i:number)=><article key={i}><b>−</b><span>{f.entity??f.factor??String(f)}</span></article>)}</div>:<p className="quietNote">No explicit contradicting structural factors were found. This is not the same as proof that none exist.</p>}</details>
       <details className="reasoningDisclosure"><summary>Assumptions <em>{latest.assumptions.length}</em></summary>{latest.assumptions.map(x=><p key={x}>• {x}</p>)}</details>
       <details className="reasoningDisclosure"><summary>Limitations <em>{latest.limitations.length}</em></summary>{latest.limitations.map(x=><p key={x}>• {x}</p>)}</details>
       <details className="reasoningDisclosure"><summary>Recommended evidence <em>{latest.recommended_evidence.length}</em></summary>{latest.recommended_evidence.map(x=><p key={x}>→ {x}</p>)}</details>
       <details className="reasoningDisclosure"><summary>Explanation</summary><p>{latest.explanation}</p></details></>:<p className="emptyText">No reasoning result yet. Run Graph Reasoner to create the first permanent scientific interpretation.</p>}
     </aside>
   </div>

   <div className="reasoningLowerGrid">
     <ResearchPanel title="Reasoning timeline" subtitle="A visible scientific process, not a black box."><div className="reasoningTimeline">{pipeline.map(([name,value],i)=><div key={name}><i className={latest||i<3?"done":""}/><span><strong>{name}</strong><small>{value}</small></span><time>{latest&&i>=3?fmt(latest.created_at):""}</time></div>)}</div></ResearchPanel>
     <ResearchPanel title="Confidence evolution" subtitle="Belief changes independently from reasoner output."><div className="confidenceJourney"><div><strong>{primary?pct(primary.prior_confidence):"—"}</strong><span>prior</span></div>{confidencePath.slice(-5).map(c=><div key={c.id}><i>→</i><strong>{pct(c.new_confidence)}</strong><span>{new Date(c.created_at).toLocaleDateString()}</span></div>)}{latest&&<div className="reasoningConfidence"><i>≠</i><strong>{pct(latest.confidence)}</strong><span>reasoner</span></div>}</div></ResearchPanel>
     <ResearchPanel title="Model comparison" subtitle="Designed for multiple scientific perspectives."><div className="modelCompare">{[["Graph",latest?pct(latest.confidence):"—","active"],["Bayesian","—","future"],["Causal","—","future"],["Forecast","—","future"],["Simulation","—","future"]].map(([n,v,s])=><div key={n}><span>{n}</span><strong>{v}</strong><em>{s}</em></div>)}</div></ResearchPanel>
   </div>

   <div className="reasoningAuditStrip">
     <ResearchPanel title="Previous reasoning runs" subtitle="Permanent scientific interpretations."><div className="ledgerList">{results.slice(0,8).map(r=><div key={r.id}><div><strong>{r.reasoner_id} · {pct(r.confidence)}</strong><span>{r.conclusion}</span></div><time>{fmt(r.created_at)}</time></div>)}{!results.length&&<p className="emptyText">No reasoning history yet.</p>}</div></ResearchPanel>
     <ResearchPanel title="Kernel command trail" subtitle="Every run is centrally audited."><div className="ledgerList">{invCommands.filter(c=>c.command_type==="RunReasoner").slice(0,8).map(c=><div key={c.id}><div><strong>{c.command_type}</strong><span>correlation {c.correlation_id.slice(0,8)}…</span></div><div><StatusPill tone={c.status==="completed"?"green":"amber"}>{c.status}</StatusPill><time>{fmt(c.requested_at)}</time></div></div>)}{!invCommands.length&&<p className="emptyText">No command audit entries yet.</p>}</div></ResearchPanel>
   </div>
 </ResearchPage></StudioFrame>;
}
