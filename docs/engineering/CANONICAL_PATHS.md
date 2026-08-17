# Canonical application paths

YetSee Alpha uses a single monorepo layout.

- `apps/api` is the canonical FastAPI backend.
- `apps/web` is the canonical Next.js Studio frontend.
- `docker-compose.yml` builds only those two application directories.

Legacy top-level `backend/` and `frontend/` directories must not be restored or edited. They existed in earlier development archives and caused dependency drift because Docker was already building `apps/api` and `apps/web`.

When upgrading an older checkout that still contains them, remove the legacy directories only after confirming any local-only edits have been copied into the canonical paths:

```bash
# review first
diff -ru backend apps/api || true
diff -ru frontend apps/web || true

# after preserving intentional local changes
rm -rf backend frontend
```

All new code, dependency changes, Docker changes, tests, and documentation must target `apps/api` or `apps/web`.
