from collections import defaultdict

from sqlalchemy import select

from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.models.semantic import SemanticConcept


class SemanticCuratorAgent:
    def manifest(self):
        return AgentManifest(
            "semantic_curator",
            "1.0",
            "Semantic Curator",
            "Audits concept extraction, article-like fallbacks, ambiguous canonicalization and weak semantic concepts.",
            ("audit_semantics", "propose_concept_resolution", "audit_topic_quality"),
            ("read:semantic_concepts", "read:evidence", "write:findings", "propose:concept_merge"),
        )

    def execute(self, db, context):
        concepts = list(db.scalars(select(SemanticConcept).order_by(SemanticConcept.created_at.desc()).limit(2000)))
        findings = []
        by_key = defaultdict(list)
        for concept in concepts:
            by_key[concept.canonical_key].append(concept)
            if concept.method == "title_fallback_v1" and concept.confidence >= 0.8:
                findings.append(FindingDraft(
                    "semantic_quality",
                    "Article-like title has excessive confidence",
                    f"{concept.canonical_name} is a title fallback and should not independently drive an investigation.",
                    "warning", "critical", .95, [concept.observation_id],
                    {"concept_id": concept.id, "canonical_key": concept.canonical_key},
                ))
        ambiguous = 0
        for key, rows in by_key.items():
            kinds = {row.kind for row in rows}
            if len(kinds) > 1 and len(rows) >= 2:
                ambiguous += 1
                findings.append(FindingDraft(
                    "semantic_ambiguity",
                    f"Ambiguous concept classification: {rows[0].canonical_name}",
                    f"The same canonical key is classified as {', '.join(sorted(kinds))}. Review ontology mapping before promotion.",
                    "info", "neutral", .82,
                    list(dict.fromkeys(row.observation_id for row in rows))[:20],
                    {"canonical_key": key, "kinds": sorted(kinds)},
                ))
        return AgentResult(
            summary=f"Reviewed {len(concepts)} semantic concepts; produced {len(findings)} curation finding(s).",
            confidence=.94,
            findings=findings,
            output={"concepts_reviewed": len(concepts), "ambiguous_keys": ambiguous, "flags": len(findings)},
            permissions_used=["read:semantic_concepts", "read:evidence", "write:findings"],
        )
