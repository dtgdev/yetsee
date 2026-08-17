# Development Promotion Override

Production discovery quality gates remain strict. Local development can explicitly promote a WATCH candidate so the Investigation Runtime can be exercised before multiple live connectors are configured.

## API

```bash
curl -X POST \
  'http://localhost:8100/api/v1/discovery/candidates/<CANDIDATE_ID>/promote?override=true&reason=Local%20runtime%20testing'
```

The override:

- requires a reason;
- emits `CandidatePromotionOverridden`;
- stores the original quality-gate result in investigation attributes;
- is rejected when `ENVIRONMENT=production`;
- can be disabled with `ALLOW_MANUAL_PROMOTION=false`.

## Find the created investigation

```bash
curl http://localhost:8100/api/v1/investigations
curl http://localhost:8100/api/v1/investigations/by-slug/running-clubs
```

The CLI provides the same flow:

```bash
yetsee investigate list
yetsee investigate promote <CANDIDATE_ID> --override --reason "Local runtime testing"
yetsee investigate open running-clubs
```
