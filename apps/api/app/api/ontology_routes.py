from fastapi import APIRouter, HTTPException

from app.knowledge_graph.ontology import ontology_manifest


router = APIRouter()


@router.get("/ontology")
def get_ontology_manifest() -> dict:
    return ontology_manifest()


@router.get("/ontology/{domain}")
def get_domain_ontology(domain: str) -> dict:
    try:
        return ontology_manifest(domain)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown ontology domain: {domain}") from exc
