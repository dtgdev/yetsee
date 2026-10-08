import Link from "next/link";
import { apiGet } from "../lib/api";
import { StudioFrame } from "../components/StudioChrome";

export const dynamic = "force-dynamic";

type Investigation = { id:string; title:string; status:string; confidence:number; summary:string|null; updated_at:string };
type SignalSummary = { observations:number; connectors:number; sources:{source:string; count:number}[]; last_run:null|{status:string} };
type GraphSummary = { entities:number; relationships:number; entity_kinds:{kind:string; count:number}[]; relationship_kinds:{kind:string; count:number}[]; last_run:null|{feature_count:number} };
type AgentSummary = { agents:number; tasks:number; runs:number; findings:number; task_statuses:{status:string;count:number}[] };
type AgentTask = { id:string; task_type:string; agent_id:string; status:string; target_id?:string; created_at:string; result_json:Record<string,unknown> };
type Finding = { id:string; agent_id:string; category:string; severity:string; confidence:number; title:string; detail:string; target_id?:string; created_at?:string };
type Connector = { id:string; state:null|{health?:string; last_success_at:string|null} };
type Workspace = {
  investigation:{ id:string; title:string; confidence:number; summary:string|null; slug?:string|null };
  observations:{ id:string; source:string; topic:string|null; metric:string; value:number|null; observed_at:string }[];
  hypotheses:{ id:string; title:string; confidence:number; prior_confidence:number }[];
  agent_findings:Finding[];
};

async function safeGet<T>(path:string, fallback:T):Promise<T> { try { return await apiGet<T>(path); } catch { return fallback; } }
const pct = (v:number) => `${(v*100).toFixed(1)}%`;

