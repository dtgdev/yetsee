import Link from "next/link";
import { apiGet } from "../../lib/api";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";

export const dynamic = "force-dynamic";
type Candidate={id:string;title:string;score:number;confidence:number;detector_count:number;evidence_count:number;summary:string|null;detector_scores:Record<string,number>;status:string;attributes:{source_count?:number;semantic_kind?:string;quality_gate?:{status:string;reasons:string[]}}};
type Detector={id:string;version:string;description:string};
async function safeGet<T>(path:string,fallback:T){try{return await apiGet<T>(path)}catch{return fallback}}

export default async function DiscoveryPage(){
 const [candidates,detectors]=await Promise.all([safeGet<Candidate[]>("/api/v1/discovery/candidates",[]),safeGet<Detector[]>("/api/v1/detectors",[])]);
 const promotable=candidates.filter(c=>c.status==="candidate").length;
 const watch=candidates.filter(c=>c.status==="watch").length;
 return <StudioFrame active="Discovery"><ResearchPage eyebrow="Ensemble Discovery" title="Discovery" subtitle="Independent detectors surface changes, then quality gates separate durable evidence from noise.">
  <ResearchMetrics><Metric label="Candidates" value={candidates.length}/><Metric label="Promotable" value={promotable} tone="green"/><Metric label="Watchlist" value={watch} tone="amber"/><Metric label="Detectors" value={detectors.length} tone="violet"/></ResearchMetrics>
  <div className="researchTwoCol wideLeft">
   <ResearchPanel title="Candidate investigations" subtitle="Evidence worth inspecting now." action={<span className="panelCode">ensemble ranked</span>}>
    <div className="candidateResearchList">{candidates.map(c=><Link href={`/discovery/${c.id}`} className="candidateResearchCard" key={c.id}>
      <div className="candidateResearchTop"><div><StatusPill tone={c.status==="candidate"?"green":"amber"}>{c.status}</StatusPill>{c.attributes?.semantic_kind&&<StatusPill tone="slate">{c.attributes.semantic_kind}</StatusPill>}</div><strong>{Math.round(c.score*100)}</strong></div>
      <h3>{c.title}</h3><p>{c.summary}</p>
      <div className="candidateMeta"><span>{c.evidence_count} evidence</span><span>{c.attributes?.source_count??0} sources</span><span>{c.detector_count} models</span></div>
      <div className="detectorMiniBars">{Object.entries(c.detector_scores).slice(0,4).map(([n,s])=><div key={n}><span>{n}</span><i><b style={{width:`${Math.round(s*100)}%`}}/></i><em>{Math.round(s*100)}</em></div>)}</div>
    </Link>)}{!candidates.length&&<div className="emptyResearchState"><strong>No candidates yet</strong><p>Run the discovery pipeline to surface evidence-backed opportunities.</p></div>}</div>
   </ResearchPanel>
   <ResearchPanel title="Detector registry" subtitle="Independent analytical lenses." className="stickyPanel"><div className="detectorRegistryV2">{detectors.map(d=><div key={d.id}><span className="detectorGlyph">⌁</span><div><strong>{d.id}</strong><p>{d.description}</p></div><em>v{d.version}</em></div>)}</div></ResearchPanel>
  </div>
 </ResearchPage></StudioFrame>
}
