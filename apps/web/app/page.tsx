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

  const featured = investigations[0];
  const workspace = featured ? await safeGet<Workspace| null>(`/api/v1/investigations/${featured.id}/workspace`, null) : null;
  const healthy = connectors.filter(c => c.state?.health === "healthy").length;
  const sourceCount = workspace ? new Set(workspace.observations.map(o => o.source)).size : signal.sources.length;
  const confidence = workspace?.hypotheses[0]?.confidence ?? featured?.confidence ?? 0;
  const prior = workspace?.hypotheses[0]?.prior_confidence ?? confidence;
  const confidenceDelta = Math.max(0, confidence - prior);
  const featuredFindings = workspace?.agent_findings.slice(0,3) ?? findings.slice(0,3);

  return (
    <StudioFrame active="Home">
      <main className="researchHome">
        <section className="researchHero">
          <div>
            <p className="heroKicker">SCIENTIFIC INVESTIGATION OPERATING SYSTEM</p>
            <h1>From Signals to<br/>Scientific Understanding.</h1>
            <p>YetSee turns the world&apos;s signals into auditable, evidence-backed, living investigations powered by agents and reasoning.</p>
          </div>
          <div className="knowledgeOrb" aria-hidden="true">
            <span className="orbCore" />
            <span className="orbitLabel health">Health</span>
            <span className="orbitLabel technology">Technology</span>
            <span className="orbitLabel lifestyle">Lifestyle</span>
            <span className="orbitLabel science">Science</span>
            <span className="orbitLabel markets">Markets</span>
            {Array.from({length:18}).map((_,i)=><i key={i} style={{"--i":i} as React.CSSProperties}/>) }
          </div>
        </section>

        <section className="scientificMetrics">
          <Metric icon="▣" label="Live Investigations" value={investigations.length.toLocaleString()} note={investigations.length ? "living and replayable" : "ready for first investigation"}/>
          <Metric icon="▤" label="Evidence Sources" value={connectors.length.toLocaleString()} note={`${healthy} healthy`}/>
          <Metric icon="⌘" label="Knowledge Graph" value={graph.entities.toLocaleString()} note={`${graph.relationships.toLocaleString()} relations`}/>
          <Metric icon="♙" label="Agent Tasks" value={agentSummary.tasks.toLocaleString()} note={`${agentSummary.findings.toLocaleString()} findings`}/>
          <Metric icon="↗" label="Confidence Updates" value={(workspace?.hypotheses.length ?? 0).toLocaleString()} note="audited beliefs"/>
        </section>

        <section className="dashboardGrid">
          <div className="dashboardPrimary">
            <div className="sectionTitleRow"><div><h2>Active Investigations</h2><p>Top topics evolving with evidence and reasoning signals</p></div><Link href="/investigations">View All →</Link></div>

            <div className="investigationShowcase">
              <article className="featuredInvestigation">
                <div className="investigationVisual">
                  <span className="visualTag">{featured ? "LIVE INVESTIGATION" : "READY"}</span>
                  <span className="visualPulse"><i/> LIVE</span>
                  <div className="signalHorizon"><i/><i/><i/><i/><i/><i/></div>
                </div>
                <h3>{workspace?.investigation.title ?? featured?.title ?? "Running Clubs"}</h3>
                <p>{workspace?.investigation.summary ?? featured?.summary ?? "Are running clubs becoming a broader lifestyle movement?"}</p>
                <div className="confidenceStrip">
                  <div><span>Confidence</span><strong>{confidence ? pct(confidence) : "—"}</strong></div>
                  <span className="positiveDelta">↑ {confidenceDelta ? pct(confidenceDelta) : "live"}</span>
                  <MiniSpark />
                </div>
                <div className="investigationFacts"><span><b>{workspace?.observations.length ?? 0}</b>Evidence</span><span><b>{sourceCount}</b>Sources</span><span><b>{featuredFindings.length}</b>Agent Findings</span></div>
                <div className="investigationActions">{featured ? <Link className="primaryAction" href={`/investigations/${featured.id}`}>Open Investigation →</Link> : <Link className="primaryAction" href="/discovery">Discover Opportunities →</Link>}<Link href="/operations">View Timeline</Link></div>
              </article>

              <div className="investigationMiniList">
                {(investigations.slice(1,4).length ? investigations.slice(1,4) : [
                  {id:"ai",title:"AI Coding Agents",confidence:.682,status:"technology",summary:null,updated_at:""},
                  {id:"battery",title:"Home Batteries",confidence:.624,status:"energy",summary:null,updated_at:""},
                  {id:"health",title:"GLP-1 Lifestyle",confidence:.713,status:"health",summary:null,updated_at:""},
                ]).map((item,index)=><div className="miniInvestigation" key={item.id}><span className="miniTag">{index===0?"TECHNOLOGY":index===1?"ENERGY":"HEALTH"}</span><strong>{item.title}</strong><div><b>{pct(item.confidence)}</b><span>↑ +{(4.2+index*2.1).toFixed(1)}%</span><MiniSpark /></div></div>)}
              </div>
            </div>
          </div>

          <div className="dashboardSecondary">
            <section className="scienceCard evidenceFlow">
              <div className="sectionTitleRow compact"><div><h2>Evidence Flow</h2><p>Signals entering the system</p></div><Link href="/signal-lake">View All →</Link></div>
              <strong className="bigNumber">{signal.observations.toLocaleString()}</strong><small>observations in the Signal Lake</small>
              <div className="flowChart" aria-label="Decorative evidence flow chart"><svg viewBox="0 0 420 120" role="img"><polyline points="0,95 32,78 60,88 90,62 118,72 146,42 176,57 210,28 240,47 272,31 302,54 336,20 368,35 400,18 420,29"/><polyline className="purple" points="0,104 45,98 85,91 125,87 165,72 205,77 245,65 285,69 325,54 365,59 420,48"/><polyline className="green" points="0,110 52,108 104,99 156,102 208,89 260,94 312,80 364,83 420,69"/></svg><div><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>Now</span></div></div>
            </section>

            <section className="scienceCard sourceDiversity">
              <div className="sectionTitleRow compact"><div><h2>Source Diversity</h2><p>Independent sources strengthening investigations</p></div></div>
              {(signal.sources.length ? signal.sources.slice(0,7) : [{source:"Google Trends",count:26},{source:"Reddit",count:22},{source:"News",count:18},{source:"YouTube",count:14},{source:"Academic",count:10},{source:"Jobs",count:6}]).map((s,idx)=>{
                const max = Math.max(...(signal.sources.length ? signal.sources : [{count:26}]).map(x=>x.count), 1);
                return <div className="sourceBarRow" key={s.source}><span><i className={`sourceDot s${idx}`}/>{s.source}</span><b><i style={{width:`${Math.max(12,(s.count/max)*100)}%`}}/></b><em>{s.count}</em></div>
              })}
            </section>
          </div>
        </section>

        <section className="whyStrip">
          <div><span>▤</span><p><strong>Immutable Evidence</strong>Every observation is versioned and replayable.</p></div>
          <div><span>◉</span><p><strong>Replaceable Intelligence</strong>A small kernel and swappable intelligence extensions.</p></div>
          <div><span>△</span><p><strong>Scientific Process</strong>Audited, explainable and designed for truth.</p></div>
          <blockquote>“The goal is not more information.<br/>The goal is better understanding.”<cite>— YetSee OS</cite></blockquote>
        </section>
      </main>

      <aside className="activityRail">
        <section className="railCard">
          <div className="sectionTitleRow compact"><div><h2>Live Agent Activity</h2><p>Real-time agent orchestration</p></div><Link href="/agents">View All</Link></div>
          <div className="activityList">
            {(tasks.length ? tasks.slice(0,5) : [
              {id:"1",agent_id:"Evidence Agent",task_type:"Audited Running Clubs evidence",status:"completed",created_at:"",result_json:{}},
              {id:"2",agent_id:"Signal Steward",task_type:"Ingesting Google Trends signals",status:"running",created_at:"",result_json:{}},
              {id:"3",agent_id:"Graph Analyst",task_type:"Updated investigation graph",status:"completed",created_at:"",result_json:{}},
            ]).map((t,i)=><div key={t.id}><span className={`agentBullet a${i}`}>◉</span><p><strong>{humanize(t.agent_id)}</strong><small>{humanize(t.task_type)}</small></p><em className={t.status}>{t.status}</em></div>)}
          </div>
        </section>

        <section className="railCard quickActions">
          <h2>Quick Actions</h2>
          <Link className="darkButton" href="/investigations">＋ New Investigation</Link>
          <Link href="/agents">♙ Run Agent Review</Link>
          <Link href="/signal-lake">▤ Explore Signal Lake</Link>
          <Link href="/graph">⌘ Search Knowledge Graph</Link>
          <Link href="/operations">⊙ View Operations</Link>
        </section>

        <section className="railCard recentFindings">
          <div className="sectionTitleRow compact"><h2>Recent Findings</h2><Link href="/agents">View All</Link></div>
          {(featuredFindings.length ? featuredFindings : findings.slice(0,4)).map((f,i)=><div key={f.id}><span className={`findingIcon sev-${f.severity}`}>{f.severity === "critical" ? "×" : f.severity === "warning" ? "!" : "i"}</span><p><strong>{f.title}</strong><small>{humanize(f.category)}</small></p><time>{i+2}h</time></div>)}
          {!featuredFindings.length && !findings.length && <p className="emptyRail">Agent findings will appear here after an audited review.</p>}
        </section>
      </aside>
    </StudioFrame>
  );
}

function Metric({icon,label,value,note}:{icon:string;label:string;value:string;note:string}) {
  return <div className="scienceMetric"><span className="metricIcon">{icon}</span><div><p>{label}</p><strong>{value}</strong><small>{note}</small></div></div>;
}
function MiniSpark(){return <svg className="miniSpark" viewBox="0 0 90 30" aria-hidden="true"><polyline points="0,25 12,22 23,23 34,17 45,19 56,11 67,13 78,7 90,4"/></svg>}
function humanize(value:string){ return value.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase()); }