export default async function Home() {
  const [investigations, signal, graph, agentSummary, tasks, findings, connectors] = await Promise.all([
    safeGet<Investigation[]>("/api/v1/investigations", []),
    safeGet<SignalSummary>("/api/v1/signal-lake/summary", { observations:0, connectors:0, sources:[], last_run:null }),
    safeGet<GraphSummary>("/api/v1/graph/summary", { entities:0, relationships:0, entity_kinds:[], relationship_kinds:[], last_run:null }),
    safeGet<AgentSummary>("/api/v1/agent-plane/summary", { agents:0, tasks:0, runs:0, findings:0, task_statuses:[] }),
    safeGet<AgentTask[]>("/api/v1/agent-tasks?limit=8", []),
    safeGet<Finding[]>("/api/v1/agent-findings?limit=8", []),
    safeGet<Connector[]>("/api/v1/connectors", []),
  ]);

  const featured = [...investigations].sort((a,b)=>new Date(b.updated_at).getTime()-new Date(a.updated_at).getTime())[0];
  const workspace = featured ? await safeGet<Workspace| null>(`/api/v1/investigations/${featured.id}/workspace`, null) : null;
  const healthy = connectors.filter(c => c.state?.health === "healthy").length;
  const sourceCount = workspace ? new Set(workspace.observations.map(o => o.source)).size : signal.sources.length;
  const confidence = workspace?.hypotheses[0]?.confidence ?? featured?.confidence ?? 0;
  const featuredFindings = workspace?.agent_findings.slice(0,3) ?? findings.slice(0,3);
  const nextHref = featured ? workspace && workspace.hypotheses.length === 0 ? `/investigations/${featured.id}?lens=evidence#hypothesis-setup` : `/investigations/${featured.id}` : "/discovery";
  const nextLabel = featured ? workspace && workspace.hypotheses.length === 0 ? "Define a hypothesis" : "Continue investigation" : "Explore discoveries";

  return (
    <StudioFrame active="Home">
      <main className="researchHome">
        <section className="researchHero">
          <div>
            <p className="heroKicker">YOUR RESEARCH</p>
            <h1>{featured ? "Pick up where you left off." : "Start with a question."}</h1>
            <p>{featured ? featured.title : "Explore emerging topics and create an investigation to test an idea."}</p>
            <Link className="homePrimaryAction" href={nextHref}>{nextLabel} →</Link>
            {featured&&<Link className="homeSecondaryAction" href="/investigations">See all investigations</Link>}
          </div>
        </section>

        <details className="homeSystemDetails"><summary>System activity</summary><section className="scientificMetrics">
          <Metric icon="▣" label="Live Investigations" value={investigations.length.toLocaleString()} note={investigations.length ? "living and replayable" : "ready for first investigation"}/>
          <Metric icon="▤" label="Connectors" value={connectors.length.toLocaleString()} note={`${healthy} healthy`}/>
          <Metric icon="⌘" label="Knowledge Graph" value={graph.entities.toLocaleString()} note={`${graph.relationships.toLocaleString()} relations`}/>
          <Metric icon="♙" label="Agent Tasks" value={agentSummary.tasks.toLocaleString()} note={`${agentSummary.findings.toLocaleString()} findings`}/>
          <Metric icon="↗" label="Hypotheses" value={(workspace?.hypotheses.length ?? 0).toLocaleString()} note="in this investigation"/>
        </section></details>

        <section className="dashboardGrid">
          <div className="dashboardPrimary">
            <div className="sectionTitleRow"><div><h2>Continue your research</h2><p>Choose an investigation to explore its evidence and next step.</p></div><Link href="/investigations">See all →</Link></div>

            <div className="investigationShowcase">
              <article className="featuredInvestigation">
                <span className="featuredEyebrow">{featured ? "RECENT INVESTIGATION" : "GET STARTED"}</span>
                <h3>{workspace?.investigation.title ?? featured?.title ?? "Start your first investigation"}</h3>
                <p>{workspace?.investigation.summary ?? featured?.summary ?? "Explore discoveries and choose a question to investigate."}</p>
                <div className="confidenceStrip">
                  <div><span>Confidence</span><strong>{confidence ? pct(confidence) : "—"}</strong></div>
                </div>
                <div className="investigationFacts"><span><b>{workspace?.observations.length ?? 0}</b>Observations</span><span><b>{sourceCount}</b>Sources</span><span><b>{featuredFindings.length}</b>Agent Findings</span></div>
                <div className="investigationActions"><Link className="primaryAction" href={nextHref}>{nextLabel} →</Link></div>
              </article>

              <div className="investigationMiniList">
                {investigations.filter(item=>item.id!==featured?.id).slice(0,3).map(item=><Link className="miniInvestigation" href={`/investigations/${item.id}`} key={item.id}><span className="miniTag">INVESTIGATION</span><strong>{item.title}</strong><div><b>{pct(item.confidence)}</b><span>Open →</span></div></Link>)}
              </div>
            </div>
          </div>

          <details className="homeDataDetails"><summary>Explore source activity</summary><div className="dashboardSecondary">
            <section className="scienceCard evidenceFlow">
              <div className="sectionTitleRow compact"><div><h2>Recorded observations</h2><p>Signals in the system</p></div><Link href="/signal-lake">View All →</Link></div>
              <strong className="bigNumber">{signal.observations.toLocaleString()}</strong><small>observations in the Signal Lake</small>
            </section>

            <section className="scienceCard sourceDiversity">
              <div className="sectionTitleRow compact"><div><h2>Source Diversity</h2><p>Independent sources strengthening investigations</p></div></div>
              {signal.sources.slice(0,7).map((s,idx)=>{
                const max = Math.max(...signal.sources.map(x=>x.count), 1);
                return <div className="sourceBarRow" key={s.source}><span><i className={`sourceDot s${idx}`}/>{s.source}</span><b><i style={{width:`${Math.max(12,(s.count/max)*100)}%`}}/></b><em>{s.count}</em></div>
              })}
            </section>
          </div></details>
        </section>

        <details className="homeDataDetails"><summary>Agent activity and tools</summary><div className="homeResearchGrid">
        <section className="railCard">
          <div className="sectionTitleRow compact"><div><h2>Recent agent activity</h2><p>Latest recorded tasks</p></div><Link href="/agents">View All</Link></div>
          <div className="activityList">
            {tasks.slice(0,5).map((t,i)=><div key={t.id}><span className={`agentBullet a${i}`}>◉</span><p><strong>{humanize(t.agent_id)}</strong><small>{humanize(t.task_type)}</small></p><em className={t.status}>{t.status}</em></div>)}
            {!tasks.length&&<p className="emptyRail">No recent agent activity.</p>}
          </div>
        </section>

        <section className="railCard quickActions">
          <h2>Quick Actions</h2>
          <Link className="darkButton" href="/discovery">Explore discoveries</Link>
          <Link href="/agents">♙ Agent registry</Link>
          <Link href="/signal-lake">▤ Explore Signal Lake</Link>
          <Link href="/graph">⌘ Search Knowledge Graph</Link>
          <Link href="/operations">⊙ View Operations</Link>
        </section>

        <section className="railCard recentFindings">
          <div className="sectionTitleRow compact"><h2>Recent Findings</h2><Link href="/agents">View All</Link></div>
          {(featuredFindings.length ? featuredFindings : findings.slice(0,4)).map(f=><div key={f.id}><span className={`findingIcon sev-${f.severity}`}>{f.severity === "critical" ? "×" : f.severity === "warning" ? "!" : "i"}</span><p><strong>{f.title}</strong><small>{humanize(f.category)}</small></p></div>)}
          {!featuredFindings.length && !findings.length && <p className="emptyRail">Agent findings will appear here after an audited review.</p>}
        </section>
        </div></details>
      </main>
    </StudioFrame>
  );
}

function Metric({icon,label,value,note}:{icon:string;label:string;value:string;note:string}) {
  return <div className="scienceMetric"><span className="metricIcon">{icon}</span><div><p>{label}</p><strong>{value}</strong><small>{note}</small></div></div>;
}
function humanize(value:string){ return value.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase()); }

