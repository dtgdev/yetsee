"use client";

import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

type Candidate = {
  candidate_id:string;
  investigation_id:string;
  claim:{
    subject:{kind:string;name:string;key:string};
    predicate:string;
    object:{kind:string;name:string;key:string};
    assertion_text:string;
  };
  extraction:{method:string;version:string;confidence:number;context_source:string;requires_review:boolean;canonical_evidence:boolean};
  provenance:{passage_id:string;publication_id:string;pmid:string|null;doi:string|null;source_url:string|null;locator:string|null};
  source_text:string;
};

type Review = {
  id:string;
  investigation_id:string;
  candidate_id:string;
  decision:"approve"|"reject";
  reviewer:string;
  rationale:string|null;
  scientific_claim_id:string|null;
  relationship_id:string|null;
  reviewed_claim:Record<string,unknown>;
  created_at:string|null;
};

type Group = {
  key:string;
  subject:string;
  predicate:string;
  object:string;
  candidates:Candidate[];
};

const humanize=(value:string)=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function ScientificClaimReviewPanel({investigationId}:{investigationId:string}){
  const [candidates,setCandidates]=useState<Candidate[]>([]);
  const [reviews,setReviews]=useState<Review[]>([]);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState<string|null>(null);
  const [expanded,setExpanded]=useState<string|null>(null);
  const [rationale,setRationale]=useState<Record<string,string>>({});
  const [message,setMessage]=useState<string|null>(null);

  async function load(){
    setLoading(true);
    try{
      const [candidateResponse,reviewResponse]=await Promise.all([
        fetch(`${API}/api/v1/investigations/${investigationId}/claim-candidates`,{cache:"no-store"}),
        fetch(`${API}/api/v1/investigations/${investigationId}/claim-candidate-reviews`,{cache:"no-store"}),
      ]);
      if(!candidateResponse.ok)throw new Error("Unable to load scientific claim candidates.");
      const candidateBody=await candidateResponse.json();
      const reviewBody=reviewResponse.ok?await reviewResponse.json():[];
      setCandidates(Array.isArray(candidateBody)?candidateBody:[]);
      setReviews(Array.isArray(reviewBody)?reviewBody:[]);
    }catch(error){
      setMessage(error instanceof Error?error.message:"Unable to load scientific claim candidates.");
    }finally{
      setLoading(false);
    }
  }

  useEffect(()=>{void load();},[investigationId]);

  const reviewsByCandidate=useMemo(()=>new Map(reviews.map(review=>[review.candidate_id,review])),[reviews]);
  const groups=useMemo<Group[]>(()=>{
    const grouped=new Map<string,Group>();
    for(const candidate of candidates){
      const key=`${candidate.claim.subject.key}|${candidate.claim.predicate}|${candidate.claim.object.key}`;
      const existing=grouped.get(key);
      if(existing){existing.candidates.push(candidate);continue;}
      grouped.set(key,{key,subject:candidate.claim.subject.name,predicate:candidate.claim.predicate,object:candidate.claim.object.name,candidates:[candidate]});
    }
    return [...grouped.values()].sort((a,b)=>b.candidates.length-a.candidates.length||a.subject.localeCompare(b.subject));
  },[candidates]);

  async function review(candidate:Candidate,decision:"approve"|"reject"){
    setBusy(candidate.candidate_id);
    setMessage(null);
    try{
      const response=await fetch(`${API}/api/v1/investigations/${investigationId}/claim-candidates/${candidate.candidate_id}/review`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({decision,reviewer:"human",rationale:rationale[candidate.candidate_id]?.trim()||null}),
      });
      const body=await response.json();
      if(!response.ok)throw new Error(body.detail||"Review could not be saved.");
      setMessage(decision==="approve"?"Approved as derived scientific knowledge. Canonical evidence is unchanged.":"Candidate rejected and preserved in the review history.");
      setExpanded(null);
      await load();
    }catch(error){
      setMessage(error instanceof Error?error.message:"Review could not be saved.");
    }finally{
      setBusy(null);
    }
  }

  if(loading)return <section className="claimReviewPanel"><div className="claimReviewEmpty">Loading suggested scientific claims…</div></section>;
  if(!candidates.length)return null;

  const pending=candidates.filter(candidate=>!reviewsByCandidate.has(candidate.candidate_id)).length;
  const approved=reviews.filter(review=>review.decision==="approve").length;
  const rejected=reviews.filter(review=>review.decision==="reject").length;

  return <section className="claimReviewPanel">
    <header className="claimReviewHeader">
      <div>
        <span className="labLabel">Suggested scientific claims</span>
        <h3>Review interpretations before they become knowledge</h3>
        <p>YetSee extracted these statements from canonical literature. Nothing enters the scientific graph until it is explicitly approved.</p>
      </div>
      <span className="evidenceBoundary">Evidence → Review → Knowledge</span>
    </header>

    <div className="claimReviewSummary">
      <span><b>{pending}</b> pending</span>
      <span className="approved"><b>{approved}</b> approved</span>
      <span className="rejected"><b>{rejected}</b> rejected</span>
      <span><b>{groups.length}</b> distinct relationships</span>
    </div>

    {message&&<div className="claimReviewMessage">{message}</div>}

    <div className="claimGroupList">
      {groups.map(group=>{
        const independentPublications=new Set(group.candidates.map(candidate=>candidate.provenance.publication_id)).size;
        return <article className="claimGroup" key={group.key}>
          <div className="claimGroupHeadline">
            <div>
              <strong>{group.subject}</strong>
              <span>→ {humanize(group.predicate)} →</span>
              <strong>{group.object}</strong>
            </div>
            <div className="claimGroupSourceCount"><b>{independentPublications}</b><span>independent {independentPublications===1?"study":"studies"}</span></div>
          </div>

          <div className="claimCandidateList">
            {group.candidates.map(candidate=>{
              const reviewState=reviewsByCandidate.get(candidate.candidate_id);
              const isOpen=expanded===candidate.candidate_id;
              return <div className={`claimCandidate ${reviewState?.decision??"pending"}`} key={candidate.candidate_id}>
                <div className="claimCandidateMain">
                  <div className="claimCandidateSource">
                    <span className={`claimStatus ${reviewState?.decision??"pending"}`}>{reviewState?reviewState.decision:"pending review"}</span>
                    <strong>{candidate.provenance.pmid?`PMID ${candidate.provenance.pmid}`:"Scientific publication"}</strong>
                    <small>{candidate.provenance.doi?`DOI ${candidate.provenance.doi} · `:""}{candidate.provenance.locator??"source passage"}</small>
                  </div>
                  <div className="claimCandidateConfidence"><b>{Math.round(candidate.extraction.confidence*100)}%</b><span>extraction confidence</span></div>
                  <button type="button" onClick={()=>setExpanded(isOpen?null:candidate.candidate_id)}>{isOpen?"Close":"Review"}</button>
                </div>

                {isOpen&&<div className="claimCandidateReview">
                  <div className="claimAssertion"><span>Source assertion</span><p>“{candidate.claim.assertion_text}”</p></div>
                  <div className="claimInterpretation"><span>Proposed interpretation</span><strong>{candidate.claim.subject.name} → {humanize(candidate.claim.predicate)} → {candidate.claim.object.name}</strong><small>Derived interpretation · not canonical evidence</small></div>
                  {candidate.provenance.source_url&&<a href={candidate.provenance.source_url} target="_blank" rel="noreferrer">Open source publication ↗</a>}

                  {reviewState?<div className="claimReviewedState">
                    <strong>{reviewState.decision==="approve"?"Approved as derived scientific knowledge":"Rejected — not promoted"}</strong>
                    {reviewState.rationale&&<p>{reviewState.rationale}</p>}
                    {reviewState.decision==="approve"&&<small>Scientific claim {reviewState.scientific_claim_id?.slice(0,8)}… · Relationship {reviewState.relationship_id?.slice(0,8)}…</small>}
                  </div>:<>
                    <label className="claimRationale"><span>Review rationale <small>optional</small></span><textarea value={rationale[candidate.candidate_id]??""} onChange={event=>setRationale(current=>({...current,[candidate.candidate_id]:event.target.value}))} placeholder="Why are you approving or rejecting this interpretation?" rows={3}/></label>
                    <div className="claimReviewActions">
                      <button type="button" className="reject" disabled={busy===candidate.candidate_id} onClick={()=>void review(candidate,"reject")}>Reject</button>
                      <button type="button" className="approve" disabled={busy===candidate.candidate_id} onClick={()=>void review(candidate,"approve")}>{busy===candidate.candidate_id?"Saving…":"Approve as knowledge"}</button>
                    </div>
                  </>}
                </div>}
              </div>;
            })}
          </div>
        </article>;
      })}
    </div>

    <footer className="claimReviewBoundary"><strong>Scientific boundary</strong><span>Approving a claim creates derived knowledge. It does not create another evidence item or change the source passage.</span></footer>
  </section>;
}
