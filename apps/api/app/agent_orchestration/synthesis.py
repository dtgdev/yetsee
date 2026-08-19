from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from app.models.agent import AgentFinding


def synthesize_findings(findings: Iterable[AgentFinding]) -> dict[str, Any]:
    """Build an auditable cross-agent synthesis without semantic guesswork.

    Agreement and contradiction are only asserted when two or more distinct
    agents cite the same evidence. This keeps the synthesis deterministic and
    provenance-preserving: shared evidence is the explicit comparison key.
    Findings with no evidence are retained as unresolved evidence gaps rather
    than being silently treated as support or contradiction.
    """
    rows = [finding for finding in findings if finding.agent_id != "investigation_agent"]
    by_evidence: dict[str, list[AgentFinding]] = defaultdict(list)
    evidence_ids: set[str] = set()

    for finding in rows:
        for evidence_id in finding.evidence_ids or []:
            evidence_ids.add(evidence_id)
            by_evidence[evidence_id].append(finding)

    supporting = [finding for finding in rows if finding.stance == "supporting"]
    critical = [finding for finding in rows if finding.stance == "critical"]
    neutral = [finding for finding in rows if finding.stance not in {"supporting", "critical"}]
    gaps = [finding for finding in rows if not (finding.evidence_ids or [])]

    agreements: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []

    for evidence_id in sorted(by_evidence):
        linked = by_evidence[evidence_id]
        agent_ids = sorted({finding.agent_id for finding in linked})
        if len(agent_ids) < 2:
            continue

        stances = {finding.stance for finding in linked}
        item = {
            "evidence_id": evidence_id,
            "agent_ids": agent_ids,
            "finding_ids": [finding.id for finding in linked],
            "stances": sorted(stances),
        }
        if "supporting" in stances and "critical" in stances:
            contradictions.append(item)
        else:
            agreements.append(item)

    agent_ids = sorted({finding.agent_id for finding in rows})
    evidence_backed = [finding for finding in rows if finding.evidence_ids]

    return {
        "finding_count": len(rows),
        "agent_count": len(agent_ids),
        "agent_ids": agent_ids,
        "supporting_count": len(supporting),
        "critical_count": len(critical),
        "neutral_count": len(neutral),
        "evidence_backed_count": len(evidence_backed),
        "evidence_gap_count": len(gaps),
        "evidence_ids": sorted(evidence_ids),
        "agreement_count": len(agreements),
        "contradiction_count": len(contradictions),
        "agreements": agreements,
        "contradictions": contradictions,
        "evidence_gaps": [
            {
                "finding_id": finding.id,
                "agent_id": finding.agent_id,
                "title": finding.title,
                "stance": finding.stance,
                "confidence": finding.confidence,
            }
            for finding in gaps
        ],
        "source_findings": [
            {
                "finding_id": finding.id,
                "agent_id": finding.agent_id,
                "category": finding.category,
                "stance": finding.stance,
                "confidence": finding.confidence,
                "evidence_ids": list(finding.evidence_ids or []),
                "title": finding.title,
            }
            for finding in rows
        ],
    }
