from collections import Counter

from sqlalchemy import select

from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.investigation_runtime.evidence_accounting import investigation_evidence_accounting
from app.scientific_literature.evidence_gap_intelligence import investigation_evidence_gap_intelligence
from app.scientific_literature.study_independence import investigation_study_independence
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink


SUGGESTED_SOURCES = {
    "behavior": ["google_trends", "reddit", "youtube", "meetup"],
    "technology": ["github", "hacker_news", "arxiv", "patents"],
    "market": ["news", "sec", "jobs", "google_trends"],
    "product_category": ["commerce", "google_trends", "reddit", "youtube"],
    "science": ["pubmed", "clinical_trials", "systematic_reviews", "regulatory_biomedical"],
    "scientific": ["pubmed", "clinical_trials", "systematic_reviews", "regulatory_biomedical"],
    "biomedical": ["pubmed", "clinical_trials", "systematic_reviews", "regulatory_biomedical"],
    "clinical": ["pubmed", "clinical_trials", "systematic_reviews", "regulatory_biomedical"],
}
DEFAULT_SOURCES = ["google_trends", "reddit", "news", "youtube", "jobs"]
SCIENTIFIC_SOURCES = ["pubmed", "clinical_trials", "systematic_reviews", "regulatory_biomedical"]


def _suggested_source_families(*, semantic_kind: str | None, independent_publication_count: int) -> list[str]:
    if semantic_kind in SUGGESTED_SOURCES:
        return SUGGESTED_SOURCES[semantic_kind]
    if independent_publication_count > 0:
        return SCIENTIFIC_SOURCES
    return DEFAULT_SOURCES


