from __future__ import annotations

from urllib.error import HTTPError, URLError

from fastapi import APIRouter, HTTPException

from app.api.deps import DB
from app.scientific_literature.pubmed import ingest_pubmed_article

router = APIRouter()


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
