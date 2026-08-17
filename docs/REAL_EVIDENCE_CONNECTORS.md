# Real Evidence Connectors

YetSee Alpha 0.3 adds two independent-source connectors behind the existing Signal Lake contract.

## Reddit

`reddit` queries the topics configured in `EXTERNAL_SIGNAL_TOPICS` using Reddit's public search JSON endpoint. Each accepted observation preserves the raw Reddit payload plus YetSee provenance (`connector_id`, version, run id). The normalized metric is `discussion_engagement = score + num_comments`.

## Google Trends

`google_trends` queries the same configured topics with the isolated `pytrends` adapter. Google does not publish a supported Trends API for this use case, so the adapter is intentionally replaceable. Failures are recorded as connector-run failures rather than fabricated data.

## Neutral investigation matching

New external observations are matched conservatively to existing investigations by exact canonical topic/title. Matches are attached to the investigation with `stance=neutral`.

This is deliberate: ingestion may improve source diversity, but it must not silently claim that evidence supports or contradicts a hypothesis. Directional hypothesis evidence remains an explicit operation.

After matching, the Kernel creates a causally-linked `RefreshInvestigation` command. The Evidence Agent reruns and can clear source-diversity warnings when independent sources are actually present.

## Run

```bash
curl -X POST http://localhost:8100/api/v1/connectors/reddit/run
curl -X POST http://localhost:8100/api/v1/connectors/google_trends/run
```

Inspect:

```bash
curl http://localhost:8100/api/v1/connectors
curl 'http://localhost:8100/api/v1/observations?topic=running%20clubs'
curl http://localhost:8100/api/v1/investigations/<INVESTIGATION_ID>/agent-findings
curl 'http://localhost:8100/api/v1/kernel/commands?limit=20'
```
