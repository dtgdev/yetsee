from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.knowledge_graph.ontology import relationship_endpoints_valid, validate_entity_type, validate_relationship_type
from app.knowledge_graph.resolver import resolve_phrase
from app.models.observation import Observation


EXTRACTOR_VERSION = "domain-graph-assertion-v1"


@dataclass(frozen=True)
class DomainRule:
    event_type: str
    predicate: str
    subject_role: str
    subject_kind: str
    object_role: str
    object_kind: str
    domain: str


RULES: tuple[DomainRule, ...] = (
    DomainRule("product_launch", "COMPANY_LAUNCHED_PRODUCT", "company", "company", "product", "product", "business"),
    DomainRule("acquisition", "COMPANY_ACQUIRED_COMPANY", "acquirer", "company", "target_company", "company", "business"),
    DomainRule("partnership", "COMPANY_PARTNERED_WITH", "company", "company", "partner", "company", "business"),
    DomainRule("technology_development", "COMPANY_DEVELOPS_TECHNOLOGY", "company", "company", "technology", "technology", "technology"),
    DomainRule("technology_adoption", "COMPANY_ADOPTS_TECHNOLOGY", "company", "company", "technology", "technology", "technology"),
    DomainRule("patent", "PATENT_COVERS_TECHNOLOGY", "patent", "patent", "technology", "technology", "technology"),
    DomainRule("repository_implementation", "REPOSITORY_IMPLEMENTS_TECHNOLOGY", "repository", "repository", "technology", "technology", "technology"),
    DomainRule("funding_round", "COMPANY_RAISED_FUNDING", "company", "company", "funding_round", "funding_round", "investment"),
    DomainRule("investment", "INVESTOR_INVESTED_IN_COMPANY", "investor", "investor", "company", "company", "investment"),
    DomainRule("job_posting", "COMPANY_POSTED_JOB", "company", "company", "job_posting", "job_posting", "market"),
    DomainRule("demand_signal", "DEMAND_SIGNAL_FOR", "demand_signal", "demand_signal", "target", "entity", "market"),
    DomainRule("regulatory_event", "REGULATOR_ISSUED_EVENT", "regulator", "regulator", "regulatory_event", "regulatory_event", "regulatory"),
    DomainRule("filing", "FILING_CONCERNS", "filing", "filing", "target", "entity", "regulatory"),
)


def _slug(value: str) -> str:
    return resolve_phrase(value).canonical_key.replace(" ", "-")


def _entity(role: str, expected_kind: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    raw = payload.get(role)
    if raw is None:
        return None

    if isinstance(raw, str):
        name = raw.strip()
        if not name:
            return None
        resolved = resolve_phrase(name, default_kind=expected_kind)
        kind = resolved.kind if expected_kind == "entity" else expected_kind
        return {
            "kind": kind,
            "name": resolved.canonical_name if resolved.kind == kind else name,
            "key": f"{kind}:{_slug(resolved.canonical_name if resolved.kind == kind else name)}",
            "aliases": list(resolved.aliases),
        }

    if not isinstance(raw, dict):
        return None

    name = str(raw.get("name") or raw.get("canonical_name") or "").strip()
    if not name:
        return None
    kind = str(raw.get("kind") or expected_kind).strip()
    if expected_kind != "entity" and kind != expected_kind:
        return None
    if not validate_entity_type(kind):
        return None

    key = str(raw.get("key") or raw.get("canonical_key") or "").strip()
    if not key:
        key = f"{kind}:{_slug(name)}"

    return {
        "kind": kind,
        "name": name,
        "key": key,
        "aliases": list(raw.get("aliases") or []),
        "attributes": dict(raw.get("attributes") or {}),
    }


def _event_payload(observation: Observation) -> dict[str, Any] | None:
    payload = observation.payload or {}
    event = payload.get("domain_event")
    if isinstance(event, dict):
        return event

    event_type = payload.get("event_type")
    if event_type:
        return {**payload, "type": event_type}

    # Metric-to-event mapping is allowed only for structured observations whose
    # required role fields are present. The metric alone never creates a claim.
    metric = (observation.metric or "").strip().lower()
    if metric in {rule.event_type for rule in RULES}:
        return {**payload, "type": metric}
    return None


def extract_graph_assertions(observation: Observation) -> list[dict[str, Any]]:
    """Deterministically convert structured domain events into graph assertions.

    This extractor never interprets arbitrary free text and never writes to the
    canonical observation. It only emits a derived assertion when a registered
    rule has all required structured roles and valid ontology endpoints.
    """
    event = _event_payload(observation)
    if event is None:
        return []

    event_type = str(event.get("type") or event.get("event_type") or "").strip().lower()
    matching_rules = [rule for rule in RULES if rule.event_type == event_type]
    assertions: list[dict[str, Any]] = []

    for rule in matching_rules:
        subject = _entity(rule.subject_role, rule.subject_kind, event)
        obj = _entity(rule.object_role, rule.object_kind, event)
        if subject is None or obj is None:
            continue
        if not validate_relationship_type(rule.predicate):
            continue
        if not relationship_endpoints_valid(rule.predicate, subject["kind"], obj["kind"]):
            continue

        assertions.append(
            {
                "subject": subject,
                "predicate": rule.predicate,
                "object": obj,
                "confidence": float(event.get("confidence", 1.0)),
                "method": EXTRACTOR_VERSION,
                "provenance": {
                    "extractor": EXTRACTOR_VERSION,
                    "domain": rule.domain,
                    "event_type": event_type,
                    "structured_event": True,
                    "free_text_inference": False,
                },
            }
        )

    return assertions


def extraction_summary(observation: Observation) -> dict[str, Any]:
    assertions = extract_graph_assertions(observation)
    return {
        "observation_id": observation.id,
        "assertion_count": len(assertions),
        "assertions": assertions,
        "policy": {
            "derived_assertions": True,
            "canonical_observation_unchanged": True,
            "structured_fields_required": True,
            "free_text_inference": False,
            "ontology_validated": True,
            "extractor": EXTRACTOR_VERSION,
        },
    }
