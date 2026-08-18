"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

export default function InvestigationMissionActions({ investigationId }: { investigationId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runTeam() {
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`${API}/api/v1/investigations/${investigationId}/agents/run`, {
        method: "POST",
      });
      const body = await response.json();
      if (!response.ok) {
        const detail = typeof body?.detail === "string" ? body.detail : "Investigation team failed";
        throw new Error(detail);
      }
      const completed = Array.isArray(body?.tasks) ? body.tasks.length : 0;
      setMessage(`Investigation team completed ${completed} audited task${completed === 1 ? "" : "s"}.`);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Investigation team failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="missionActions">
      <button className="missionPrimaryAction" disabled={busy} onClick={runTeam}>
        {busy ? "Running scientific team…" : "Run Investigation Team"}
      </button>
      <span>Evidence → critique → structure → opportunity → quality → synthesis</span>
      {message && <p className="missionActionMessage">{message}</p>}
    </div>
  );
}
