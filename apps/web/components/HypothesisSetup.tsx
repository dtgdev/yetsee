"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiPost } from "../lib/api";

type Hypothesis = { id: string; title: string; description: string | null; prior_confidence: number; confidence: number };
type Observation = { id: string; source: string; topic: string; metric: string; value: number | null; observed_at: string };
type Link = { id: string; hypothesis_id: string; observation_id: string; stance: string; rationale: string | null };
type Stance = "supporting" | "contradicting" | "neutral";

export default function HypothesisSetup({ investigationId, researchQuestion, hypotheses, observations, links, literatureCount }: {
  investigationId: string;
  researchQuestion: string | null;
  hypotheses: Hypothesis[];
  observations: Observation[];
  links: Link[];
  literatureCount: number;
}) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState(hypotheses[0]?.id ?? "");
  const [created, setCreated] = useState<Hypothesis | null>(null);
  const [recentLinks, setRecentLinks] = useState<Link[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [prior, setPrior] = useState(50);
  const [observationId, setObservationId] = useState("");
  const [stance, setStance] = useState<Stance>("supporting");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const choices = created && !hypotheses.some(item => item.id === created.id) ? [...hypotheses, created] : hypotheses;
  const active = choices.find(item => item.id === selectedId) ?? choices[0];
  const linked = [...links, ...recentLinks.filter(item => !links.some(link => link.id === item.id))].filter(link => link.hypothesis_id === active?.id);
  const available = observations.filter(item => !linked.some(link => link.observation_id === item.id));
  const chosenObservation = available.find(item => item.id === observationId);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const claim = title.trim();
    if (!claim) { setError("Write a claim that can be tested against evidence."); return; }
    if (!Number.isFinite(prior) || prior < 0 || prior > 100) { setError("Initial confidence must be between 0 and 100%."); return; }
    setBusy(true); setError(""); setMessage("");
    try {
      const created = await apiPost<Hypothesis>(`/api/v1/investigations/${investigationId}/hypotheses`, {
        title: claim, description: description.trim() || null, confidence: prior / 100,
      });
      setCreated(created);
      setSelectedId(created.id);
      setTitle(""); setDescription("");
      setMessage("Hypothesis recorded. Now classify an observation against it.");
      router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create hypothesis."); }
    finally { setBusy(false); }
  }

  async function link(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!active || !chosenObservation) { setError("Choose an observation from this investigation."); return; }
    if (!rationale.trim()) { setError("Explain why this observation has the selected stance."); return; }
    setBusy(true); setError(""); setMessage("");
    try {
      const saved = await apiPost<Link>(`/api/v1/investigations/${investigationId}/hypotheses/${active.id}/evidence`, {
        observation_id: chosenObservation.id, stance, weight: 1, rationale: rationale.trim(),
      });
      setRecentLinks(items => [...items, saved]);
      setObservationId(""); setRationale("");
      setMessage("Evidence linked. Hypothesis confidence and investigation history were recalculated.");
      router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not link observation."); }
    finally { setBusy(false); }
  }

  return <section className="hypothesisSetup" id="hypothesis-setup" aria-labelledby="hypothesis-setup-title">
    <header><div><span className="labLabel">Guided investigation</span><h2 id="hypothesis-setup-title">Define what you want to test</h2><p>Record a testable claim, then decide what each observation says about it.</p></div><span className="hypothesisSetupStep">{active ? "Step 2 of 2" : "Step 1 of 2"}</span></header>
    {researchQuestion && <p className="hypothesisResearchQuestion"><b>Investigation context</b>{researchQuestion}</p>}
    {choices.length > 0 && <div className="hypothesisSelector"><label htmlFor="hypothesis-choice">Hypothesis to examine</label><select id="hypothesis-choice" value={active?.id ?? ""} onChange={event => { setSelectedId(event.target.value); setObservationId(""); setMessage(""); setError(""); }}>{choices.map(item => <option value={item.id} key={item.id}>{item.title}</option>)}</select></div>}
    {active ? <div className="hypothesisCurrent"><div><strong>{active.title}</strong>{active.description && <p>{active.description}</p>}</div><div><span>Initial belief {Math.round(active.prior_confidence * 100)}%</span><b>Current {Math.round(active.confidence * 100)}%</b></div></div> : <p className="hypothesisSetupIntro">No hypothesis has been defined. Start with a specific claim that evidence could support or contradict.</p>}
    <details className="hypothesisCreate" open={!active ? true : undefined}><summary>{active ? "Add another hypothesis" : "Create a hypothesis"}</summary><form onSubmit={create}>
      <label>Testable claim<input value={title} onChange={event => setTitle(event.target.value)} placeholder="For example: AI infrastructure demand is increasing" maxLength={255} required /></label>
      <label>What would you expect to observe? <small>Optional</small><textarea value={description} onChange={event => setDescription(event.target.value)} rows={2} placeholder="Describe a measurable pattern and possible counter-evidence." /></label>
      <label>Initial confidence <small>before linking evidence</small><span className="hypothesisPrior"><input type="number" min={0} max={100} step={1} value={prior} onChange={event => setPrior(Number(event.target.value))} /><b>%</b></span></label>
      <p className="hypothesisBoundary">This is your starting belief, not the graph's structural support score. Recording a claim does not prove it.</p>
      <button type="submit" disabled={busy || !title.trim()}>{busy ? "Saving…" : "Record hypothesis"}</button>
    </form></details>
    {active && <div className="hypothesisEvidenceStep"><h3>Classify an observation</h3><p>Choose a recorded observation and explain whether it supports, contradicts, or provides context for this hypothesis.</p>
      {available.length ? <form onSubmit={link}><label>Observation<select required value={observationId} onChange={event => setObservationId(event.target.value)}><option value="">Choose an observation</option>{available.map(item => <option value={item.id} key={item.id}>{item.source} · {item.metric} · {item.topic}</option>)}</select></label>
        {chosenObservation && <div className="hypothesisObservationPreview"><strong>{chosenObservation.metric}: {chosenObservation.value ?? "—"}</strong><span>{chosenObservation.source} · {new Date(chosenObservation.observed_at).toLocaleDateString()}</span></div>}
        <fieldset><legend>What does it indicate?</legend>{(["supporting", "contradicting", "neutral"] as const).map(value => <label key={value}><input type="radio" name="hypothesis-stance" value={value} checked={stance === value} onChange={() => setStance(value)} />{value === "neutral" ? "Context only" : value === "supporting" ? "Supports" : "Contradicts"}</label>)}</fieldset>
        <label>Why? <textarea required value={rationale} onChange={event => setRationale(event.target.value)} rows={2} placeholder="Explain the link and any uncertainty." /></label>
        <button type="submit" disabled={busy || !observationId || !rationale.trim()}>{busy ? "Linking…" : "Link observation"}</button>
      </form> : <p className="hypothesisSetupIntro">{observations.length ? "All available observations are already classified for this hypothesis." : "No structured observations are linked to this investigation yet."}</p>}
      {linked.length > 0 && <div className="hypothesisLinked"><strong>Recorded links</strong>{linked.map(link => { const item = observations.find(observation => observation.id === link.observation_id); return <div key={link.id}><span className={link.stance}>{link.stance === "neutral" ? "context" : link.stance}</span><b>{item ? `${item.source} · ${item.metric}` : link.observation_id}</b><small>{link.rationale}</small></div>; })}</div>}
    </div>}
    {literatureCount > 0 && <p className="hypothesisBoundary">{literatureCount} canonical scientific {literatureCount === 1 ? "passage is" : "passages are"} available below. The current hypothesis confidence link accepts structured observations only; passage evidence is reviewed separately and is not silently counted in this score.</p>}
    {error && <p role="alert" className="hypothesisSetupError">{error}</p>}{message && <p role="status" className="hypothesisSetupSuccess">{message}</p>}
  </section>;
}
