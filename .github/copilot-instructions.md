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
Python 3.13, FastAPI, SQLAlchemy async, Alembic, Argon2, python-jose, OpenTelemetry (api/sdk + instrumentation 0.58b0), httpx, pytest, Pillow 11.0.0 (image processing), python-magic 0.4.27 (file type detection).

## Directories (Planned)
```
src/
  domain/{tenants,users,authz,audit,config}
  auth_core/
  adapters/{api,persistence,logging,observability,security,media}
  services/
  schemas/
  cli/
contracts/ (generated OpenAPI fragments)
specs/
  001-modern-enterprise-grade/{spec.md,plan.md,research.md,data-model.md,quickstart.md,contracts/}
  003-user-profile-details/{spec.md,plan.md,research.md,data-model.md,quickstart.md,contracts/}
```

## OpenAPI Fragments Added
- contracts/openapi-base.yaml (tenants, users, auth token, embed exchange, audit events)
- contracts/openapi-auth-policy.yaml (login, refresh, password reset, policies)
- contracts/openapi-observability.yaml (log exports, metrics snapshot, redaction rules)
- specs/003-user-profile-details/contracts/openapi-user-profile.yaml (profile CRUD, photo upload)

## Pending (Early Phase 2)
- Generate failing contract tests under `tests/contract/`
- Implement repository interfaces + domain models
- Policy evaluation engine skeleton
- Bootstrap script & config hashing
- **NEW**: User profile details feature (Phase 1 complete, ready for /tasks)

## Constraints & Budgets
- p95 CRUD <200ms; login p95 <300ms with hash upgrades
- Photo upload/processing <5s p95; image serving <100ms p50
- Duplication <3%; complexity: avg B, max C

## Recent Deltas
- Added FR-077 audit metadata
- Added OpenAPI contract fragments
- Added quickstart.md (lint-fixed)
- Updated pyproject to Python >=3.12
- Marked Phase 1 complete in plan.md (Post-Design Check PASS)
- **NEW**: User profile details feature spec (003-user-profile-details)
  - Table: user_details (user_id FK, full_name, phone, address, 3 photo URLs)
  - Photo specs: 640x640 display, 96x96 thumbnail, 48x48 avatar (~200KB total)
  - Image processing: Pillow (resize, compress, EXIF strip), FastAPI BackgroundTasks
  - Storage: Local FS (dev) + S3 (prod) abstraction
  - Endpoints: GET/PUT /users/{id}/profile, POST/DELETE /users/{id}/profile/photo
  - Tenant isolation: Inherited from users.tenant_id JOIN
  - RBAC: Users edit own, admins view tenant, superadmin view all
- **✅ COMPLETE**: FR-122 Role Management & Hierarchy (V1.0 Phase 3.3.1)
  - Roles table: id (UUID), name, tenant_id (nullable for system roles), is_system, permissions (JSONB)
  - System roles: superadmin, tenant_admin, user (immutable, fixed UUIDs)
  - Permissions: 40+ constants (*, tenant:*, users:*, roles:*, policies:*, profile:update_own)
  - Domain layer: Role entity, 6 exceptions, permission validation, has_permission() with wildcard
  - Persistence layer: RoleModel, UserRoleModel (UUID role_id), SQLAlchemyRoleRepository (11 methods)
  - API layer: 7 endpoints in src/adapters/api/routers/admin/roles.py (GET/POST/PUT/DELETE roles, POST/DELETE assignments)
  - TenantContext pattern: All endpoints use get_tenant_context() from request.state (not User model)
  - RBAC enforcement: check_admin_access(), check_tenant_isolation(), system role immutability
  - Testing: 20 contract tests (test_role_management.py), 11 integration tests (test_role_api.py)
  - Tasks T076-T090 complete: Database → Domain → Persistence → API → Testing
<!-- END COPILOT CONTEXT -->
