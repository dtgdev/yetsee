from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EntityTypeSpec:
    name: str
    domain: str
    description: str
    parent: str | None = None


@dataclass(frozen=True)
class RelationshipTypeSpec:
    name: str
    domain: str
    source_types: tuple[str, ...]
    target_types: tuple[str, ...]
    description: str
    directed: bool = True


ONTOLOGY_VERSION = "yetsee-ontology-v1"

CORE_ENTITY_TYPES: tuple[EntityTypeSpec, ...] = (
    EntityTypeSpec("entity", "core", "Domain-neutral graph entity."),
    EntityTypeSpec("actor", "core", "Person, organization, team, institution, or other acting party.", "entity"),
    EntityTypeSpec("organization", "core", "Organization or institution.", "actor"),
    EntityTypeSpec("person", "core", "Individual person.", "actor"),
    EntityTypeSpec("asset", "core", "Thing of value, capability, intellectual property, or resource.", "entity"),
    EntityTypeSpec("product", "core", "Product, service, or offering.", "asset"),
    EntityTypeSpec("technology", "core", "Technology, method, platform, or technical capability.", "asset"),
    EntityTypeSpec("market", "core", "Market, segment, category, or economic arena.", "entity"),
    EntityTypeSpec("event", "core", "Time-bounded occurrence such as launch, funding, trial, filing, or regulatory action.", "entity"),
    EntityTypeSpec("metric", "core", "Measured or reported quantitative variable.", "entity"),
    EntityTypeSpec("source", "core", "Origin of canonical evidence or information.", "entity"),
    EntityTypeSpec("claim", "core", "Derived assertion grounded in one or more evidence items.", "entity"),
    EntityTypeSpec("assessment", "core", "Derived quality, consistency, independence, risk, or gap assessment.", "entity"),
    EntityTypeSpec("opportunity", "core", "Derived opportunity hypothesis or opportunity object.", "entity"),
    EntityTypeSpec("risk", "core", "Derived or reported risk object.", "entity"),
    EntityTypeSpec("topic", "core", "General investigation or observation topic.", "entity"),
    EntityTypeSpec("behavior", "core", "Observed behavior or behavioral pattern.", "topic"),
    EntityTypeSpec("product_category", "core", "Product or service category.", "market"),
    EntityTypeSpec("industry", "core", "Industry or economic sector.", "market"),
)

