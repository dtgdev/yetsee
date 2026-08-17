from collections import Counter

from sqlalchemy import select

from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink


SUGGESTED_SOURCES = {
    "behavior": ["google_trends", "reddit", "youtube", "meetup"],
    "technology": ["github", "hacker_news", "arxiv", "patents"],
    "market": ["news", "sec", "jobs", "google_trends"],
    "product_category": ["commerce", "google_trends", "reddit", "youtube"],
}
DEFAULT_SOURCES = ["google_trends", "reddit", "news", "youtube", "jobs"]


class EvidenceAgent:
    def manifest(self):
        return AgentManifest(
            "evidence_agent",
            "1.0",
            "Evidence Agent",
            "Audits investigation evidence coverage, source independence, repetition, and contradiction gaps without rewriting observations.",
            ("audit_evidence", "detect_source_gaps", "suggest_sources", "audit_contradictions"),
            ("read:investigation", "read:evidence", "read:hypotheses", "write:findings"),
        )

    def execute(self, db, context):
        investigation, links, observations = investigation_bundle(db, context.target_id)
        findings = []
        sources = sorted({item.source for item in observations})

        # Repeated ingestion runs are useful history but do not equal independent evidence.
        fingerprints = [
            (item.source, item.source_ref or "", item.metric or "", item.topic or "")
            for item in observations
        ]
        unique_fingerprints = set(fingerprints)
        repeated_count = max(0, len(observations) - len(unique_fingerprints))

        if len(sources) < 2:
            findings.append(FindingDraft(
                category="source_diversity",
                title="Independent source coverage is too low",
                detail=f"This investigation currently uses {len(sources)} independent source(s): {', '.join(sources) or 'none'}. Add at least one unrelated source before treating the thesis as validated.",
                severity="critical",
                stance="warning",
                confidence=0.99,
                evidence_ids=[item.id for item in observations],
                metadata={"source_count": len(sources), "sources": sources},
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
        suggestions = [source for source in SUGGESTED_SOURCES.get(semantic_kind, DEFAULT_SOURCES) if source not in sources]
        if suggestions:
            findings.append(FindingDraft(
                category="missing_sources",
                title="Collect independent evidence next",
                detail="Recommended source families: " + ", ".join(suggestions[:4]) + ". These are suggestions, not evidence, and must be ingested before affecting confidence.",
                severity="info",
                stance="neutral",
                confidence=0.9,
                metadata={"suggested_sources": suggestions[:4], "current_sources": sources},
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
            summary=f"Audited {investigation.title}: {len(observations)} observation(s), {len(sources)} source(s), {len(findings)} finding(s).",
            recommendation="collect_independent_evidence" if len(sources) < 2 else "continue_review",
            confidence=0.96,
            findings=findings,
            output={
                "observations": len(observations),
                "independent_sources": len(sources),
                "sources": sources,
                "effective_evidence_patterns": len(unique_fingerprints),
                "repeated_observations": repeated_count,
                "suggested_sources": suggestions[:4],
                "hypotheses": len(hypotheses),
            },
            permissions_used=["read:investigation", "read:evidence", "read:hypotheses", "write:findings"],
        )
