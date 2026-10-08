import Link from "next/link";

export type EvidenceProfile = {
  relationship_id: string;
  subject: string;
  predicate: string;
  object: string;
  supporting_count: number;
  contradicting_count: number;
  contextual_count: number;
  independent_publication_count: number;
  agreement: string;
  strength: string;
  sources: {
    evidence_link_id: string;
    stance: string;
    passage_id: string;
    publication_id: string;
    pmid: string | null;
    doi: string | null;
    title: string;
    source_url: string | null;
    text: string;
  }[];
};

const strengthLabels: Record<string, string> = {
  strong: "Strong linked support",
  moderate: "Moderate linked support",
  limited: "Limited linked support",
  contested: "Contested",
  insufficient: "Insufficient linked evidence",
};

function agreementLabel(profile: EvidenceProfile) {
  if (profile.agreement === "mixed") return "Supporting and contradicting passages";
  if (profile.agreement === "context_only") return "Context only";
  if (profile.agreement === "no_evidence") return "No linked passage evidence";
  if (profile.independent_publication_count < 2) return "Cross-publication agreement not assessed";
  if (profile.agreement === "supporting_consensus") return "Supporting passages across publications";
  if (profile.agreement === "contradicting_consensus") return "Contradicting passages across publications";
  return "Agreement not assessed";
}

const plural = (count: number, singular: string, other = `${singular}s`) => `${count} ${count === 1 ? singular : other}`;
const humanize = (value: string) => value.replaceAll("_", " ").toLowerCase();

export default function EvidenceStrengthPanel({ investigationId, profiles, canonicalEvidenceCount, canonicalSourceCount, observationCount }: {
  investigationId: string;
  profiles: EvidenceProfile[] | null;
  canonicalEvidenceCount: number;
  canonicalSourceCount: number;
  observationCount: number;
}) {
  const ordered = [...(profiles ?? [])].sort((a, b) => {
    const priority: Record<string, number> = { contested: 0, strong: 1, moderate: 2, limited: 3, insufficient: 4 };
    return (priority[a.strength] ?? 5) - (priority[b.strength] ?? 5) || a.subject.localeCompare(b.subject) || a.relationship_id.localeCompare(b.relationship_id);
  });

  return <section className="evidenceStrength" aria-labelledby="evidence-strength-title">
    <header>
      <div><span className="evidenceStrengthEyebrow">Evidence strength</span><h2 id="evidence-strength-title">How well are relationships supported?</h2><p>Review linked passages and distinct publications behind each scientific relationship.</p></div>
      <span className="evidenceStrengthScope">Relationship level · scientific literature</span>
    </header>
    {profiles === null ? <p className="evidenceStrengthEmpty">Relationship assessments are temporarily unavailable. Review the canonical evidence below.</p>
      : ordered.length === 0 ? <div className="evidenceStrengthEmpty"><strong>No literature relationships to rate yet</strong><p>This investigation has {plural(canonicalEvidenceCount, "canonical evidence item")} from {plural(canonicalSourceCount, "source")}, including {plural(observationCount, "observation")}. A relationship strength assessment appears after scientific passages are linked to a relationship.</p></div>
      : <div className="evidenceStrengthList">{ordered.map(profile => <article key={profile.relationship_id} className={`evidenceStrengthCard ${profile.strength}`}>
        <div className="evidenceStrengthCardHead"><div><span className="evidenceStrengthRelation">{profile.subject} <b>→</b> {profile.object}</span><small>{humanize(profile.predicate)}</small></div><strong className="evidenceStrengthRating">{strengthLabels[profile.strength] ?? humanize(profile.strength)}</strong></div>
        <p className="evidenceStrengthAgreement">{agreementLabel(profile)}</p>
        <div className="evidenceStrengthCounts"><span>{plural(profile.independent_publication_count, "distinct publication")}</span><span>{plural(profile.supporting_count, "supporting passage")}</span><span>{plural(profile.contradicting_count, "contradicting passage")}</span>{profile.contextual_count > 0 && <span>{plural(profile.contextual_count, "context passage")}</span>}</div>
        <details><summary>Inspect source passages <span>{profile.sources.length}</span></summary>
          {profile.sources.length ? <div className="evidenceStrengthSources">{profile.sources.map(source => <div key={source.evidence_link_id}>
            <div><span className={`evidenceStrengthStance ${source.stance}`}>{humanize(source.stance)}</span><strong>{source.title}</strong></div>
            <small>{source.pmid ? `PMID ${source.pmid}` : source.doi ? `DOI ${source.doi}` : "Scientific publication"}</small>
            <p>{source.text}</p>{source.source_url && <a href={source.source_url} target="_blank" rel="noreferrer">Open publication ↗</a>}
          </div>)}</div> : <p>No canonical passage is linked to this relationship in this investigation.</p>}
        </details>
      </article>)}</div>}
    <footer>Strength uses linked passage stance and distinct publications. It does not measure study quality, study independence, causal certainty, or hypothesis probability. <Link href={`/investigations/${investigationId}?lens=reasoning`}>View reasoning →</Link></footer>
  </section>;
}
