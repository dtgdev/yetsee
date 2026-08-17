import Link from "next/link";
import { apiGet } from "../../lib/api";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";

export const dynamic = "force-dynamic";

type Investigation = { id:string; title:string; status:string; confidence:number; summary:string|null; updated_at:string };

export default async function InvestigationsPage() {
  let investigations: Investigation[] = [];
  try { investigations = await apiGet<Investigation[]>("/api/v1/investigations"); } catch {}
  const active = investigations.filter(i => i.status !== "archived").length;
  const avg = investigations.length ? Math.round(investigations.reduce((s,i)=>s+i.confidence,0)/investigations.length*100) : 0;

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
  </ResearchPage></StudioFrame>;
}
