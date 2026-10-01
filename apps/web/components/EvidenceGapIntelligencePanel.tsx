export type EvidenceGap={
  gap_type:string;
  priority:"critical"|"high"|"medium"|"low";
  title:string;
  rationale:string;
  evidence:Record<string,unknown>;
  suggested_next_evidence:string[];
};

export type EvidenceGapSummary={
  investigation_id:string;
  gap_count:number;
  priority_counts:{critical:number;high:number;medium:number;low:number};
  gaps:EvidenceGap[];
  inputs:{study_count:number;question_type:string|null;independence_status:string|null;claim_group_count:number};
  policy:{derived_gap_assessment:boolean;canonical_evidence:boolean;does_not_change_evidence_count:boolean;absence_of_evidence_is_not_evidence_of_absence:boolean;suggested_next_evidence_is_investigation_guidance:boolean;algorithm:string};
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function EvidenceGapIntelligencePanel({summary}:{summary:EvidenceGapSummary}){
  if(!summary.gap_count) return <section className="evidenceGapIntel evidenceGapIntelClear">
    <header className="evidenceGapIntelHeader">
      <div>
        <span className="evidenceGapIntelEyebrow">Derived investigation guidance</span>
        <h2>Evidence Gap Intelligence</h2>
        <p>No material evidence gaps were detected by the current deterministic rules. This does not prove the evidence base is complete.</p>
      </div>
      <span className="evidenceGapIntelPolicy">No material gaps detected</span>
    </header>
    <p className="evidenceGapIntelDisclosure">Derived assessment only · {summary.policy.algorithm}. Absence of a detected gap is not evidence that no gap exists.</p>
  </section>;

  return <section className="evidenceGapIntel">
    <header className="evidenceGapIntelHeader">
      <div>
        <span className="evidenceGapIntelEyebrow">Derived investigation guidance</span>
        <h2>Evidence Gap Intelligence</h2>
        <p>Identifies what is still missing, unresolved, weakly replicated, or awaiting review before the investigation should place greater trust in its conclusions.</p>
      </div>
      <span className="evidenceGapIntelPolicy">Explainable · deterministic</span>
    </header>

    <div className="evidenceGapIntelSummary">
      <div><strong>{summary.gap_count}</strong><span>detected gaps</span></div>
      <div><strong>{summary.priority_counts.critical}</strong><span>critical</span></div>
      <div><strong>{summary.priority_counts.high}</strong><span>high priority</span></div>
      <div><strong>{summary.priority_counts.medium}</strong><span>medium priority</span></div>
    </div>

    <div className="evidenceGapIntelList">
      {summary.gaps.map((gap,index)=><article className={"evidenceGapCard priority_"+gap.priority} key={gap.gap_type+":"+index}>
        <div className="evidenceGapCardTop">
          <div>
            <span className={"evidenceGapPriority "+gap.priority}>{gap.priority}</span>
            <h3>{gap.title}</h3>
            <small>{humanize(gap.gap_type)}</small>
          </div>
        </div>
        <p>{gap.rationale}</p>
        {gap.suggested_next_evidence.length>0&&<div className="evidenceGapNext">
          <strong>What would reduce this gap?</strong>
          <ul>{gap.suggested_next_evidence.map((item,itemIndex)=><li key={itemIndex}>{item}</li>)}</ul>
        </div>}
      </article>)}
    </div>

    <p className="evidenceGapIntelDisclosure">Derived assessment only · {summary.policy.algorithm}. It does not modify canonical evidence, study counts, review decisions, or scientific claims. Absence of evidence is not evidence of absence.</p>
  </section>;
}
