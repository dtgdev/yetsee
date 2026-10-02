from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.writer import governed_entity, governed_relationship
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.scientific_literature import ScientificPassage, ScientificPublication
from app.scientific_literature.contradiction_intelligence import extract_scientific_context


_OSIMERTINIB_RE = re.compile(r"\bosimertinib\b", re.I)


def _publication_node(db: Session, publication: ScientificPublication):
    return governed_entity(
        db,
        kind="publication",
        canonical_name=publication.title,
        canonical_key=f"publication:pubmed:{publication.pmid or publication.id}",
        aliases=[value for value in [publication.doi, publication.pmid] if value],
        attributes={
            "publication_id": publication.id,
            "pmid": publication.pmid,
            "doi": publication.doi,
            "journal": publication.journal,
            "publication_date": publication.publication_date.isoformat() if publication.publication_date else None,
            "source_system": publication.source_system,
            "source_url": publication.source_url,
            "canonical_record": "scientific_publication",
        },
    )


def _passage_node(db: Session, passage: ScientificPassage, publication: ScientificPublication):
    return governed_entity(
        db,
        kind="source",
        canonical_name=f"{publication.pmid or publication.id} · {passage.locator or passage.section or 'passage'}",
        canonical_key=f"scientific-passage:{passage.id}",
        attributes={
            "passage_id": passage.id,
            "publication_id": publication.id,
            "section": passage.section,
            "locator": passage.locator,
            "content_hash": passage.content_hash,
            "canonical_record": "scientific_passage",
        },
    )


def _trial_ids(publication: ScientificPublication) -> list[str]:
    metadata = publication.metadata_json or {}
    return sorted({
        str(value).upper()
        for value in metadata.get("clinical_trial_ids", metadata.get("trial_identifiers", []))
        if value
    })


def _context_text(publication: ScientificPublication, passages: list[ScientificPassage]) -> str:
    return " ".join([publication.title, *[passage.text for passage in passages]])


