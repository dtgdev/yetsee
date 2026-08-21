from __future__ import annotations

from urllib.error import HTTPError, URLError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DB
from app.scientific_literature.evidence import bind_passage_to_investigation, list_literature_evidence
from app.scientific_literature.pubmed import ingest_pubmed_article

router = APIRouter()


class LiteratureEvidenceRequest(BaseModel):
    passage_id: str = Field(min_length=1)
    stance: str = "contextual"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


@router.post("/scientific-literature/pubmed/{pmid}/ingest")
def ingest_pubmed(pmid: str, db: DB) -> dict:
    try:
        publication, passages, created = ingest_pubmed_article(db, pmid)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="PubMed retrieval failed") from exc

    return {
        "created": created,
        "publication": {
            "id": publication.id,
            "source_system": publication.source_system,
            "source_id": publication.source_id,
            "pmid": publication.pmid,
            "doi": publication.doi,
            "title": publication.title,
            "journal": publication.journal,
            "publication_date": publication.publication_date.isoformat() if publication.publication_date else None,
            "authors": publication.authors_json,
            "source_url": publication.source_url,
            "retrieval_ref": publication.retrieval_ref,
            "content_hash": publication.content_hash,
            "metadata": publication.metadata_json,
        },
        "passages": [
            {
                "id": passage.id,
                "publication_id": passage.publication_id,
                "section": passage.section,
                "locator": passage.locator,
                "text": passage.text,
                "content_hash": passage.content_hash,
                "provenance": passage.provenance_json,
            }
            for passage in passages
        ],
    }


@router.post("/investigations/{investigation_id}/literature-evidence")
def add_literature_evidence(investigation_id: str, request: LiteratureEvidenceRequest, db: DB) -> dict:
    try:
        link, created = bind_passage_to_investigation(
            db,
            investigation_id,
            request.passage_id,
            stance=request.stance,
            weight=request.weight,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "created": created,
        "evidence_link_id": link.id,
        "investigation_id": link.investigation_id,
        "scientific_passage_id": link.scientific_passage_id,
        "stance": link.stance,
        "weight": link.weight,
        "canonical_evidence": True,
        "evidence_kind": "scientific_passage",
    }


@router.get("/investigations/{investigation_id}/literature-evidence")
def investigation_literature_evidence(investigation_id: str, db: DB) -> list[dict]:
    try:
        return list_literature_evidence(db, investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