DOMAIN_ENTITY_TYPES: dict[str, tuple[EntityTypeSpec, ...]] = {
    "science": (
        EntityTypeSpec("research_question", "science", "Scientific research question.", "entity"),
        EntityTypeSpec("publication", "science", "Scientific publication.", "source"),
        EntityTypeSpec("study", "science", "Scientific study distinct from its publications.", "event"),
        EntityTypeSpec("clinical_trial", "science", "Registered or identified clinical trial.", "study"),
        EntityTypeSpec("cohort", "science", "Study cohort or participant population.", "entity"),
        EntityTypeSpec("population", "science", "Scientific or clinical population.", "entity"),
        EntityTypeSpec("intervention", "science", "Treatment, exposure, procedure, or experimental intervention.", "entity"),
        EntityTypeSpec("drug", "science", "Drug or therapeutic agent.", "intervention"),
        EntityTypeSpec("disease", "science", "Disease, condition, or phenotype.", "entity"),
        EntityTypeSpec("biomarker", "science", "Measured biological marker.", "entity"),
        EntityTypeSpec("genomic_alteration", "science", "Genomic alteration or molecular feature.", "biomarker"),
        EntityTypeSpec("mechanism", "science", "Biological or scientific mechanism.", "entity"),
        EntityTypeSpec("assay", "science", "Assay or measurement method.", "technology"),
        EntityTypeSpec("outcome", "science", "Scientific or clinical outcome.", "entity"),
        EntityTypeSpec("evidence_gap", "science", "Derived scientific evidence gap.", "assessment"),
        EntityTypeSpec("drug_resistance", "science", "Drug-resistance state or phenotype.", "outcome"),
    ),
    "business": (
        EntityTypeSpec("company", "business", "Commercial organization.", "organization"),
        EntityTypeSpec("business_unit", "business", "Operating unit within a company.", "organization"),
        EntityTypeSpec("customer_segment", "business", "Customer or buyer segment.", "market"),
        EntityTypeSpec("competitor", "business", "Company acting as a competitor in a scoped market.", "company"),
        EntityTypeSpec("supplier", "business", "Supplier organization.", "company"),
        EntityTypeSpec("partner", "business", "Partner organization.", "company"),
        EntityTypeSpec("executive", "business", "Business executive or leader.", "person"),
        EntityTypeSpec("pricing_plan", "business", "Commercial pricing plan or tier.", "asset"),
        EntityTypeSpec("product_launch", "business", "Commercial product launch event.", "event"),
        EntityTypeSpec("partnership_event", "business", "Commercial partnership event.", "event"),
        EntityTypeSpec("acquisition", "business", "Acquisition or merger event.", "event"),
    ),
    "technology": (
        EntityTypeSpec("patent", "technology", "Patent or patent application.", "asset"),
        EntityTypeSpec("repository", "technology", "Software repository.", "asset"),
        EntityTypeSpec("benchmark", "technology", "Technical benchmark or evaluation.", "assessment"),
        EntityTypeSpec("model", "technology", "Computational or AI model.", "technology"),
        EntityTypeSpec("standard", "technology", "Technical standard or specification.", "asset"),
    ),
    "investment": (
        EntityTypeSpec("investor", "investment", "Investor or investing organization.", "actor"),
        EntityTypeSpec("funding_round", "investment", "Financing event.", "event"),
        EntityTypeSpec("valuation", "investment", "Reported or inferred valuation observation.", "metric"),
        EntityTypeSpec("revenue_metric", "investment", "Revenue or recurring-revenue metric.", "metric"),
        EntityTypeSpec("investment_thesis", "investment", "Derived or stated investment thesis.", "claim"),
        EntityTypeSpec("catalyst", "investment", "Potential catalyst relevant to an investment thesis.", "event"),
    ),
    "market": (
        EntityTypeSpec("job_posting", "market", "Hiring demand signal.", "event"),
        EntityTypeSpec("price_observation", "market", "Observed product or market price.", "metric"),
        EntityTypeSpec("demand_signal", "market", "Observed or derived demand signal.", "metric"),
    ),
    "regulatory": (
        EntityTypeSpec("regulator", "regulatory", "Regulatory organization.", "organization"),
        EntityTypeSpec("regulatory_event", "regulatory", "Regulatory filing, decision, approval, warning, or action.", "event"),
        EntityTypeSpec("filing", "regulatory", "Formal regulatory or corporate filing.", "source"),
    ),
}

CORE_RELATIONSHIP_TYPES: tuple[RelationshipTypeSpec, ...] = (
    RelationshipTypeSpec("SUPPORTED_BY", "core", ("claim",), ("source", "entity"), "Links a derived claim to supporting evidence or source."),
    RelationshipTypeSpec("CONTRADICTED_BY", "core", ("claim",), ("source", "entity"), "Links a derived claim to contradicting evidence or source."),
    RelationshipTypeSpec("DERIVED_FROM", "core", ("claim", "assessment", "opportunity", "risk"), ("source", "entity"), "Records derivation provenance."),
    RelationshipTypeSpec("ABOUT", "core", ("claim", "assessment", "source"), ("entity",), "Connects information to the entity it concerns."),
    RelationshipTypeSpec("PART_OF", "core", ("entity",), ("entity",), "Generic containment or membership relationship."),
    RelationshipTypeSpec("RELATED_TO", "core", ("entity",), ("entity",), "Generic governed fallback relation when a more specific relation is unavailable."),
    RelationshipTypeSpec("OBSERVED_ON", "core", ("entity",), ("source",), "Observation topic was observed on or through a source."),
    RelationshipTypeSpec("MEASURED_BY", "core", ("entity",), ("metric",), "Entity or topic is measured by a metric."),
    RelationshipTypeSpec("MENTIONS", "core", ("entity",), ("entity",), "Evidence-backed mention of another entity."),
    RelationshipTypeSpec("SEMANTICALLY_RELATED_TO", "core", ("entity",), ("entity",), "Deterministic semantic similarity relationship.", directed=False),
)

