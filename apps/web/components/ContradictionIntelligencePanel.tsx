export type ContradictionSource={
  candidate_id:string;
  publication_id:string;
  pmid:string|null;
  assertion_text:string;
  review_status:string;
};

export type ContradictionPair={
  left_candidate_id:string;
  right_candidate_id:string;
  left_publication_id:string;
  right_publication_id:string;
  left_pmid:string|null;
  right_pmid:string|null;
  status:string;
  semantic_status?:string;
  confidence:number;
  rationale:string;
  review_rationale?:string;
  left_polarity?:string;
  right_polarity?:string;
  context_comparison?:{status:string;confidence:number;divergent_dimensions:string[];aligned_dimensions:string[];rationale:string;dimensions:{dimension:string;status:string;left:string[];right:string[]}[]};
};

export type ContradictionGroup={
  relationship:{subject:{name:string;key:string};predicate:string;object:{name:string;key:string}};
  source_count:number;
  publication_count:number;
  overall_status:string;
  agreement_pair_count:number;
  direct_contradiction_pair_count:number;
  reviewed_agreement_pair_count:number;
  provisional_agreement_pair_count:number;
  reviewed_contradiction_pair_count:number;
  provisional_tension_pair_count:number;
  contextual_divergence_pair_count:number;
  context_aligned_pair_count:number;
  pairwise_assessments:ContradictionPair[];
  sources:ContradictionSource[];
};

export type ContradictionSummary={
  investigation_id:string;
  claim_group_count:number;
  agreement_group_count:number;
  direct_contradiction_group_count:number;
  reviewed_agreement_group_count:number;
  provisional_agreement_group_count:number;
  reviewed_contradiction_group_count:number;
  provisional_tension_group_count:number;
  contextual_divergence_group_count:number;
  groups:ContradictionGroup[];
  policy:{derived_contradiction_assessment:boolean;canonical_evidence:boolean;does_not_change_evidence_count:boolean;algorithm:string};
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function ContradictionIntelligencePanel({summary}:{summary:ContradictionSummary}){
  if(!summary.claim_group_count) return null;
  return <section className="contradictionIntel">
    <header className="contradictionIntelHeader">
      <div>
        <span className="contradictionIntelEyebrow">Derived consistency intelligence</span>
        <h2>Contradiction Intelligence</h2>
        <p>Compares normalized scientific claims only when their subject, predicate, and object match, separates reviewed conclusions from provisional states, and explains contextual differences that may account for apparent disagreement.</p>
      </div>
      <span className="contradictionIntelPolicy">Explainable · deterministic</span>
    </header>

    <div className="contradictionIntelSummary">
      <div><strong>{summary.claim_group_count}</strong><span>claim groups</span></div>
      <div><strong>{summary.reviewed_agreement_group_count}</strong><span>reviewed agreement</span></div>
      <div><strong>{summary.provisional_agreement_group_count}</strong><span>provisional agreement</span></div>
      <div><strong>{summary.reviewed_contradiction_group_count}</strong><span>reviewed contradictions</span></div>
      <div><strong>{summary.provisional_tension_group_count}</strong><span>provisional tensions</span></div>
      <div><strong>{summary.contextual_divergence_group_count}</strong><span>context divergence</span></div>
    </div>

    <div className="contradictionIntelList">
      {summary.groups.map((group,index)=><article className="contradictionIntelCard" key={group.relationship.subject.key+":"+group.relationship.predicate+":"+group.relationship.object.key+":"+index}>
        <div className="contradictionIntelTitle">
          <div>
            <span className={"contradictionStatus "+group.overall_status}>{humanize(group.overall_status)}</span>
            <strong>{group.relationship.subject.name} → {group.relationship.object.name}</strong>
            <small>{humanize(group.relationship.predicate)} · {group.publication_count} distinct publication{group.publication_count===1?"":"s"}</small>
          </div>
          <div className="contradictionIntelCounts">
            <strong>{group.reviewed_agreement_pair_count}</strong><span>reviewed agree</span>
            <strong>{group.provisional_agreement_pair_count}</strong><span>provisional agree</span>
            <strong>{group.reviewed_contradiction_pair_count}</strong><span>reviewed contradict</span>
            <strong>{group.provisional_tension_pair_count}</strong><span>provisional tension</span>
          </div>
        </div>
        {group.pairwise_assessments.length>0&&<div className="contradictionPairs">
          {group.pairwise_assessments.map((pair,pairIndex)=><div className="contradictionPair" key={pair.left_candidate_id+":"+pair.right_candidate_id+":"+pairIndex}>
            <div><strong>{humanize(pair.status)}</strong><span>{Math.round(pair.confidence*100)}% assessment confidence</span></div>
            <p>{pair.rationale}</p>{pair.review_rationale&&<p>{pair.review_rationale}</p>}
            {pair.context_comparison&&<div className={"contextComparison "+pair.context_comparison.status}><strong>{humanize(pair.context_comparison.status)}</strong><p>{pair.context_comparison.rationale}</p>{pair.context_comparison.divergent_dimensions.length>0&&<small>Divergent: {pair.context_comparison.divergent_dimensions.map(humanize).join(" · ")}</small>}{pair.context_comparison.aligned_dimensions.length>0&&<small>Aligned: {pair.context_comparison.aligned_dimensions.map(humanize).join(" · ")}</small>}</div>}
            <small>{pair.left_pmid?"PMID "+pair.left_pmid:"Publication A"} ↔ {pair.right_pmid?"PMID "+pair.right_pmid:"Publication B"}</small>
          </div>)}
        </div>}
        {group.pairwise_assessments.length===0&&<p className="contradictionSingle">Only one source currently supports this normalized claim, so cross-publication contradiction cannot yet be assessed.</p>}
      </article>)}
    </div>

    <p className="contradictionIntelDisclosure">Derived assessment only · {summary.policy.algorithm}. It does not modify canonical evidence, publication counts, or claim review decisions.</p>
  </section>;
}
