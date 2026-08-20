import Link from "next/link";
import { apiGet } from "../../lib/api";
import GalileoGraph from "../../components/GalileoGraph";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";

export const dynamic = "force-dynamic";

type Investigation = { id:string; title:string; status:string; confidence:number; summary:string|null; updated_at:string };
type RankedNode = { node_id:string; domain_id?:string; label:string; kind:string; score:number; evidence_count:number; source_count:number };
type BridgeNode = { node_id:string; domain_id?:string; label:string; kind:string; betweenness:number; communities_connected:number; articulation_point:boolean; evidence_count?:number };
type Community = { id:number; size:number; node_ids:string[]; semantic_nodes?:{node_id:string;domain_id?:string;label:string;kind:string}[]; kinds:Record<string,number> };
type GraphNode = { id:string; domain_id:string; kind:string; label:string; description?:string|null; confidence:number; evidence_count:number; source_count:number; degree:number; degree_centrality:number; metadata:Record<string,any> };
type GraphEdge = { id:string; source:string; target:string; kind:string; confidence:number; evidence_ids:string[]; metadata:Record<string,any> };
type GraphAnalytics = {
  degree_centrality?:Record<string,number>;
  betweenness_centrality?:Record<string,number>;
  closeness_centrality?:Record<string,number>;
  pagerank?:Record<string,number>;
  communities?:Community[];
  bridge_nodes?:BridgeNode[];
  articulation_points?:string[];
  connected_components?:string[][];
  central_nodes?:RankedNode[];
  semantic_central_nodes?:RankedNode[];
  top_nodes?:RankedNode[];
  top_semantic_nodes?:RankedNode[];
  density?:number;
};
type InvestigationGraph = {
  investigation:{id:string;title:string;status:string};
  nodes:GraphNode[];
  edges:GraphEdge[];
  metrics:{nodes:number;edges:number;entities:number;observations:number;hypotheses:number;independent_sources:number;sources:string[];connected_components:number;density:number;relationship_types:Record<string,number>};
  analytics?:GraphAnalytics;
  generated_at:string;
  derived:boolean;
};

async function safeGraph(id:string):Promise<InvestigationGraph|null>{
  try{return await apiGet<InvestigationGraph>(`/api/v1/investigations/${id}/graph`)}catch{return null}
}

function mergeMetricMaps(graphs:InvestigationGraph[], key:keyof Pick<GraphAnalytics,"degree_centrality"|"betweenness_centrality"|"closeness_centrality"|"pagerank">){
  const merged:Record<string,number>={};
  for(const graph of graphs){
    const values=graph.analytics?.[key]??{};
    for(const [nodeId,value] of Object.entries(values)) merged[nodeId]=Math.max(merged[nodeId]??0,value);
  }
  return merged;
}

function mergeRanked(graphs:InvestigationGraph[], keys:(keyof Pick<GraphAnalytics,"central_nodes"|"semantic_central_nodes"|"top_nodes"|"top_semantic_nodes">)[]){
  const ranked=new Map<string,RankedNode>();
  for(const graph of graphs){
    for(const key of keys){
      for(const item of graph.analytics?.[key]??[]){
        const current=ranked.get(item.node_id);
        if(!current||item.score>current.score) ranked.set(item.node_id,item);
      }
    }
  }
  return [...ranked.values()].sort((a,b)=>b.score-a.score);
}