DOMAIN_RELATIONSHIP_TYPES: dict[str, tuple[RelationshipTypeSpec, ...]] = {
    "science": (
        RelationshipTypeSpec("PUBLICATION_REPORTS_STUDY", "science", ("publication",), ("study", "clinical_trial"), "Publication reports results from a study or trial."),
        RelationshipTypeSpec("PUBLICATION_CONTAINS_PASSAGE", "science", ("publication",), ("source",), "Publication contains or supplies a canonical source passage represented outside the graph."),
        RelationshipTypeSpec("STUDY_REGISTERED_AS_TRIAL", "science", ("study",), ("clinical_trial",), "Study is registered as the specified clinical trial."),
        RelationshipTypeSpec("STUDY_HAS_POPULATION", "science", ("study", "clinical_trial"), ("population", "cohort"), "Study includes the specified population or cohort."),
        RelationshipTypeSpec("STUDY_USES_INTERVENTION", "science", ("study", "clinical_trial"), ("intervention", "drug"), "Study evaluates or uses an intervention."),
        RelationshipTypeSpec("STUDY_USES_ASSAY", "science", ("study", "clinical_trial"), ("assay",), "Study uses the specified assay."),
        RelationshipTypeSpec("STUDY_MEASURES_OUTCOME", "science", ("study", "clinical_trial"), ("outcome",), "Study measures the specified outcome."),
        RelationshipTypeSpec("MECHANISM_CONTRIBUTES_TO", "science", ("mechanism", "genomic_alteration", "biomarker"), ("outcome", "disease", "entity"), "Scientific mechanism contributes to an outcome or state."),
        RelationshipTypeSpec("STUDY_REPLICATES", "science", ("study", "clinical_trial"), ("study", "clinical_trial"), "Study provides replication evidence for another study."),
        RelationshipTypeSpec("STUDY_OVERLAPS_WITH", "science", ("study", "clinical_trial", "cohort"), ("study", "clinical_trial", "cohort"), "Studies or cohorts share participants, trial identity, or material provenance.", directed=False),
        RelationshipTypeSpec("EVIDENCE_GAP_CONCERNS", "science", ("evidence_gap",), ("claim", "study", "population", "mechanism", "entity"), "Evidence gap concerns a graph object."),
        RelationshipTypeSpec("contributes_to", "science", ("mechanism", "genomic_alteration", "biomarker"), ("drug_resistance", "outcome", "disease", "entity"), "Compatibility relation used by current scientific grounding for contribution claims."),
        RelationshipTypeSpec("reported_as_resistance_mechanism", "science", ("mechanism", "genomic_alteration", "biomarker"), ("drug_resistance", "outcome", "entity"), "Compatibility relation used by current scientific candidate grounding."),
    ),
    "business": (
        RelationshipTypeSpec("COMPANY_LAUNCHED_PRODUCT", "business", ("company",), ("product",), "Company launched a product."),
        RelationshipTypeSpec("COMPANY_ACQUIRED_COMPANY", "business", ("company",), ("company",), "Company acquired another company."),
        RelationshipTypeSpec("COMPANY_COMPETES_WITH", "business", ("company",), ("company",), "Companies compete in a scoped market.", directed=False),
        RelationshipTypeSpec("COMPANY_PARTNERED_WITH", "business", ("company",), ("company", "partner"), "Company formed a partnership.", directed=False),
        RelationshipTypeSpec("PRODUCT_TARGETS_MARKET", "business", ("product",), ("market", "customer_segment"), "Product targets a market or customer segment."),
        RelationshipTypeSpec("PRODUCT_HAS_PRICING_PLAN", "business", ("product",), ("pricing_plan",), "Product is offered under a pricing plan."),
    ),
    "technology": (
        RelationshipTypeSpec("COMPANY_DEVELOPS_TECHNOLOGY", "technology", ("company",), ("technology", "model"), "Company develops a technology or model."),
        RelationshipTypeSpec("PATENT_COVERS_TECHNOLOGY", "technology", ("patent",), ("technology",), "Patent covers a technology."),
        RelationshipTypeSpec("REPOSITORY_IMPLEMENTS_TECHNOLOGY", "technology", ("repository",), ("technology",), "Repository implements a technology."),
        RelationshipTypeSpec("TECHNOLOGY_EVALUATED_BY", "technology", ("technology", "model"), ("benchmark",), "Technology is evaluated by a benchmark."),
        RelationshipTypeSpec("COMPANY_ADOPTS_TECHNOLOGY", "technology", ("company",), ("technology", "model"), "Company adopts or uses a technology."),
    ),
    "investment": (
        RelationshipTypeSpec("INVESTOR_INVESTED_IN_COMPANY", "investment", ("investor",), ("company",), "Investor invested in a company."),
        RelationshipTypeSpec("COMPANY_RAISED_FUNDING", "investment", ("company",), ("funding_round",), "Company completed a funding round."),
        RelationshipTypeSpec("FUNDING_ROUND_HAS_VALUATION", "investment", ("funding_round",), ("valuation",), "Funding round reports a valuation."),
        RelationshipTypeSpec("THESIS_CONCERNS_COMPANY", "investment", ("investment_thesis",), ("company",), "Investment thesis concerns a company."),
        RelationshipTypeSpec("CATALYST_AFFECTS_THESIS", "investment", ("catalyst",), ("investment_thesis",), "Catalyst may affect an investment thesis."),
    ),
    "market": (
        RelationshipTypeSpec("COMPANY_POSTED_JOB", "market", ("company",), ("job_posting",), "Company posted a job."),
        RelationshipTypeSpec("PRICE_OBSERVED_FOR", "market", ("price_observation",), ("product", "market"), "Price observation concerns a product or market."),
        RelationshipTypeSpec("DEMAND_SIGNAL_FOR", "market", ("demand_signal",), ("product", "technology", "market", "company"), "Demand signal concerns a market object."),
    ),
    "regulatory": (
        RelationshipTypeSpec("REGULATOR_ISSUED_EVENT", "regulatory", ("regulator",), ("regulatory_event",), "Regulator issued a regulatory event."),
        RelationshipTypeSpec("REGULATORY_EVENT_CONCERNS", "regulatory", ("regulatory_event",), ("company", "product", "drug", "technology", "entity"), "Regulatory event concerns a graph entity."),
        RelationshipTypeSpec("FILING_CONCERNS", "regulatory", ("filing",), ("company", "product", "entity"), "Filing concerns a graph entity."),
    ),
}


