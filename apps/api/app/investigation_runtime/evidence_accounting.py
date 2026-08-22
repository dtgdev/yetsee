from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.scientific_literature import ScientificPassage, ScientificPublication


def investigation_evidence_accounting(db: Session, investigation_id: str) -> dict:
    links = list(
        db.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.investigation_id == investigation_id)
            .order_by(EvidenceLink.created_at.asc())
        )
    )

    observation_links = [link for link in links if link.observation_id]
    literature_links = [link for link in links if link.scientific_passage_id]

    passage_ids = sorted({link.scientific_passage_id for link in literature_links if link.scientific_passage_id})
    passages = []
    publications = []
    if passage_ids:
        passages = list(db.scalars(select(ScientificPassage).where(ScientificPassage.id.in_(passage_ids))))
        publication_ids = sorted({passage.publication_id for passage in passages})
        if publication_ids:
            publications = list(
                db.scalars(select(ScientificPublication).where(ScientificPublication.id.in_(publication_ids)))
            )

    passages_by_id = {passage.id: passage for passage in passages}
    publications_by_id = {publication.id: publication for publication in publications}

    stance_counts = Counter(link.stance for link in links)
    literature_stance_counts = Counter(link.stance for link in literature_links)

    observation_source_keys = {f"observation:{link.observation_id}" for link in observation_links if link.observation_id}
    publication_source_keys = {
        f"publication:{passages_by_id[link.scientific_passage_id].publication_id}"
        for link in literature_links
        if link.scientific_passage_id in passages_by_id
    }

    literature_items = []
    for link in literature_links:
        passage = passages_by_id.get(link.scientific_passage_id)
        if passage is None:
            continue
        publication = publications_by_id.get(passage.publication_id)
        literature_items.append(
            {
                "evidence_link_id": link.id,
                "stance": link.stance,
                "weight": link.weight,
                "passage": {
                    "id": passage.id,
                    "section": passage.section,
                    "locator": passage.locator,
                    "text": passage.text,
                    "content_hash": passage.content_hash,
                    "provenance": passage.provenance_json,
                },
                "publication": None
                if publication is None
                else {
                    "id": publication.id,
                    "pmid": publication.pmid,
                    "doi": publication.doi,
                    "title": publication.title,
                    "journal": publication.journal,
                    "publication_date": publication.publication_date.isoformat()
                    if publication.publication_date
                    else None,
                    "source_url": publication.source_url,
                    "content_hash": publication.content_hash,
                },
            }
        )

    return {
        "canonical_evidence_count": len(links),
        "observation_evidence_count": len(observation_links),
        "literature_evidence_count": len(literature_links),
        "independent_source_count": len(observation_source_keys | publication_source_keys),
        "independent_publication_count": len(publication_source_keys),
        "supporting_count": stance_counts["supporting"],
        "contradicting_count": stance_counts["contradicting"],
        "contextual_count": stance_counts["contextual"],
        "literature_supporting_count": literature_stance_counts["supporting"],
        "literature_contradicting_count": literature_stance_counts["contradicting"],
        "literature_contextual_count": literature_stance_counts["contextual"],
        "literature_items": literature_items,
        "policy": {
            "canonical_sources": ["observation", "scientific_passage"],
            "derived_claims_are_evidence": False,
            "memory_is_evidence": False,
        },
    }
