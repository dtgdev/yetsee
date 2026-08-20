"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ScientificDecisionPanel from "./ScientificDecisionPanel";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

type Mission = { id: string; status: string; objective?: string };

export default function InvestigationAgentActions({ investigationId }: { investigationId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [decisionMission, setDecisionMission] = useState<Mission | null>(null);
  const [missionsLoaded, setMissionsLoaded] = useState(false);

  async function loadDecisionMission() {
    try {
      const response = await fetch(`/api/investigations/${investigationId}/missions`, { cache: "no-store" });
      if (!response.ok) return;
      const body = await response.json();
      const missions: Mission[] = Array.isArray(body) ? body : [];
      // Decisions belong to completed scientific work. Prefer the newest completed
      // mission, but keep the section visible even when the mission console's
      // synthesis lookup cannot resolve its finding metadata.
      setDecisionMission(missions.find(m => m.status === "completed") ?? missions[0] ?? null);
    } finally {
      setMissionsLoaded(true);
    }
  }

  useEffect(() => { void loadDecisionMission(); }, [investigationId]);

  async function run(path: string, label: string) {
    setBusy(label);
    setMessage(null);
    try {
      const response = await fetch(`${API}${path}`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Request failed");
      setMessage(`${label} completed.`);
      await loadDecisionMission();
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(null);
    }
  }

  return <>
    <div className="agentActions">
      <button disabled={!!busy} onClick={() => run(`/api/v1/investigations/${investigationId}/agents/evidence/run`, "Evidence Agent")}>Run Evidence Agent</button>
      <button disabled={!!busy} onClick={() => run(`/api/v1/investigations/${investigationId}/refresh`, "Investigation refresh")}>Refresh Investigation</button>
      {message && <span className="muted">{message}</span>}
    </div>

    {decisionMission ? (
      <ScientificDecisionPanel
        investigationId={investigationId}
        missionId={decisionMission.id}
        onMissionCreated={async () => {
          await loadDecisionMission();
          router.refresh();
        }}
      />
    ) : missionsLoaded ? (
      <section className="scientificDecisionPanel">
        <div className="scientificDecisionHeader">
          <div>
            <span className="labLabel">Scientific decision</span>
            <h3>Convert synthesis into an explicit next action</h3>
            <p>Decision unavailable — no persisted mission exists yet. Create and run a mission in Mission Control first.</p>
          </div>
        </div>
      </section>
    ) : null}
  </>;
}
