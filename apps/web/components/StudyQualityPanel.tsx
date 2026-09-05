export type StudyQualityAssessment = {
  publication_id:string;
  pmid:string|null;
  doi:string|null;
  title:string;
  study_design:string;
  evidence_level:string;
  quality_score:number;
  quality_rating:string;
  assessment_confidence:number;
  dimensions:{
    design:{score:number;rationale:string};
    sample_size:{value:number|null;score_adjustment:number;evidence:string|null;rationale:string};
    method_signals:{name:string;points:number;rationale:string}[];
  };
  limitations:string[];
  policy:{derived_quality_assessment:boolean;canonical_evidence:boolean;formal_risk_of_bias:boolean;algorithm:string};
  investigation_evidence:{stances:string[];evidence_link_count:number;passage_count:number};
};

export type StudyQualitySummary = {
  investigation_id:string;
  study_count:number;
  mean_quality_score:number|null;
  high_or_moderate_quality_count:number;
  studies:StudyQualityAssessment[];
  policy:{derived_quality_assessment:boolean;does_not_change_evidence_count:boolean;formal_risk_of_bias:boolean;algorithm:string};
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const pct=(value:number)=>`${Math.round(value*100)}%`;

export default function StudyQualityPanel({summary}:{summary:StudyQualitySummary}){
  if(!summary.study_count) return null;
  return <section className="studyQuality">
    <header className="studyQualityHeader">
      <div><span className="studyQualityEyebrow">Derived evidence intelligence</span><h2>Study Quality Intelligence</h2><p>Transparent study-strength signals derived from currently stored publication metadata and passages. Ratings do not change canonical evidence counts.</p></div>
      <span className="studyQualityPolicy">Not formal risk of bias</span>
    </header>
    <div className="studyQualitySummary">
      <div><strong>{summary.study_count}</strong><span>studies assessed</span></div>
      <div><strong>{summary.high_or_moderate_quality_count}</strong><span>high / moderate</span></div>
      <div><strong>{summary.mean_quality_score??"—"}</strong><span>mean signal score</span></div>
    </div>
    <div className="studyQualityList">{summary.studies.map(study=><article className="studyQualityCard" key={study.publication_id}>
      <div className="studyQualityTitle"><div><span className={`studyQualityRating ${study.quality_rating}`}>{humanize(study.quality_rating)}</span><strong>{study.title}</strong><small>{humanize(study.study_design)}{study.pmid?` · PMID ${study.pmid}`:""}</small></div><div className="studyQualityScore"><strong>{study.quality_score}</strong><span>signal score</span><small>{pct(study.assessment_confidence)} assessment confidence</small></div></div>
      <div className="studyQualityDimensions">
        <div><span>Design</span><strong>{humanize(study.evidence_level)} evidence level</strong><small>{study.dimensions.design.rationale}</small></div>
        <div><span>Sample size</span><strong>{study.dimensions.sample_size.value??"Not established"}</strong><small>{study.dimensions.sample_size.rationale}</small></div>
        <div><span>Explicit method signals</span><strong>{study.dimensions.method_signals.length||"None detected"}</strong><small>{study.dimensions.method_signals.map(signal=>humanize(signal.name)).join(" · ")||"No additional method signals established from available text."}</small></div>
      </div>
      <footer><span>Derived assessment · {study.policy.algorithm}</span><span>{study.investigation_evidence.stances.map(humanize).join(" · ")} · {study.investigation_evidence.passage_count} canonical passage{study.investigation_evidence.passage_count===1?"":"s"}</span></footer>
    </article>)}</div>
    <p className="studyQualityDisclosure">Quality ratings are explainable heuristic assessments, not probabilities that a study is correct. Missing metadata remains unknown rather than inferred. Formal risk-of-bias assessment requires richer structured evidence.</p>
  </section>;
}
