from types import SimpleNamespace

from app.agent_orchestration.synthesis import synthesize_findings


def finding(fid, agent, stance, evidence_ids):
    return SimpleNamespace(
        id=fid,
        agent_id=agent,
        category="test",
        stance=stance,
        confidence=0.8,
        evidence_ids=evidence_ids,
        title=f"Finding {fid}",
    )


def test_synthesis_preserves_shared_evidence_agreement_and_gaps():
    result = synthesize_findings([
        finding("f1", "evidence_agent", "critical", ["e1"]),
        finding("f2", "quality_agent", "critical", ["e1"]),
        finding("f3", "opportunity_analyst", "neutral", []),
    ])

    assert result["finding_count"] == 3
    assert result["agent_count"] == 3
    assert result["agreement_count"] == 1
    assert result["contradiction_count"] == 0
    assert result["evidence_gap_count"] == 1
    assert result["agreements"][0]["evidence_id"] == "e1"
    assert result["evidence_gaps"][0]["finding_id"] == "f3"


def test_synthesis_exposes_cross_agent_contradiction_on_same_evidence():
    result = synthesize_findings([
        finding("f1", "evidence_agent", "supporting", ["e1"]),
        finding("f2", "evidence_critic", "critical", ["e1"]),
        finding("f3", "graph_analyst", "neutral", ["e2"]),
    ])

    assert result["agreement_count"] == 0
    assert result["contradiction_count"] == 1
    assert result["contradictions"][0]["evidence_id"] == "e1"
    assert result["contradictions"][0]["agent_ids"] == ["evidence_agent", "evidence_critic"]
    assert result["evidence_ids"] == ["e1", "e2"]


def test_synthesis_excludes_prior_investigation_agent_output():
    result = synthesize_findings([
        finding("old", "investigation_agent", "critical", ["e1"]),
        finding("new", "quality_agent", "neutral", ["e2"]),
    ])

    assert result["finding_count"] == 1
    assert result["agent_ids"] == ["quality_agent"]
    assert result["evidence_ids"] == ["e2"]