class EvidenceAgent:
    def manifest(self):
        return AgentManifest(
            "evidence_agent",
            "1.3",
            "Evidence Agent",
            "Audits investigation evidence coverage, source independence, repetition, and contradiction gaps without rewriting observations.",
            ("audit_evidence", "detect_source_gaps", "suggest_sources", "audit_contradictions"),
            ("read:investigation", "read:evidence", "read:hypotheses", "write:findings"),
        )

    def execute(self, db, context):
        investigation, links, observations = investigation_bundle(db, context.target_id)
        findings = []
        observation_sources = sorted({item.source for item in observations})
        accounting = investigation_evidence_accounting(db, investigation.id)
        accounting_source_count = accounting["independent_source_count"]
        independent_publication_count = accounting["independent_publication_count"]
        literature_sources = sorted({
            f"PubMed {item['publication']['pmid']}" if item.get("publication") and item["publication"].get("pmid") else f"Publication {item['publication']['id']}"
            for item in accounting["literature_items"]
            if item.get("publication")
        })
        source_labels = observation_sources + literature_sources
        # Agent source diversity is family/publication based rather than raw evidence-item based.
        # Multiple observations from the same upstream source are not independent confirmations.
        independent_source_count = len(observation_sources) + independent_publication_count

        # Repeated ingestion runs are useful history but do not equal independent evidence.
        fingerprints = [
            (item.source, item.source_ref or "", item.metric or "", item.topic or "")
            for item in observations
        ]
        unique_fingerprints = set(fingerprints)
        repeated_count = max(0, len(observations) - len(unique_fingerprints))

        if independent_source_count < 2:
            findings.append(FindingDraft(
                category="source_diversity",
                title="Independent source coverage is too low",
                detail=f"This investigation currently uses {independent_source_count} independent canonical source(s): {', '.join(source_labels) or 'none'}. Add at least one unrelated source before treating the thesis as validated.",
                severity="critical",
                stance="warning",
                confidence=0.99,
                evidence_ids=[item.id for item in observations],
                metadata={
                    "source_count": independent_source_count,
                    "observation_sources": observation_sources,
                    "independent_publications": independent_publication_count,
                    "literature_sources": literature_sources,
                    "accounting_source_count": accounting_source_count,
                    "accounting_policy": accounting["policy"],
                },
            ))

        if repeated_count:
            counts = Counter(fingerprints)
            repeated = [
                {"source": key[0], "source_ref": key[1], "metric": key[2], "count": count}
                for key, count in counts.items() if count > 1
            ]
            findings.append(FindingDraft(
                category="evidence_repetition",
                title="Repeated observations should not be treated as independent confirmation",
                detail=f"{repeated_count} of {len(observations)} observation(s) repeat an existing source/source-reference/metric pattern. The evidence history is valid, but independence is lower than the raw count suggests.",
                severity="warning",
                stance="warning",
                confidence=0.97,
                evidence_ids=[item.id for item in observations],
                metadata={"raw_observations": len(observations), "effective_patterns": len(unique_fingerprints), "repeated_patterns": repeated},
            ))

        semantic_kind = (investigation.attributes or {}).get("semantic_kind")
        scientific_mode = independent_publication_count > 0 or semantic_kind in {"science", "scientific", "biomedical", "clinical"}
        evidence_gaps = None
        independence = None
        if scientific_mode:
            evidence_gaps = investigation_evidence_gap_intelligence(db, investigation.id)
            independence = investigation_study_independence(db, investigation.id)

        recommended_families = _suggested_source_families(
            semantic_kind=semantic_kind,
            independent_publication_count=independent_publication_count,
        )
        covered_families = set(observation_sources)
        if independent_publication_count > 0:
            covered_families.add("pubmed")
        suggestions = [source for source in recommended_families if source not in covered_families]

        if scientific_mode and evidence_gaps and evidence_gaps["gap_count"] > 0:
            prioritized = evidence_gaps["gaps"][:3]
            gap_titles = "; ".join(gap["title"] for gap in prioritized)
            next_steps = [
                item
                for gap in prioritized
                for item in gap.get("suggested_next_evidence", [])
            ][:3]
            findings.append(FindingDraft(
                category="evidence_gap_guidance",
                title="Resolve current evidence gaps next",
                detail=(
                    f"Current prioritized gaps: {gap_titles}. "
                    + ("Recommended next evidence: " + " ".join(next_steps) if next_steps else "")
                ).strip(),
                severity="info",
                stance="neutral",
                confidence=0.95,
                metadata={
                    "gap_count": evidence_gaps["gap_count"],
                    "priority_counts": evidence_gaps["priority_counts"],
                    "prioritized_gap_types": [gap["gap_type"] for gap in prioritized],
                    "suggested_next_evidence": next_steps,
                    "study_independence_status": independence["overall_status"] if independence else None,
                    "current_distinct_publications": independent_publication_count,
                    "gap_policy": evidence_gaps["policy"],
                },
            ))
        elif suggestions:
            findings.append(FindingDraft(
                category="missing_sources",
                title="Collect additional evidence next",
                detail="Recommended source families: " + ", ".join(suggestions[:4]) + ". These are suggestions, not evidence, and must be ingested before affecting confidence.",
                severity="info",
                stance="neutral",
                confidence=0.9,
                metadata={
                    "suggested_sources": suggestions[:4],
                    "current_observation_sources": observation_sources,
                    "current_distinct_sources": independent_source_count,
                    "current_distinct_publications": independent_publication_count,
                    "recommendation_profile": "scientific" if recommended_families == SCIENTIFIC_SOURCES else (semantic_kind or "default"),
                },
            ))

        hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.investigation_id == investigation.id)))
        for hypothesis in hypotheses:
            hypothesis_links = list(db.scalars(select(HypothesisEvidenceLink).where(HypothesisEvidenceLink.hypothesis_id == hypothesis.id)))
            contradicting = [link for link in hypothesis_links if link.stance == "contradicting"]
            supporting = [link for link in hypothesis_links if link.stance == "supporting"]
            if not contradicting:
                findings.append(FindingDraft(
                    category="counter_evidence",
                    title=f"No counter-evidence linked to: {hypothesis.title}",
                    detail="Actively search for observations that could falsify this hypothesis before increasing trust in it.",
                    severity="warning",
                    stance="critical",
                    confidence=0.96,
                    evidence_ids=[link.observation_id for link in supporting],
                    metadata={"hypothesis_id": hypothesis.id, "supporting_links": len(supporting), "contradicting_links": 0},
                ))

        return AgentResult(
            summary=f"Audited {investigation.title}: {accounting['canonical_evidence_count']} canonical evidence item(s), {independent_source_count} distinct source(s), {len(findings)} finding(s).",
            recommendation=(
                "collect_additional_evidence"
                if independent_source_count < 2
                else "resolve_evidence_gaps"
                if evidence_gaps and evidence_gaps["gap_count"] > 0
                else "continue_review"
            ),
            confidence=0.96,
            findings=findings,
            output={
                "observations": len(observations),
                "canonical_evidence": accounting["canonical_evidence_count"],
                "independent_sources": independent_source_count,
                "accounting_sources": accounting_source_count,
                "independent_publications": independent_publication_count,
                "observation_sources": observation_sources,
                "literature_sources": literature_sources,
                "effective_evidence_patterns": len(unique_fingerprints),
                "repeated_observations": repeated_count,
                "suggested_sources": suggestions[:4],
                "evidence_gap_count": evidence_gaps["gap_count"] if evidence_gaps else 0,
                "study_independence_status": independence["overall_status"] if independence else None,
                "hypotheses": len(hypotheses),
                "evidence_accounting_policy": accounting["policy"],
            },
            permissions_used=["read:investigation", "read:evidence", "read:hypotheses", "write:findings"],
        )
