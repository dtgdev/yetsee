# 6.13 — Evidence Strength and Agreement View

## Purpose

The Evidence lens first answers how well each scientific relationship is supported. The detailed synthesis, passage inventory, quality, independence, contradiction, and gap assessments remain available below it.

## Contract

- Read the existing investigation-scoped `/evidence-profiles` endpoint. No evidence records, relationship confidence, review decisions, or hypothesis scores are changed.
- Render one card per relationship with its recorded strength class, passage stance counts, and distinct publication count. Contested relationships appear first.
- Expand a card to inspect the linked canonical passage text, publication identity, and source URL. Show a clear empty state for observation-only investigations and an unavailable state when the profile endpoint fails.
- Do not equate multiple passages with independent studies. A single publication never receives a cross-publication agreement claim. Strength is a deterministic classification of linked passages, not study quality, causality, or hypothesis probability.
- In the Structure inspector, keep duplicate graph labels distinct in relationship rows and use grammatical source and relationship counts.

## Verification

TypeScript, production build, and diff whitespace validation. Visual review on the local investigation after pulling: the current observation-only example should show the honest empty state; a literature-backed investigation should show expandable relationship cards with passage provenance.
