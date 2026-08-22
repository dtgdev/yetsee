"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ScientificDecisionPanel from "./ScientificDecisionPanel";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

type Mission = { id: string; status: string; objective?: string };
type EvidenceSource = {pmid:string|null;doi:string|null;title:string;stance:string;weight:number};
type EvidenceProfile = {
  relationship_id:string;
  subject:string;
  predicate:string;
  object:string;
  supporting_count:number;
  contradicting_count:number;
  independent_publication_count:number;
  agreement:string;
  strength:string;
  sources:EvidenceSource[];
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function InvestigationAgentActions({ investigationId }: { investigationId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [decisionMission, setDecisionMission] = useState<Mission | null>(null);
  const [missionsLoaded, setMissionsLoaded] = useState(false);
  const [profiles,setProfiles]=useState<EvidenceProfile[]>([]);

  async function loadEvidenceProfiles(){
    try{
      const response=await fetch(`/api/v1/investigations/${investigationId}/evidence-profiles`,{cache:"no-store"});
      if(!response.ok)return;
      const body=await response.json();
      setProfiles(Array.isArray(body)?body:[]);
    }catch{return;}
  }

  async function loadDecisionMission() {
    try {
      const response = await fetch(`/api/investigations/${investigationId}/missions`, { cache: "no-store" });
      if (!response.ok) return;
      const body = await response.json();
      const missions: Mission[] = Array.isArray(body) ? body : [];
      setDecisionMission(missions.find(m => m.status === "completed") ?? missions[0] ?? null);
    } finally {
      setMissionsLoaded(true);
    }
  }

  useEffect(() => { void loadDecisionMission(); void loadEvidenceProfiles(); }, [investigationId]);

  async function run(path: string, label: string) {
    setBusy(label);
    setMessage(null);
    try {
      const response = await fetch(`${API}${path}`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Request failed");
      setMessage(`${label} completed.`);
      await Promise.all([loadDecisionMission(),loadEvidenceProfiles()]);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(null);
    }
  }

  const primaryProfile=profiles[0];

  return <>
    {primaryProfile&&<section className="scientificEvidenceProfiles investigationEvidenceHero">
      <header>
        <div>
          <span className="labLabel">Scientific evidence</span>
          <h3>{primaryProfile.subject} → {humanize(primaryProfile.predicate)} → {primaryProfile.object}</h3>
          <p>{humanize(primaryProfile.strength)} evidence · {humanize(primaryProfile.agreement)} · {primaryProfile.independent_publication_count} independent {primaryProfile.independent_publication_count===1?"study":"studies"}</p>
        </div>
        <span className="evidenceBoundary">Evidence ≠ Interpretation</span>
      </header>
      <div className="evidenceCounts">
        <span><b>{primaryProfile.supporting_count}</b> supporting</span>
        <span><b>{primaryProfile.contradicting_count}</b> contradicting</span>
        <span><b>{primaryProfile.independent_publication_count}</b> independent studies</span>
      </div>
      <Link className="tinyLink" href={`/investigations/${investigationId}?lens=evidence`}>View scientific evidence →</Link>
    </section>}

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