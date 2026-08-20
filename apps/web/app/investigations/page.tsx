import Link from "next/link";
import { apiGet } from "../../lib/api";
import GalileoGraph from "../../components/GalileoGraph";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";

export const dynamic = "force-dynamic";

type Investigation = { id:string; title:string; status:string; confidence:number; summary:string|null; updated_at:string };
type GraphNode = { id:string; domain_id:string; kind:string; label:string; description?:string|null; confidence:number; evidence_count:number; source_count:number; degree:number; degree_centrality:number; metadata:Record<string,any> };
type GraphEdge = { id:string; source:string; target:string; kind:string; confidence:number; evidence_ids:string[]; metadata:Record<string,any> };
type InvestigationGraph = {
  investigation:{id:string;title:string;status:string};
  nodes:GraphNode[];
  edges:GraphEdge[];
  metrics:{nodes:number;edges:number;entities:number;observations:number;hypotheses:number;independent_sources:number;sources:string[];connected_components:number;density:number;relationship_types:Record<string,number>};
  analytics?:Record<string,any>;
  generated_at:string;
  derived:boolean;
};

async function safeGraph(id:string):Promise<InvestigationGraph|null>{
  try{return await apiGet<InvestigationGraph>(`/api/v1/investigations/${id}/graph`)}catch{return null}
}

function buildLandscape(graphs:InvestigationGraph[]):InvestigationGraph{
  const nodeMap=new Map<string,GraphNode>();
  const edgeMap=new Map<string,GraphEdge>();
  const sources=new Set<string>();
  const relationshipTypes:Record<string,number>={};

  for(const graph of graphs){
    graph.nodes.forEach(node=>nodeMap.set(node.id,node));
    graph.edges.forEach(edge=>edgeMap.set(edge.id,edge));
    graph.metrics.sources.forEach(source=>sources.add(source));
    for(const [kind,count] of Object.entries(graph.metrics.relationship_types)) relationshipTypes[kind]=(relationshipTypes[kind]??0)+count;
  }

  const nodes=[...nodeMap.values()];
  const edges=[...edgeMap.values()];
  const entityKinds=new Set(["entity","concept","organization","company","person","topic"]);
  const entities=nodes.filter(node=>entityKinds.has(node.kind.toLowerCase())).length;
  const observations=nodes.filter(node=>node.kind.toLowerCase()==="observation").length;
  const hypotheses=nodes.filter(node=>node.kind.toLowerCase()==="hypothesis").length;

  return {
    investigation:{id:"investigation-landscape",title:"Investigation Landscape",status:"live"},
    nodes,
    edges,
    metrics:{
      nodes:nodes.length,
      edges:edges.length,
      entities,
      observations,
      hypotheses,
      independent_sources:sources.size,
      sources:[...sources],
      connected_components:graphs.reduce((sum,graph)=>sum+graph.metrics.connected_components,0),
      density:graphs.length?graphs.reduce((sum,graph)=>sum+graph.metrics.density,0)/graphs.length:0,
      relationship_types:relationshipTypes,
    },
    generated_at:new Date().toISOString(),
    derived:true,
  };
}

export default async function InvestigationsPage() {
  let investigations: Investigation[] = [];
  try { investigations = await apiGet<Investigation[]>("/api/v1/investigations"); } catch {}
  const active = investigations.filter(i => i.status !== "archived").length;
  const avg = investigations.length ? Math.round(investigations.reduce((s,i)=>s+i.confidence,0)/investigations.length*100) : 0;
  const graphs=(await Promise.all(investigations.map(inv=>safeGraph(inv.id)))).filter((graph):graph is InvestigationGraph=>graph!==null);
  const landscape=buildLandscape(graphs);

  return <StudioFrame active="Investigations"><ResearchPage eyebrow="Living Investigation Runtime" title="Investigations" subtitle="Versioned research workspaces where evidence, hypotheses, confidence, agents and history stay connected.">
    <ResearchMetrics>
      <Metric label="Investigations" value={investigations.length} note="living and replayable" />
      <Metric label="Active" value={active} note="currently in review" tone="green" />
      <Metric label="Average confidence" value={`${avg}%`} note="across investigations" tone="violet" />
      <Metric label="History model" value="Append-only" note="no silent overwrites" tone="amber" />
    </ResearchMetrics>

    <ResearchPanel title="Living investigations" subtitle="Open a workspace to inspect evidence, confidence, agent findings and timeline." action={<span className="panelCode">GET /api/v1/investigations</span>}>
      <div className="investigationGridV2">
        {investigations.map(inv => <Link className="investigationCardV2" href={`/investigations/${inv.id}`} key={inv.id}>
          <div className="investigationCardTop"><StatusPill tone={inv.status === "under_review" ? "amber" : "green"}>{inv.status.replaceAll("_"," ")}</StatusPill><span>{new Date(inv.updated_at).toLocaleDateString()}</span></div>
          <h3>{inv.title}</h3><p>{inv.summary ?? "Living, evidence-backed investigation."}</p>
          <div className="confidenceBarV2"><div><span>Confidence</span><strong>{Math.round(inv.confidence*100)}%</strong></div><i><b style={{width:`${Math.round(inv.confidence*100)}%`}} /></i></div>
          <div className="cardFooterLink">Open scientific workspace →</div>
        </Link>)}
        {!investigations.length && <div className="emptyResearchState"><strong>No investigations yet</strong><p>Promote a discovery candidate to create the first living investigation.</p><Link href="/discovery">Open Discovery →</Link></div>}
      </div>
    </ResearchPanel>

    {landscape.nodes.length>0 && <ResearchPanel title="Investigation Landscape" subtitle="Explore how investigations, hypotheses, evidence, concepts and sources connect across the living research system." action={<span className="panelCode">LIVE GRAPH PROJECTION</span>}>
      <GalileoGraph graph={landscape}/>
    </ResearchPanel>}
  </ResearchPage></StudioFrame>;
}
