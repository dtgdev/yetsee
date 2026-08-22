from __future__ import annotations

from urllib.error import HTTPError, URLError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB
from app.investigation_runtime.evidence_accounting import investigation_evidence_accounting
from app.models.investigation import Investigation
from app.scientific_literature.candidate_extraction import extract_investigation_claim_candidates
from app.scientific_literature.evidence import bind_passage_to_investigation, list_literature_evidence
from app.scientific_literature.evidence_profile import investigation_evidence_profiles, relationship_evidence_profile
from app.scientific_literature.grounding import ground_claim_relationship
from app.scientific_literature.pubmed import ingest_pubmed_article

router = APIRouter()


def _serialize_investigation(investigation: Investigation) -> dict:
    return {"id":investigation.id,"title":investigation.title,"slug":investigation.slug,"status":investigation.status,"confidence":investigation.confidence,"summary":investigation.summary,"hypothesis":investigation.hypothesis,"counter_thesis":investigation.counter_thesis,"attributes":investigation.attributes,"created_at":investigation.created_at.isoformat() if investigation.created_at else None,"updated_at":investigation.updated_at.isoformat() if investigation.updated_at else None}

class ScientificInvestigationRequest(BaseModel):
    title:str=Field(min_length=1,max_length=255); slug:str=Field(min_length=1,max_length=255); research_question:str=Field(min_length=1,max_length=4000); domain:str=Field(default="biomedicine",min_length=1,max_length=120)
class LiteratureEvidenceRequest(BaseModel):
    passage_id:str=Field(min_length=1); stance:str="contextual"; weight:float=Field(default=1.0,ge=0.0,le=1.0)
class GroundScientificClaimRequest(BaseModel):
    investigation_id:str=Field(min_length=1); passage_id:str=Field(min_length=1); claim_text:str=Field(min_length=1,max_length=4000); subject_kind:str=Field(min_length=1,max_length=80); subject_name:str=Field(min_length=1,max_length=255); subject_key:str=Field(min_length=1,max_length=320); predicate:str=Field(min_length=1,max_length=100); object_kind:str=Field(min_length=1,max_length=80); object_name:str=Field(min_length=1,max_length=255); object_key:str=Field(min_length=1,max_length=320); extraction_method:str=Field(default="manual",min_length=1,max_length=80); extraction_version:str=Field(default="l2-v1",min_length=1,max_length=80)

@router.post("/scientific-investigations")
def create_scientific_investigation(request:ScientificInvestigationRequest,db:DB)->dict:
    existing=db.scalar(select(Investigation).where(Investigation.slug==request.slug))
    if existing is not None:return {"created":False,"investigation":_serialize_investigation(existing)}
    investigation=Investigation(title=request.title,slug=request.slug,status="collecting",confidence=0.0,summary=request.research_question,hypothesis=None,counter_thesis=None,attributes={"investigation_type":"scientific_literature","research_question":request.research_question,"domain":request.domain,"evidence_policy":{"canonical_sources":["scientific_passage"],"derived_claims_are_evidence":False,"memory_is_evidence":False}})
    db.add(investigation);db.commit();db.refresh(investigation);return {"created":True,"investigation":_serialize_investigation(investigation)}

@router.post("/scientific-literature/pubmed/{pmid}/ingest")
def ingest_pubmed(pmid:str,db:DB)->dict:
    try: publication,passages,created=ingest_pubmed_article(db,pmid)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except (HTTPError,URLError,TimeoutError) as exc: raise HTTPException(status_code=502,detail="PubMed retrieval failed") from exc
    return {"created":created,"publication":{"id":publication.id,"source_system":publication.source_system,"source_id":publication.source_id,"pmid":publication.pmid,"doi":publication.doi,"title":publication.title,"journal":publication.journal,"publication_date":publication.publication_date.isoformat() if publication.publication_date else None,"authors":publication.authors_json,"source_url":publication.source_url,"retrieval_ref":publication.retrieval_ref,"content_hash":publication.content_hash,"metadata":publication.metadata_json},"passages":[{"id":p.id,"publication_id":p.publication_id,"section":p.section,"locator":p.locator,"text":p.text,"content_hash":p.content_hash,"provenance":p.provenance_json} for p in passages]}

@router.post("/investigations/{investigation_id}/literature-evidence")
def add_literature_evidence(investigation_id:str,request:LiteratureEvidenceRequest,db:DB)->dict:
    try: link,created=bind_passage_to_investigation(db,investigation_id,request.passage_id,stance=request.stance,weight=request.weight)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"created":created,"evidence_link_id":link.id,"investigation_id":link.investigation_id,"scientific_passage_id":link.scientific_passage_id,"stance":link.stance,"weight":link.weight,"canonical_evidence":True,"evidence_kind":"scientific_passage"}

@router.get("/investigations/{investigation_id}/literature-evidence")
def investigation_literature_evidence(investigation_id:str,db:DB)->list[dict]:
    try:return list_literature_evidence(db,investigation_id)
    except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/investigations/{investigation_id}/claim-candidates")
def investigation_claim_candidates(investigation_id:str,db:DB)->list[dict]:
    try:return extract_investigation_claim_candidates(db,investigation_id)
    except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/investigations/{investigation_id}/evidence-accounting")
def investigation_canonical_evidence_accounting(investigation_id:str,db:DB)->dict:
    if db.get(Investigation,investigation_id) is None:raise HTTPException(status_code=404,detail="Investigation not found")
    return investigation_evidence_accounting(db,investigation_id)

@router.get("/investigations/{investigation_id}/evidence-profiles")
def investigation_scientific_evidence_profiles(investigation_id:str,db:DB)->list[dict]:
    try:return investigation_evidence_profiles(db,investigation_id=investigation_id)
    except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/investigations/{investigation_id}/relationships/{relationship_id}/evidence-profile")
def investigation_relationship_evidence_profile(investigation_id:str,relationship_id:str,db:DB)->dict:
    try:return relationship_evidence_profile(db,investigation_id=investigation_id,relationship_id=relationship_id)
    except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/scientific-literature/claims/ground")
def ground_scientific_claim(request:GroundScientificClaimRequest,db:DB)->dict:
    try: claim,relationship,created=ground_claim_relationship(db,investigation_id=request.investigation_id,passage_id=request.passage_id,claim_text=request.claim_text,subject_kind=request.subject_kind,subject_name=request.subject_name,subject_key=request.subject_key,predicate=request.predicate,object_kind=request.object_kind,object_name=request.object_name,object_key=request.object_key,extraction_method=request.extraction_method,extraction_version=request.extraction_version)
    except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"created":created,"investigation_id":request.investigation_id,"claim":{"id":claim.id,"publication_id":claim.publication_id,"passage_id":claim.passage_id,"claim_text":claim.claim_text,"claim_type":claim.claim_type,"extraction_method":claim.extraction_method,"extraction_version":claim.extraction_version,"canonical_evidence":claim.canonical_evidence,"extraction":claim.extraction_json},"relationship":{"id":relationship.id,"source_entity_id":relationship.source_entity_id,"target_entity_id":relationship.target_entity_id,"kind":relationship.kind,"confidence":relationship.confidence,"evidence_ids":relationship.evidence_ids,"provenance":relationship.provenance}}
