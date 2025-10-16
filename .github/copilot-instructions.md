# GitHub Copilot Context (Auto-Generated Phase 1)

KEEP CHANGES BETWEEN MARKERS. Short, <150 lines, recent deltas at bottom.

# Python Execution
Always activate venv before running Python:
- Activation: `source .venv/bin/activate`
- Combined command: `source .venv/bin/activate && python script.py`
- Terminal: Always start servers in seperate terminal and all curl commands in another terminal.

<!-- BEGIN COPILOT CONTEXT -->
## Project Essence
Modern multi-tenant FastAPI backend (hexagonal). Domains: tenants, users, policies, audit, embed. Reusable `auth_core` package. Strong observability (OpenTelemetry), structured logging with redaction/export, configuration via single descriptor file.

## Key Principles (Abbrev)
- Hexagonal: domain pure, adapters isolate infra.
- Multi-tenancy: tenant_id required, superadmin isolated path.
- RBAC + Policy Engine: tri-state (ALLOW/DENY/ABSTAIN); no inline role spaghetti.
- Auth: Argon2id hashing; JWT (python-jose); token replay protection placeholder.
- Observability: Tracing (FastAPI + SQLAlchemy), metrics snapshots, regression events.
- Config: Single YAML descriptor hashed at startup.
- Quality Gates: complexity (xenon), duplication (jscpd), safety vulnerability scan.
- Audit: FR-077 ensures created/updated metadata fields.

## Tech Stack
Python 3.13, FastAPI, SQLAlchemy async, Alembic, Argon2, python-jose, OpenTelemetry (api/sdk + instrumentation 0.58b0), httpx, pytest.

## Directories (Planned)
```
src/
  domain/{tenants,users,authz,audit,config}
  auth_core/
  adapters/{api,persistence,logging,observability,security}
  services/
  schemas/
  cli/
contracts/ (generated OpenAPI fragments)
specs/001-modern-enterprise-grade/{spec.md,plan.md,research.md,data-model.md,quickstart.md,contracts/}
```

## OpenAPI Fragments Added
- contracts/openapi-base.yaml (tenants, users, auth token, embed exchange, audit events)
- contracts/openapi-auth-policy.yaml (login, refresh, password reset, policies)
- contracts/openapi-observability.yaml (log exports, metrics snapshot, redaction rules)

## Pending (Early Phase 2)
- Generate failing contract tests under `tests/contract/`
- Implement repository interfaces + domain models
- Policy evaluation engine skeleton
- Bootstrap script & config hashing

## Constraints & Budgets
- p95 CRUD <200ms; login p95 <300ms with hash upgrades
- Duplication <3%; complexity: avg B, max C

## Recent Deltas
- Added FR-077 audit metadata
- Added OpenAPI contract fragments
- Added quickstart.md (lint-fixed)
- Updated pyproject to Python >=3.12
- Marked Phase 1 complete in plan.md (Post-Design Check PASS)
<!-- END COPILOT CONTEXT -->