def project_investigation_literature_graph(db: Session, investigation_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    rows = db.execute(
        select(EvidenceLink, ScientificPassage, ScientificPublication)
        .join(ScientificPassage, EvidenceLink.scientific_passage_id == ScientificPassage.id)
        .join(ScientificPublication, ScientificPassage.publication_id == ScientificPublication.id)
        .where(EvidenceLink.investigation_id == investigation_id)
        .order_by(ScientificPublication.id.asc(), ScientificPassage.id.asc())
    ).all()

    grouped: dict[str, dict] = {}
    for link, passage, publication in rows:
        entry = grouped.setdefault(
            publication.id,
            {"publication": publication, "passages": [], "evidence_links": []},
        )
        entry["passages"].append(passage)
        entry["evidence_links"].append(link)

    node_ids: set[str] = set()
    relationship_ids: set[str] = set()
    publication_nodes = 0
    passage_nodes = 0
    trial_nodes = 0
    context_nodes = 0

    for entry in grouped.values():
        publication: ScientificPublication = entry["publication"]
        passages: list[ScientificPassage] = entry["passages"]
        evidence_ids = [passage.id for passage in passages]
        pub_node = _publication_node(db, publication)
        node_ids.add(pub_node.id)
        publication_nodes += 1

        for passage in passages:
            passage_node = _passage_node(db, passage, publication)
            node_ids.add(passage_node.id)
            passage_nodes += 1
            relation = governed_relationship(
                db,
                source=pub_node,
                target=passage_node,
                kind="PUBLICATION_CONTAINS_PASSAGE",
                confidence=1.0,
                evidence_ids=[passage.id],
                provenance={
                    "method": "scientific-literature-graph-projection-v1",
                    "investigation_id": investigation_id,
                    "publication_id": publication.id,
                    "passage_id": passage.id,
                    "canonical_evidence_kind": "scientific_passage",
                },
            )
            relationship_ids.add(relation.id)

        trials = _trial_ids(publication)
        context = extract_scientific_context(_context_text(publication, passages))

        for trial_id in trials:
            trial = governed_entity(
                db,
                kind="clinical_trial",
                canonical_name=trial_id,
                canonical_key=f"clinical-trial:{trial_id.lower()}",
                aliases=[],
                attributes={
                    "registry": "ClinicalTrials.gov",
                    "registry_id": trial_id,
                    "canonical_source_publication_ids": [publication.id],
                },
            )
            node_ids.add(trial.id)
            trial_nodes += 1
            relation = governed_relationship(
                db,
                source=pub_node,
                target=trial,
                kind="PUBLICATION_REPORTS_STUDY",
                confidence=0.99,
                evidence_ids=evidence_ids,
                provenance={
                    "method": "explicit-clinical-trial-id",
                    "investigation_id": investigation_id,
                    "publication_id": publication.id,
                    "trial_id": trial_id,
                    "canonical_evidence_kind": "scientific_passage",
                },
            )
            relationship_ids.add(relation.id)

            for population_key in context.get("population", []):
                labels = {
                    "egfr_mutant": "EGFR-mutant NSCLC",
                    "egfr_t790m": "EGFR T790M NSCLC",
                }
                population = governed_entity(
                    db,
                    kind="population",
                    canonical_name=labels.get(population_key, population_key.replace("_", " ").title()),
                    canonical_key=f"population:{population_key}",
                    attributes={
                        "context_dimension": "population",
                        "context_key": population_key,
                        "derived_from_text": True,
                    },
                )
                node_ids.add(population.id)
                context_nodes += 1
                relation = governed_relationship(
                    db,
                    source=trial,
                    target=population,
                    kind="STUDY_HAS_POPULATION",
                    confidence=0.9,
                    evidence_ids=evidence_ids,
                    provenance={
                        "method": "deterministic-scientific-context-v1",
                        "investigation_id": investigation_id,
                        "publication_id": publication.id,
                        "trial_id": trial_id,
                        "context_key": population_key,
                        "canonical_evidence_kind": "scientific_passage",
                    },
                )
                relationship_ids.add(relation.id)

            if _OSIMERTINIB_RE.search(_context_text(publication, passages)):
                drug = governed_entity(
                    db,
                    kind="drug",
                    canonical_name="Osimertinib",
                    canonical_key="drug:osimertinib",
                    aliases=[],
                    attributes={"derived_from_text": True},
                )
                node_ids.add(drug.id)
                context_nodes += 1
                relation = governed_relationship(
                    db,
                    source=trial,
                    target=drug,
                    kind="STUDY_USES_INTERVENTION",
                    confidence=0.95,
                    evidence_ids=evidence_ids,
                    provenance={
                        "method": "deterministic-intervention-mention-v1",
                        "investigation_id": investigation_id,
                        "publication_id": publication.id,
                        "trial_id": trial_id,
                        "canonical_evidence_kind": "scientific_passage",
                    },
                )
                relationship_ids.add(relation.id)

            assay_labels = {
                "next_generation_sequencing": "Next-generation sequencing",
                "circulating_tumor_dna": "Circulating tumor DNA",
                "plasma": "Plasma assay context",
                "tissue": "Tissue assay context",
            }
            for assay_key in context.get("assay_context", []):
                assay = governed_entity(
                    db,
                    kind="assay",
                    canonical_name=assay_labels.get(assay_key, assay_key.replace("_", " ").title()),
                    canonical_key=f"assay:{assay_key}",
                    attributes={
                        "context_dimension": "assay_context",
                        "context_key": assay_key,
                        "derived_from_text": True,
                    },
                )
                node_ids.add(assay.id)
                context_nodes += 1
                relation = governed_relationship(
                    db,
                    source=trial,
                    target=assay,
                    kind="STUDY_USES_ASSAY",
                    confidence=0.9,
                    evidence_ids=evidence_ids,
                    provenance={
                        "method": "deterministic-scientific-context-v1",
                        "investigation_id": investigation_id,
                        "publication_id": publication.id,
                        "trial_id": trial_id,
                        "context_key": assay_key,
                        "canonical_evidence_kind": "scientific_passage",
                    },
                )
                relationship_ids.add(relation.id)

    db.commit()
    return {
        "investigation_id": investigation_id,
        "publication_count": len(grouped),
        "publication_nodes": publication_nodes,
        "passage_nodes": passage_nodes,
        "trial_nodes": trial_nodes,
        "context_nodes": context_nodes,
        "node_count": len(node_ids),
        "relationship_count": len(relationship_ids),
        "policy": {
            "canonical_literature_remains_in_scientific_tables": True,
            "graph_is_derived_projection": True,
            "passage_text_not_duplicated_into_graph": True,
            "relationships_require_provenance": True,
            "projection": "scientific-literature-graph-projection-v1",
        },
    }
