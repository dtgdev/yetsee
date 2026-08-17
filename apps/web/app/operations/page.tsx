import { apiGet } from "../../lib/api";
import { StudioFrame } from "../../components/StudioChrome";
import { Metric, ResearchMetrics, ResearchPage, ResearchPanel, StatusPill } from "../../components/ResearchWorkspace";

export const dynamic="force-dynamic";
type Connector={id:string;version:string;description:string;schedule:string;state:null|{last_success_at:string|null;last_error_at:string|null;consecutive_failures:number;health:string}};
type Command={id:string;command_id:string;command_type:string;aggregate_type:string;aggregate_id:string|null;correlation_id:string;causation_id:string|null;status:string;error:string|null;requested_at:string};
export default async function OperationsPage(){
 const [connectors,commands]=await Promise.all([apiGet<Connector[]>("/api/v1/connectors"),apiGet<Command[]>("/api/v1/kernel/commands?limit=50")]);
 const healthy=connectors.filter(c=>c.state?.health==="healthy").length; const failed=commands.filter(c=>c.status==="failed").length;
 return <StudioFrame active="Operations"><ResearchPage eyebrow="Runtime Operations" title="Operations" subtitle="Monitor evidence-source health and audit every command executed by the investigation kernel.">
  <ResearchMetrics><Metric label="Connectors" value={connectors.length}/><Metric label="Healthy" value={healthy} tone="green"/><Metric label="Recent commands" value={commands.length} tone="blue"/><Metric label="Failures" value={failed} tone={failed?"red":"green"}/></ResearchMetrics>
  <div className="researchTwoCol wideLeft">
   <ResearchPanel title="Connector health" subtitle="External evidence sources and ingestion state."><div className="connectorHealthGrid">{connectors.map(c=><div className="connectorHealthCard" key={c.id}><div><span className="connectorIcon">↯</span><div><strong>{c.id}</strong><small>v{c.version} · {c.schedule}</small></div></div><StatusPill tone={c.state?.health==="healthy"?"green":c.state?.health?"red":"slate"}>{c.state?.health??"never run"}</StatusPill><p>{c.description}</p><footer><span>{c.state?.last_success_at?`Last success ${new Date(c.state.last_success_at).toLocaleString()}`:"Not run yet"}</span><span>{c.state?.consecutive_failures??0} failures</span></footer></div>)}</div></ResearchPanel>
   <ResearchPanel title="System summary" subtitle="Scientific runtime posture." className="stickyPanel"><div className="systemSummaryList"><div><span>Kernel</span><b>Healthy</b></div><div><span>Evidence mutation policy</span><b>Immutable</b></div><div><span>Command model</span><b>Audited</b></div><div><span>History</span><b>Append-only</b></div></div></ResearchPanel>
  </div>
  <ResearchPanel title="Kernel command history" subtitle="Correlation and causation make every system action traceable."><div className="commandTableV2"><div className="tableHeader"><span>Command</span><span>Target</span><span>Correlation</span><span>Status</span><span>Requested</span></div>{commands.map(c=><div className="tableRow" key={c.id}><div><strong>{c.command_type}</strong><small>cmd {c.command_id.slice(0,8)}</small></div><span>{c.aggregate_type}<small>{c.aggregate_id?.slice(0,8)??"global"}</small></span><span>{c.correlation_id.slice(0,8)}{c.causation_id&&<small>← {c.causation_id.slice(0,8)}</small>}</span><StatusPill tone={c.status==="completed"?"green":c.status==="failed"?"red":"amber"}>{c.status}</StatusPill><span>{new Date(c.requested_at).toLocaleString()}</span></div>)}</div></ResearchPanel>
 </ResearchPage></StudioFrame>
}
