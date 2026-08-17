"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

export default function InvestigationAgentActions({ investigationId }: { investigationId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function run(path: string, label: string) {
    setBusy(label);
    setMessage(null);
    try {
      const response = await fetch(`${API}${path}`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Request failed");
      setMessage(`${label} completed.`);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(null);
    }
  }

  return <div className="agentActions">
    <button disabled={!!busy} onClick={() => run(`/api/v1/investigations/${investigationId}/agents/evidence/run`, "Evidence Agent")}>Run Evidence Agent</button>
    <button disabled={!!busy} onClick={() => run(`/api/v1/investigations/${investigationId}/refresh`, "Investigation refresh")}>Refresh Investigation</button>
    {message && <span className="muted">{message}</span>}
  </div>;
}