function buildLandscape(graphs:InvestigationGraph[]):InvestigationGraph{
  const nodeMap=new Map<string,GraphNode>();
  const edgeMap=new Map<string,GraphEdge>();
  const sources=new Set<string>();
  const relationshipTypes:Record<string,number>={};
  const communities:Community[]=[];
  const bridges=new Map<string,BridgeNode>();
  const articulationPoints=new Set<string>();
  const connectedComponents:string[][]=[];
  let communityOffset=0;

  for(const graph of graphs){
    graph.nodes.forEach(node=>nodeMap.set(node.id,node));
    graph.edges.forEach(edge=>edgeMap.set(edge.id,edge));
    graph.metrics.sources.forEach(source=>sources.add(source));
    for(const [kind,count] of Object.entries(graph.metrics.relationship_types)) relationshipTypes[kind]=(relationshipTypes[kind]??0)+count;

    const graphCommunities=graph.analytics?.communities??[];
    for(const community of graphCommunities){
      communities.push({...community,id:community.id+communityOffset});
    }
    communityOffset+=graphCommunities.length;

    for(const bridge of graph.analytics?.bridge_nodes??[]){
      const current=bridges.get(bridge.node_id);
      if(!current||bridge.betweenness>current.betweenness) bridges.set(bridge.node_id,bridge);
    }
    for(const nodeId of graph.analytics?.articulation_points??[]) articulationPoints.add(nodeId);
    for(const component of graph.analytics?.connected_components??[]) connectedComponents.push(component);
  }

  const nodes=[...nodeMap.values()];
  const edges=[...edgeMap.values()];
  const entityKinds=new Set(["entity","concept","organization","company","person","topic"]);
  const entities=nodes.filter(node=>entityKinds.has(node.kind.toLowerCase())).length;
  const observations=nodes.filter(node=>node.kind.toLowerCase()==="observation").length;
  const hypotheses=nodes.filter(node=>node.kind.toLowerCase()==="hypothesis").length;
  const semanticCentral=mergeRanked(graphs,["semantic_central_nodes","top_semantic_nodes"]);
  const central=mergeRanked(graphs,["central_nodes","top_nodes"]);
  const averageDensity=graphs.length?graphs.reduce((sum,graph)=>sum+(graph.analytics?.density??graph.metrics.density),0)/graphs.length:0;

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
      connected_components:connectedComponents.length||graphs.reduce((sum,graph)=>sum+graph.metrics.connected_components,0),
      density:averageDensity,
      relationship_types:relationshipTypes,
    },
    analytics:{
      degree_centrality:mergeMetricMaps(graphs,"degree_centrality"),
      betweenness_centrality:mergeMetricMaps(graphs,"betweenness_centrality"),
      closeness_centrality:mergeMetricMaps(graphs,"closeness_centrality"),
      pagerank:mergeMetricMaps(graphs,"pagerank"),
      communities,
      bridge_nodes:[...bridges.values()].sort((a,b)=>b.betweenness-a.betweenness),
      articulation_points:[...articulationPoints],
      connected_components:connectedComponents,
      central_nodes:central,
      semantic_central_nodes:semanticCentral,
      top_nodes:central,
      top_semantic_nodes:semanticCentral,
      density:averageDensity,
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
  const semanticCount=landscape.analytics?.semantic_central_nodes?.length??0;
  const communityCount=landscape.analytics?.communities?.length??0;
  const bridgeCount=landscape.analytics?.bridge_nodes?.length??0;

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

    {landscape.nodes.length>0 && <>
      <div className="structureScientificHeader">
        <div><span>SCIENTIFIC SYSTEM MAP</span><h2>Investigation Landscape</h2><p>Explore the complete evidence-derived topology across living investigations. Centrality, communities, bridge concepts, provenance, evidence paths and node inspection remain available.</p></div>
        <div className="structureTrust"><StatusPill tone="green">derived</StatusPill><StatusPill tone="blue">deterministic</StatusPill><StatusPill tone="violet">replayable</StatusPill></div>
      </div>
      <ResearchMetrics>
        <Metric label="Semantic concepts" value={semanticCount} note="ranked domain nodes" tone="blue"/>
        <Metric label="Communities" value={communityCount} note="structural neighborhoods" tone="violet"/>
        <Metric label="Bridge concepts" value={bridgeCount} note="cross-community connectors" tone="amber"/>
        <Metric label="Independent sources" value={landscape.metrics.independent_sources} note={landscape.metrics.sources.join(" · ")||"none"} tone="green"/>
      </ResearchMetrics>
      <ResearchPanel title="Investigation Landscape" subtitle="Search, filter, zoom and inspect every node. The right-side inspector preserves scientific importance, evidence paths, structural role and provenance." action={<span className="panelCode">LIVE GRAPH PROJECTION</span>}>
        <GalileoGraph graph={landscape}/>
      </ResearchPanel>
    </>}
  </ResearchPage></StudioFrame>;
}
