export type QuestionEvidenceHierarchyStudy = {
  publication_id:string;
  pmid:string|null;
  doi:string|null;
  title:string;
  study_design:string;
  generic_quality_score:number;
  generic_quality_rating:string;
  question_fit_score:number;
  question_fit:string;
  rationale:string[];
};

export type QuestionEvidenceHierarchySummary = {
  investigation_id:string;
  research_question:string;
  question_type:string;
  classification_confidence:number;
  classification_rationale:string;
  study_count:number;
  studies:QuestionEvidenceHierarchyStudy[];
  policy:{
    question_specific_assessment:boolean;
    generic_quality_is_not_universal_hierarchy:boolean;
    canonical_evidence:boolean;
    does_not_change_evidence_count:boolean;
    algorithm:string;
  };
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const pct=(value:number)=>`${Math.round(value*100)}%`;

export default function QuestionEvidenceHierarchyPanel({summary}:{summary:QuestionEvidenceHierarchySummary}){
  if(!summary.study_count) return null;
  return <section className="questionHierarchy">
    <header className="questionHierarchyHeader">
      <div>
        <span className="questionHierarchyEyebrow">Question-specific evidence intelligence</span>
        <h2>Evidence Hierarchy for This Question</h2>
        <p>{summary.research_question}</p>
      </div>
      <div className="questionHierarchyClass">
        <strong>{humanize(summary.question_type)}</strong>
        <span>{pct(summary.classification_confidence)} classification confidence</span>
      </div>
    </header>

    <div className="questionHierarchyExplanation">
      <strong>{summary.classification_rationale}</strong>
      <span>Study quality and question fit are shown separately; a strong generic design is not automatically the strongest design for every scientific question.</span>
    </div>

    <div className="questionHierarchyList">
      {summary.studies.map(study=><article className="questionHierarchyCard" key={study.publication_id}>
        <div className="questionHierarchyTitle">
          <div>
            <span className={`questionHierarchyFit ${study.question_fit}`}>{humanize(study.question_fit)} fit</span>
            <strong>{study.title}</strong>
            <small>{humanize(study.study_design)}{study.pmid?` · PMID ${study.pmid}`:""}</small>
          </div>
          <div className="questionHierarchyScore">
            <strong>{study.question_fit_score}</strong>
            <span>question-fit score</span>
            <small>Generic quality {study.generic_quality_score} · {humanize(study.generic_quality_rating)}</small>
          </div>
        </div>
        <div className="questionHierarchyRationale">
          {study.rationale.map((item,index)=><p key={index}>{item}</p>)}
        </div>
      </article>)}
    </div>

    <p className="questionHierarchyDisclosure">Derived assessment only · {summary.policy.algorithm}. It does not change canonical evidence counts or replace formal risk-of-bias assessment.</p>
  </section>;
}
