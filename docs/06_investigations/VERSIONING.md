# Investigation Versioning

Investigations are living objects, but understanding must never be silently overwritten.

`POST /api/v1/investigations/{id}/commit?message=...`

creates an immutable revision snapshot and publishes an `InvestigationCommitted` kernel event.
