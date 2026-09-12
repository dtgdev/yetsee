from app.models.scientific_literature import ScientificPublication
from app.scientific_literature.study_independence import assess_pair


def publication(source_id, trial_ids=None, authors=None):
    return ScientificPublication(source_system="pubmed",source_id=source_id,pmid=source_id,doi=None,title="Study "+source_id,journal="Example Journal",authors_json=authors or [],metadata_json={"clinical_trial_ids":trial_ids or []},source_url=None,retrieval_ref=None,content_hash=(source_id*64)[:64])


def test_distinct_registered_trials_are_independent():
    result=assess_pair(publication("11111111",["NCT02296125"]),publication("22222222",["NCT02151981"]))
    assert result["status"]=="independent_trials"
    assert result["confidence"]==0.98
    assert result["shared_trial_ids"]==[]
    assert result["policy"]["canonical_evidence"] is False


def test_same_registered_trial_is_not_independent_replication():
    result=assess_pair(publication("33333333",["NCT00000001"]),publication("44444444",["NCT00000001"]))
    assert result["status"]=="same_trial"
    assert result["confidence"]==0.99
    assert result["shared_trial_ids"]==["NCT00000001"]


def test_author_overlap_without_trial_identity_is_only_likely_related():
    authors=[{"last_name":"Alpha","initials":"A"},{"last_name":"Beta","initials":"B"},{"last_name":"Gamma","initials":"C"},{"last_name":"Delta","initials":"D"}]
    other=authors[:3]+[{"last_name":"Epsilon","initials":"E"}]
    result=assess_pair(publication("55555555",authors=authors),publication("66666666",authors=other))
    assert result["status"]=="likely_related"
    assert result["confidence"]==0.65
    assert result["shared_author_count"]==3
    assert result["author_overlap"]>0.5


def test_missing_trial_identity_remains_unknown():
    left=[{"last_name":"Alpha","initials":"A"}]
    right=[{"last_name":"Omega","initials":"O"}]
    result=assess_pair(publication("77777777",authors=left),publication("88888888",authors=right))
    assert result["status"]=="unknown"
    assert result["confidence"]==0.5
    assert result["shared_author_count"]==0
