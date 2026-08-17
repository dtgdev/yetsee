import { apiGet } from "../../lib/api";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";

export const dynamic = "force-dynamic";
type Agent={id:string;version:string;role:string;description:string;capabilities:string[];permissions:string[]};
type Summary={agents:number;tasks:number;runs:number;findings:number;task_statuses:{status:string;count:number}[]};
type Task={id:string;task_type:string;agent_id:string;status:string;target_type?:string;target_id?:string;created_at:string};
type Finding={id:string;agent_id:string;category:string;severity:string;stance:string;confidence:number;title:string;detail:string;evidence_ids:string[]};
async function safeGet<T>(p:string,f:T){try{return await apiGet<T>(p)}catch{return f}}
export default async function AgentsPage(){
 const [agents,summary,tasks,findings]=await Promise.all([safeGet<Agent[]>("/api/v1/agents",[]),safeGet<Summary>("/api/v1/agent-plane/summary",{agents:0,tasks:0,runs:0,findings:0,task_statuses:[]}),safeGet<Task[]>("/api/v1/agent-tasks?limit=20",[]),safeGet<Finding[]>("/api/v1/agent-findings?limit=30",[])]);
 const completed=tasks.filter(t=>t.status==="completed").length;
 return <StudioFrame active="Agents"><ResearchPage eyebrow="Audited Coordination" title="Agent Plane" subtitle="Specialist agents critique investigations through typed tasks. Engines compute; canonical evidence remains immutable.">
  <ResearchMetrics><Metric label="Registered agents" value={summary.agents}/><Metric label="Audited tasks" value={summary.tasks} tone="blue"/><Metric label="Completed" value={completed} tone="green"/><Metric label="Findings" value={summary.findings} tone="amber"/></ResearchMetrics>
  <ResearchPanel title="Agent registry" subtitle="Stable roles with bounded permissions." action={<StatusPill tone="green">No evidence mutation</StatusPill>}>
   <div className="agentRegistryV2">{agents.map(a=><article key={a.id}><div className="agentRoleHead"><span className="agentOrb">◉</span><div><h3>{a.role}</h3><small>{a.id} · v{a.version}</small></div></div><p>{a.description}</p><div className="capabilityWrap">{a.capabilities.map(c=><span key={c}>{c}</span>)}</div><div className="permissionWrap">{a.permissions.map(p=><code key={p}>{p}</code>)}</div></article>)}</div>
  </ResearchPanel>
  <div className="researchTwoCol">
   <ResearchPanel title="Task ledger" subtitle="Every agent action is auditable."><div className="ledgerList">{tasks.map(t=><div key={t.id}><div><strong>{t.agent_id}</strong><span>{t.task_type}</span></div><div><StatusPill tone={t.status==="completed"?"green":"amber"}>{t.status}</StatusPill><time>{new Date(t.created_at).toLocaleString()}</time></div></div>)}{!tasks.length&&<p className="emptyText">No agent tasks yet.</p>}</div></ResearchPanel>
   <ResearchPanel title="Latest findings" subtitle="Findings challenge understanding; they are never source-of-truth."><div className="findingListV2">{findings.slice(0,12).map(f=><div key={f.id}><span className={`findingDot ${f.severity}`}>!</span><div><strong>{f.title}</strong><p>{f.detail}</p><small>{f.agent_id} · {f.category}</small></div><div><b>{Math.round(f.confidence*100)}%</b><span>{f.evidence_ids.length} evidence</span></div></div>)}{!findings.length&&<p className="emptyText">No findings yet.</p>}</div></ResearchPanel>
  </div>
 </ResearchPage></StudioFrame>
}
