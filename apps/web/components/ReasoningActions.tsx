"use client";
import { useState } from "react";

export function RunGraphReasoner({ investigationId }: { investigationId: string }) {
  const [busy,setBusy]=useState(false); const [message,setMessage]=useState("");
  async function run(){setBusy(true);setMessage("");try{const r=await fetch(`/api/investigations/${investigationId}/reasoning/graph/run`,{method:"POST"});if(!r.ok){const b=await r.json().catch(()=>({}));throw new Error(typeof b.detail==="string"?b.detail:`Request failed (${r.status})`)}setMessage("Graph reasoning completed. Refreshing…");window.location.reload()}catch(e){setMessage(e instanceof Error?e.message:"Reasoning failed")}finally{setBusy(false)}}
  return <div className="reasoningAction"><button className="primaryAction" onClick={run} disabled={busy}>{busy?"Reasoning…":"Run Graph Reasoner"}</button>{message&&<small>{message}</small>}</div>
}
