from __future__ import annotations

import re
from collections import Counter

from app.knowledge_graph.resolver import canonicalize, extract_known_entities, resolve_phrase
from app.semantic_engine.contracts import ConceptCandidate

# Concepts here are intentionally deterministic and dependency-light.  The
# interface is designed so NER/embedding/ontology providers can replace or
# augment these rules later without changing stored concepts or downstream APIs.
THEME_RULES: tuple[tuple[tuple[str, ...], str, str, float], ...] = (
    (("running club", "social running", "run club"), "Running Clubs", "behavior", 0.98),
    (("home batter", "residential batter", "battery storage"), "Home Batteries", "product_category", 0.96),
    (("ai agent", "agentic ai", "autonomous agent"), "AI Agents", "technology", 0.97),
    (("formal verification",), "Formal Verification", "technology", 0.95),
    (("zero knowledge", "zero-knowledge", "zk proof"), "Zero-Knowledge Proofs", "technology", 0.95),
    (("risc-v", "risc v", "riscv"), "RISC-V", "technology", 0.97),
    (("ai credit", "inference credit", "model credit"), "AI Compute Credits", "market", 0.90),
    (("system prompt", "prompt engineering"), "LLM System Prompts", "technology", 0.91),
    (("watermark", "text adulteration"), "AI Content Watermarking", "technology", 0.88),
    (("openrouter", "ai routing", "model router"), "AI Model Routing", "technology", 0.89),
    (("ai infra", "ai infrastructure", "gpu financing", "infra financing"), "AI Infrastructure", "market", 0.90),
    (("adblock", "ad blocker", "adblocker"), "Ad Blocking", "technology", 0.92),
    (("cloudflare", "nameserver", "analytics injection"), "Web Infrastructure Analytics", "technology", 0.82),
    (("swarm intelligence", "boids"), "Swarm Intelligence", "technology", 0.94),
    (("ceramic water filter", "water filter"), "Water Filtration", "product_category", 0.90),
    (("nuclear reactor", "control rods", "reactor shutdown"), "Nuclear Operations", "industry", 0.90),
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at", "with", "from", "is", "are",
    "was", "were", "be", "been", "being", "has", "have", "had", "it", "its", "this", "that", "these",
    "those", "you", "your", "we", "they", "their", "as", "by", "now", "new", "over", "into", "when",
    "why", "how", "what", "after", "before", "later", "more", "most", "may", "can", "will", "would",
    "should", "could", "than", "then", "about", "against", "out", "up", "down", "not", "no", "yes",
    "tell", "show", "hn", "video", "years", "year", "later", "purpose", "amount", "they", "should",
}

GENERIC_TERMS = {
    "news", "world", "support", "video", "years", "people", "today", "story", "article", "things", "time"
}


def _text(*values: object) -> str:
    return " ".join(str(v) for v in values if v is not None).strip()


def _add(result: dict[str, ConceptCandidate], candidate: ConceptCandidate) -> None:
    existing = result.get(candidate.canonical_key)
    if existing is None or candidate.confidence > existing.confidence:
        result[candidate.canonical_key] = candidate


def _theme_candidates(text: str) -> list[ConceptCandidate]:
    lowered = text.lower()
    results: list[ConceptCandidate] = []
    for needles, name, kind, confidence in THEME_RULES:
        matched = next((needle for needle in needles if needle in lowered), None)
        if not matched:
            continue
        results.append(ConceptCandidate(
            canonical_name=name,
            canonical_key=canonicalize(name),
            kind=kind,
            mention_text=matched,
            confidence=confidence,
            method="theme_rule_v1",
            attributes={"rule_terms": list(needles)},
        ))
    return results


def _keyphrase_candidates(text: str) -> list[ConceptCandidate]:
    tokens = [t for t in canonicalize(text).split() if len(t) > 2 and t not in STOPWORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    ranked = [token for token, _ in counts.most_common(8) if token not in GENERIC_TERMS]
    # Single tokens are intentionally lower-confidence; they help browsing but
    # should not independently promote an investigation.
    return [
        ConceptCandidate(
            canonical_name=token.title(),
            canonical_key=token,
            kind="keyword",
            mention_text=token,
            confidence=0.56,
            method="keyword_v1",
            attributes={"frequency": counts[token]},
        )
        for token in ranked[:5]
    ]


def extract_concepts(topic: str | None, payload: dict, source: str, metric: str) -> list[ConceptCandidate]:
    title = str(payload.get("title", ""))
    body = str(payload.get("text", payload.get("description", "")))
    text = _text(topic, title, body)
    result: dict[str, ConceptCandidate] = {}

    # Canonical catalog/alias matches become durable entities/concepts.
    for resolved in extract_known_entities(text):
        _add(result, ConceptCandidate(
            canonical_name=resolved.canonical_name,
            canonical_key=resolved.canonical_key,
            kind=resolved.kind,
            mention_text=resolved.canonical_name,
            confidence=0.96,
            method="entity_link_v1",
            attributes={"aliases": list(resolved.aliases)},
        ))

    for candidate in _theme_candidates(text):
        _add(result, candidate)

    # Connector topics that already look like durable concepts remain available,
    # but article-like titles are marked so quality gates can avoid promoting them.
    if topic:
        resolved = resolve_phrase(topic)
        word_count = len(canonicalize(topic).split())
        article_like = word_count >= 7 or source == "hacker_news" and word_count >= 5
        if resolved.canonical_key not in GENERIC_TERMS:
            _add(result, ConceptCandidate(
                canonical_name=resolved.canonical_name,
                canonical_key=resolved.canonical_key,
                kind=resolved.kind,
                mention_text=topic,
                confidence=0.62 if article_like else 0.88,
                method="title_fallback_v1" if article_like else "topic_v1",
                attributes={"article_like": article_like, "source": source, "metric": metric},
            ))

    # Lightweight keyphrases are useful graph/context features but are deliberately
    # too low-confidence to become investigations on their own.
    for candidate in _keyphrase_candidates(text):
        _add(result, candidate)

    return sorted(result.values(), key=lambda item: item.confidence, reverse=True)


def preferred_concept(concepts: list[ConceptCandidate]) -> ConceptCandidate | None:
    if not concepts:
        return None
    kind_rank = {
        "behavior": 10, "technology": 9, "market": 9, "industry": 8, "product_category": 8,
        "company": 7, "product": 7, "topic": 5, "keyword": 1,
    }
    eligible = [c for c in concepts if c.method != "title_fallback_v1" and c.kind != "keyword"]
    if not eligible:
        eligible = [c for c in concepts if c.kind != "keyword"]
    if not eligible:
        return None
    return max(eligible, key=lambda c: (kind_rank.get(c.kind, 3), c.confidence))
