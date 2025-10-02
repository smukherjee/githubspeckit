# Alembic Migration Environment (Phase 3 Preparation)

This directory scaffolds the database migration layer planned for Phase 3 (Persistence Layer & Durable Seed).

## Goals

- Provide deterministic, reviewable schema evolution.
- Enforce migration safety (manual diff review, no implicit destructive ops without approval).
- Surface current DB head revision through health/status endpoint (FR-015) once implemented.

## Structure

```text
alembic/
  README.md              # This file
  env.py                 # Alembic environment script (async engine wiring) (placeholder)
  versions/              # Individual migration scripts live here
```

## Conventions

- Revision file naming: `YYYYMMDD_HHMM_<summary>.py`.
- Deterministic ordering via timestamp prefix.
- Each migration includes upgrade & downgrade (even if downgrade raises NotImplemented for irreversible ops with rationale comment).
- No data-destructive change without explicit comment `# APPROVED: <reason>` and cross-reference to task/clarification.

## Async Engine

The future `env.py` will:

- Read configuration (DSN) from unified config loader (no direct env var scattering).
- Use SQLAlchemy async engine + run migrations in synchronous context via `run_sync` as necessary.
- Emit structured log lines: `migration.apply.start` / `migration.apply.end` with revision identifiers and duration.

## Safety Gates (Planned)

- Pre-commit hook / CI step: static check disallowing raw `DROP TABLE` / `ALTER TABLE ... DROP COLUMN` unless accompanied by approval comment.
- CI migration smoke: apply base -> head on empty DB then re-apply idempotently (TEST-DB-04).
- Startup check (IMPL-DB-15): service refuses (non-dev) if `head` != stored revision.

## Next Steps

1. Implement `env.py` (IMPL-DB-03).
2. Generate initial revision after SQLAlchemy models (IMPL-DB-02) merged.
3. Add migration safety CI scripts and update tasks accordingly.

---
This scaffold intentionally minimal until Phase 3 work begins.
