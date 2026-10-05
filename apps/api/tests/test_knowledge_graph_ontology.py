from app.knowledge_graph.ontology import (
    ontology_manifest,
    validate_entity_type,
    validate_relationship_type,
)


def test_core_ontology_is_domain_neutral():
    manifest = ontology_manifest("core")
    names = {item["name"] for item in manifest["entity_types"]}
    assert {"entity", "actor", "organization", "product", "technology", "market", "event", "claim", "assessment", "opportunity", "risk"} <= names
    assert manifest["policy"]["domain_neutral_core"] is True
    assert validate_relationship_type("EVENT_INVOLVES")
    assert validate_relationship_type("EVENT_PRECEDES")


def test_science_pack_does_not_own_core_claim_or_source_types():
    manifest = ontology_manifest("science")
    names = {item["name"] for item in manifest["entity_types"]}
    assert "publication" in names
    assert "clinical_trial" in names
    assert "genomic_alteration" in names
    assert "claim" not in names
    assert "source" not in names


def test_business_technology_and_investment_packs_are_registered():
    assert validate_entity_type("company")
    assert validate_entity_type("patent")
    assert validate_entity_type("funding_round")
    assert validate_relationship_type("COMPANY_LAUNCHED_PRODUCT")
    assert validate_relationship_type("PATENT_COVERS_TECHNOLOGY")
    assert validate_relationship_type("COMPANY_RAISED_FUNDING")


def test_cross_domain_regulatory_relationship_can_target_business_science_or_technology():
    manifest = ontology_manifest("regulatory")
    relation = next(item for item in manifest["relationship_types"] if item["name"] == "REGULATORY_EVENT_CONCERNS")
    assert {"company", "product", "drug", "technology", "entity"} <= set(relation["target_types"])


def test_unknown_domain_is_rejected():
    try:
        ontology_manifest("unknown-domain")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown ontology domain should be rejected")
