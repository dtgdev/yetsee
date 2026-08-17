# Semantic Engine

## Purpose

The Semantic Engine separates **source text** from **canonical meaning**.

Raw observations stay immutable. The Semantic Engine appends evidence-linked interpretations that downstream graph, discovery, investigation, and agent layers may reuse.

```text
Observation
  -> semantic extraction
  -> canonical concept(s)
  -> Knowledge Graph
  -> Discovery quality gates
```

## Current extractors

The baseline implementation is deterministic and dependency-light:

- canonical entity / alias linking
- durable theme rules
- topic normalization
- article-title fallback classification
- low-confidence keyphrase extraction

The stored contract is intentionally provider-neutral so future implementations can add or replace the baseline with transformer NER, embedding-based entity linking, ontology matching, topic models, or LLM-assisted extraction.

## Permanent rules

1. Semantic output never mutates observations.
2. Every concept points to the exact observation that produced it.
3. Extractor version is persisted.
4. Article-like titles are evidence, not automatically investigations.
5. Low-confidence keywords may enrich context but cannot independently justify promotion.
6. Discovery promotion requires evidence quantity, source diversity, and model agreement.

## Candidate quality gate

A discovery result is `candidate` only when it currently has:

- at least 3 evidence items
- at least 2 independent sources
- at least 2 agreeing discovery models

Otherwise it remains `watch`.

These thresholds are policy defaults, not canonical truth, and can evolve independently of the evidence history.