def entity_types(domain: str | None = None) -> tuple[EntityTypeSpec, ...]:
    if domain is None:
        items = [*CORE_ENTITY_TYPES]
        for pack in DOMAIN_ENTITY_TYPES.values():
            items.extend(pack)
        return tuple(items)
    if domain == "core":
        return CORE_ENTITY_TYPES
    return DOMAIN_ENTITY_TYPES.get(domain, ())


def relationship_types(domain: str | None = None) -> tuple[RelationshipTypeSpec, ...]:
    if domain is None:
        items = [*CORE_RELATIONSHIP_TYPES]
        for pack in DOMAIN_RELATIONSHIP_TYPES.values():
            items.extend(pack)
        return tuple(items)
    if domain == "core":
        return CORE_RELATIONSHIP_TYPES
    return DOMAIN_RELATIONSHIP_TYPES.get(domain, ())


def entity_type_spec(kind: str) -> EntityTypeSpec | None:
    return next((item for item in entity_types() if item.name == kind), None)


def relationship_type_spec(kind: str) -> RelationshipTypeSpec | None:
    return next((item for item in relationship_types() if item.name == kind), None)


def validate_entity_type(kind: str) -> bool:
    return entity_type_spec(kind) is not None


def validate_relationship_type(kind: str) -> bool:
    return relationship_type_spec(kind) is not None


def entity_type_is_a(kind: str, expected: str) -> bool:
    current = entity_type_spec(kind)
    seen: set[str] = set()
    while current is not None and current.name not in seen:
        if current.name == expected:
            return True
        seen.add(current.name)
        current = entity_type_spec(current.parent) if current.parent else None
    return False


def relationship_endpoints_valid(kind: str, source_kind: str, target_kind: str) -> bool:
    spec = relationship_type_spec(kind)
    if spec is None:
        return False
    source_ok = any(entity_type_is_a(source_kind, allowed) for allowed in spec.source_types)
    target_ok = any(entity_type_is_a(target_kind, allowed) for allowed in spec.target_types)
    return source_ok and target_ok


def ontology_manifest(domain: str | None = None) -> dict:
    domains = ["core", *DOMAIN_ENTITY_TYPES.keys()]
    if domain is not None and domain not in domains:
        raise KeyError(domain)
    return {
        "version": ONTOLOGY_VERSION,
        "scope": domain or "all",
        "domains": domains,
        "entity_types": [asdict(item) for item in entity_types(domain)],
        "relationship_types": [asdict(item) for item in relationship_types(domain)],
        "policy": {
            "domain_neutral_core": True,
            "domain_packs_are_extensible": True,
            "claims_assessments_opportunities_and_risks_are_derived": True,
            "ontology_does_not_make_evidence_canonical": True,
            "provenance_required_for_asserted_relationships": True,
        },
    }
