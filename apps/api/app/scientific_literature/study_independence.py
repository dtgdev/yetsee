from __future__ import annotations

from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.scientific_literature import ScientificPassage, ScientificPublication


def _trial_ids(publication: ScientificPublication) -> set[str]:
    metadata = publication.metadata_json or {}
    return {str(value).upper() for value in metadata.get("clinical_trial_ids", []) if value}


def _author_keys(publication: ScientificPublication) -> set[str]:
    keys: set[str] = set()
    for author in publication.authors_json or []:
        last = str(author.get("last_name") or "").strip().lower()
        initials = str(author.get("initials") or "").strip().lower()
        collective = str(author.get("collective_name") or "").strip().lower()
        if last:
            keys.add(f"{last}:{initials}")
        elif collective:
            keys.add(f"collective:{collective}")
    return keys


def assess_pair(left: ScientificPublication, right: ScientificPublication) -> dict:
    left_trials = _trial_ids(left)
    right_trials = _trial_ids(right)
    shared_trials = sorted(left_trials & right_trials)

    left_authors = _author_keys(left)
    right_authors = _author_keys(right)
    shared_authors = left_authors & right_authors
    author_union = left_authors | right_authors
    author_overlap = round(len(shared_authors) / len(author_union), 3) if author_union else 0.0

    if shared_trials:
        status = "same_trial"
        confidence = 0.99
        rationale = f"Both publications explicitly reference the same registered trial: {', '.join(shared_trials)}."
    elif left_trials and right_trials:
        status = "independent_trials"
        confidence = 0.98
        rationale = (
            "Both publications contain explicit ClinicalTrials.gov identifiers and the trial identifiers are disjoint: "
            f"{', '.join(sorted(left_trials))} vs {', '.join(sorted(right_trials))}."
        )
    elif author_overlap >= 0.5 and len(shared_authors) >= 3:
        status = "likely_related"
        confidence = 0.65
        rationale = (
            "No shared registered trial identifier is available, but substantial author overlap suggests the publications may derive from related research programs or cohorts."
        )
    else:
        status = "unknown"
        confidence = 0.5
        rationale = "Available metadata is insufficient to establish whether the underlying study populations are independent."

    return {
        "left_publication_id": left.id,
        "right_publication_id": right.id,
        "status": status,
        "confidence": confidence,
        "shared_trial_ids": shared_trials,
        "left_trial_ids": sorted(left_trials),
        "right_trial_ids": sorted(right_trials),
        "shared_author_count": len(shared_authors),
        "author_overlap": author_overlap,
        "rationale": rationale,
        "policy": {
            "derived_independence_assessment": True,
            "canonical_evidence": False,
            "algorithm": "deterministic-study-independence-v1",
        },
    }


def investigation_study_independence(db: Session, investigation_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    rows = db.execute(
        select(ScientificPublication)
        .join(ScientificPassage, ScientificPassage.publication_id == ScientificPublication.id)
        .join(EvidenceLink, EvidenceLink.scientific_passage_id == ScientificPassage.id)
        .where(EvidenceLink.investigation_id == investigation_id)
        .distinct()
        .order_by(ScientificPublication.publication_date.asc(), ScientificPublication.id.asc())
    ).scalars().all()

    publications = list(rows)
    pairwise = [assess_pair(left, right) for left, right in combinations(publications, 2)]

    same_trial_pairs = [item for item in pairwise if item["status"] == "same_trial"]
    independent_pairs = [item for item in pairwise if item["status"] == "independent_trials"]
    unresolved_pairs = [item for item in pairwise if item["status"] in {"unknown", "likely_related"}]

    if same_trial_pairs:
        overall = "overlap_detected"
    elif pairwise and len(independent_pairs) == len(pairwise):
        overall = "confirmed_independent_trials"
    elif not pairwise:
        overall = "single_publication"
    else:
        overall = "partially_resolved"

    study_records = []
    for publication in publications:
        metadata = publication.metadata_json or {}
        study_records.append({
            "publication_id": publication.id,
            "pmid": publication.pmid,
            "doi": publication.doi,
            "title": publication.title,
            "publication_date": publication.publication_date.isoformat() if publication.publication_date else None,
            "clinical_trial_ids": sorted(_trial_ids(publication)),
            "publication_types": metadata.get("publication_types", []),
            "mesh_terms": metadata.get("mesh_terms", []),
        })

    return {
        "investigation_id": investigation_id,
        "publication_count": len(publications),
        "overall_status": overall,
        "confirmed_independent_pair_count": len(independent_pairs),
        "same_trial_pair_count": len(same_trial_pairs),
        "unresolved_pair_count": len(unresolved_pairs),
        "studies": study_records,
        "pairwise_assessments": pairwise,
        "policy": {
            "publication_count_is_not_study_count": True,
            "derived_independence_assessment": True,
            "does_not_change_canonical_evidence": True,
            "algorithm": "deterministic-study-independence-v1",
            "strong_signal_priority": ["shared_clinical_trial_id", "disjoint_clinical_trial_ids"],
            "weak_signal_only": ["author_overlap"],
        },
    }
