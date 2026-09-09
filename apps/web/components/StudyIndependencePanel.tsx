export type StudyIndependenceSummary={
  investigation_id:string;
  publication_count:number;
  overall_status:string;
  confirmed_independent_pair_count:number;
  same_trial_pair_count:number;
  unresolved_pair_count:number;
  studies:{publication_id:string;pmid:string|null;doi:string|null;title:string;publication_date:string|null;clinical_trial_ids:string[];publication_types:string[];mesh_terms:string[]}[];
  pairwise_assessments:{left_publication_id:string;right_publication_id:string;status:string;confidence:number;shared_trial_ids:string[];left_trial_ids:string[];right_trial_ids:string[];shared_author_count:number;author_overlap:number;rationale:string;policy:{derived_independence_assessment:boolean;canonical_evidence:boolean;algorithm:string}}[];
  policy:{publication_count_is_not_study_count:boolean;derived_independence_assessment:boolean;does_not_change_canonical_evidence:boolean;algorithm:string;strong_signal_priority:string[];weak_signal_only:string[]};
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function StudyIndependencePanel({summary}:{summary:StudyIndependenceSummary}){
  if(!summary.publication_count)return null;
  const confirmed=summary.overall_status==="confirmed_independent_trials";
  return <section className="studyIndependence">
    <header className="studyIndependenceHeader">
      <div><span className="studyIndependenceEyebrow">Derived replication intelligence</span><h2>Study Independence</h2><p>Separates publication count from underlying trial or cohort independence using explicit study identifiers first.</p></div>
      <span className={`studyIndependenceStatus ${confirmed?"positive":"neutral"}`}>{humanize(summary.overall_status)}</span>
    </header>
    <div className="studyIndependenceSummary">
      <div><strong>{summary.publication_count}</strong><span>publications</span></div>
      <div><strong>{summary.confirmed_independent_pair_count}</strong><span>confirmed independent pairs</span></div>
      <div><strong>{summary.same_trial_pair_count}</strong><span>same-trial pairs</span></div>
      <div><strong>{summary.unresolved_pair_count}</strong><span>unresolved pairs</span></div>
    </div>
    <div className="studyIndependenceStudies">{summary.studies.map(study=><article key={study.publication_id}>
      <div><strong>{study.title}</strong><small>{study.pmid?`PubMed ${study.pmid}`:"Scientific publication"}</small></div>
      <div className="trialIds">{study.clinical_trial_ids.length?study.clinical_trial_ids.map(id=><span key={id}>{id}</span>):<span>Trial ID not established</span>}</div>
    </article>)}</div>
    {summary.pairwise_assessments.map(pair=><div className="studyIndependenceRationale" key={`${pair.left_publication_id}:${pair.right_publication_id}`}><strong>{humanize(pair.status)} · {Math.round(pair.confidence*100)}% assessment confidence</strong><p>{pair.rationale}</p></div>)}
    <p className="studyIndependenceDisclosure">Derived assessment only. It does not merge publications or change canonical evidence counts. Distinct publications are not assumed to be independent unless supported by explicit metadata.</p>
  </section>;
}
