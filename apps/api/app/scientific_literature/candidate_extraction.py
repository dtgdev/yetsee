from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.scientific_literature import ScientificPassage, ScientificPublication

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_RESISTANCE_MECHANISM_RE = re.compile(
    r"(?:resistance mechanisms? (?:are|were|include|included)|"
    r"resistance-related genomic alterations?[^.;:]*[:;,]?)[^.;]*",
    re.IGNORECASE,
)
_ALTERATION_RE = re.compile(
    r"\b([A-Z][A-Z0-9-]{1,15})\s+(amplification|[A-Z]\d+[A-Z](?:/X)?\s+mutations?|mutations?)\b",
)


@dataclass(frozen=True)
class ClaimCandidate:
    candidate_id: str
    investigation_id: str
    passage_id: str
    publication_id: str
    pmid: str | None
    doi: str | None
    source_url: str | None
    locator: str | None
    source_text: str
    assertion_text: str
    subject_kind: str
    subject_name: str
    subject_key: str
    predicate: str
    object_kind: str
    object_name: str
    object_key: str
    extraction_method: str
    extraction_version: str
    extraction_confidence: float
    requires_review: bool = True
    canonical_evidence: bool = False

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "investigation_id": self.investigation_id,
            "claim": {
                "subject": {
                    "kind": self.subject_kind,
                    "name": self.subject_name,
                    "key": self.subject_key,
                },
                "predicate": self.predicate,
                "object": {
                    "kind": self.object_kind,
                    "name": self.object_name,
                    "key": self.object_key,
                },
                "assertion_text": self.assertion_text,
            },
            "extraction": {
                "method": self.extraction_method,
                "version": self.extraction_version,
                "confidence": self.extraction_confidence,
                "requires_review": self.requires_review,
                "canonical_evidence": self.canonical_evidence,
            },
            "provenance": {
                "passage_id": self.passage_id,
                "publication_id": self.publication_id,
                "pmid": self.pmid,
                "doi": self.doi,
                "source_url": self.source_url,
                "locator": self.locator,
            },
            "source_text": self.source_text,
        }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _candidate_id(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"scc-{digest[:24]}"


def _drug_resistance_object(text: str) -> tuple[str, str] | None:
    lower = text.lower()
    # Conservative v1: only map a treatment when it is explicitly present in
    # the assertion sentence. This vocabulary is intentionally small and can be
    # replaced by a terminology service later without changing the contract.
    for drug in ("osimertinib",):
        if drug in lower:
            name = f"Acquired {drug} resistance"
            return name, f"drug-resistance:{drug}-acquired"
    return None


def _normalized_alteration(gene: str, alteration: str) -> str:
    gene = gene.upper()
    normalized = alteration.strip()
    if normalized.lower() == "amplification":
        return f"{gene} amplification"
    if normalized.lower() == "mutations":
        return f"{gene} mutation"
    if normalized.lower() == "mutation":
        return f"{gene} mutation"
    return f"{gene} {normalized.upper().replace(' MUTATIONS', '').replace(' MUTATION', '')} mutation"


def _extract_explicit_resistance_mechanisms(
    *,
    investigation_id: str,
    passage: ScientificPassage,
    publication: ScientificPublication,
) -> list[ClaimCandidate]:
    candidates: list[ClaimCandidate] = []
    for sentence in _SENTENCE_SPLIT_RE.split(passage.text.strip()):
        if not sentence:
            continue
        if _RESISTANCE_MECHANISM_RE.search(sentence) is None:
            continue
        resistance = _drug_resistance_object(sentence)
        if resistance is None:
            # Do not inherit drug context from another sentence in v1.
            continue
        object_name, object_key = resistance
        seen_subjects: set[str] = set()
        for match in _ALTERATION_RE.finditer(sentence):
            subject_name = _normalized_alteration(match.group(1), match.group(2))
            subject_key = f"genomic-alteration:{_slug(subject_name)}"
            if subject_key in seen_subjects:
                continue
            seen_subjects.add(subject_key)
            candidate_id = _candidate_id(
                investigation_id,
                passage.id,
                publication.id,
                subject_key,
                "reported_as_resistance_mechanism",
                object_key,
                sentence,
            )
            candidates.append(
                ClaimCandidate(
                    candidate_id=candidate_id,
                    investigation_id=investigation_id,
                    passage_id=passage.id,
                    publication_id=publication.id,
                    pmid=publication.pmid,
                    doi=publication.doi,
                    source_url=publication.source_url,
                    locator=passage.locator,
                    source_text=passage.text,
                    assertion_text=sentence,
                    subject_kind="genomic_alteration",
                    subject_name=subject_name,
                    subject_key=subject_key,
                    predicate="reported_as_resistance_mechanism",
                    object_kind="drug_resistance",
                    object_name=object_name,
                    object_key=object_key,
                    extraction_method="deterministic_explicit_assertion",
                    extraction_version="l3-v1",
                    extraction_confidence=0.98,
                )
            )
    return candidates


def extract_investigation_claim_candidates(db: Session, investigation_id: str) -> list[dict]:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    rows = db.execute(
        select(EvidenceLink, ScientificPassage, ScientificPublication)
        .join(ScientificPassage, EvidenceLink.scientific_passage_id == ScientificPassage.id)
        .join(ScientificPublication, ScientificPassage.publication_id == ScientificPublication.id)
        .where(
            EvidenceLink.investigation_id == investigation_id,
            EvidenceLink.scientific_passage_id.is_not(None),
        )
        .order_by(ScientificPublication.source_id.asc(), ScientificPassage.locator.asc())
    ).all()

    candidates: list[ClaimCandidate] = []
    for _, passage, publication in rows:
        candidates.extend(
            _extract_explicit_resistance_mechanisms(
                investigation_id=investigation_id,
                passage=passage,
                publication=publication,
            )
        )

    return [candidate.to_dict() for candidate in candidates]
