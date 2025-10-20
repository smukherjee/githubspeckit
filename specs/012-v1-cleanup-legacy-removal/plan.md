
# Implementation Plan: V1.0 Release - Legacy Code Removal & Cleanup

**Branch**: `012-v1-cleanup-legacy-removal` | **Date**: 2025-10-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-v1-cleanup-legacy-removal/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

This feature removes all backward compatibility code, deprecated middleware, and legacy patterns to establish V1.0 as a clean baseline. Key changes include:
- Remove `DeprecationMiddleware` and `DeprecationWarningMiddleware` from codebase
- Unify all admin routes under `/api/v1/admin/*` prefix structure
- Enforce per-tenant email uniqueness with `UNIQUE(email, tenant_id)` constraint
- Finalize and publish V1.0 database schema with SchemaSpy documentation
- Remove legacy test code and fixtures
- Publish OpenAPI v1.0 specification
- Create comprehensive migration guide for pre-release users
- Provide complete dev environment setup (native Makefile + Docker Compose)

**Technical Approach**: Breaking change release following established migration pattern with Alembic for schema changes, router prefix updates in FastAPI, OpenAPI regeneration, and comprehensive testing to ensure performance maintained within 5% of baseline.

## Technical Context
**Language/Version**: Python 3.13 (compatible with 3.12+)  
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.x async, Alembic, Pydantic v2, pytest 8.4.2, httpx AsyncClient, OpenTelemetry, python-jose (JWT), Argon2id  
**Storage**: PostgreSQL (primary via psycopg[binary]>=3.1.0, asyncpg>=0.29.0), SQLite (dev/test via aiosqlite>=0.19.0), Redis >=6.4.0 (caching/rate limiting)  
**Testing**: pytest + pytest-asyncio 1.2.0, httpx.AsyncClient for API tests, schemathesis for contract validation, coverage ≥85% overall / ≥90% domain  
**Target Platform**: Linux/macOS server (production: containerized, dev: native or Docker Compose)
**Project Type**: Web backend API (multi-tenant SaaS)  
**Performance Goals**: p95 <200ms CRUD operations, maintain <5% variance from pre-V1.0 baseline, p99 <500ms for heavy operations  
**Constraints**: Breaking change release (no backward compatibility), V1.0 public release readiness, complete legacy removal, <5 minute dev environment bootstrap  
**Scale/Scope**: Multi-tenant architecture, 7 functional requirements + 3 non-functional requirements, ~55 implementation tasks estimated, 8-day timeline (Pre-Phase 0: 1 day, Phases 0-5: 7 days)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluate and explicitly confirm (checklist) before proceeding:

1. ✅ **Architecture**: No new domain logic; this is cleanup removing deprecated adapters. Domain layer remains framework-free (Principle I).
2. ✅ **Test-First & Coverage**: Existing test suite adapted to V1.0 routes. Coverage maintained ≥90% domain, ≥85% overall per FR-118 (Principle II).
3. ✅ **Multi-Tenancy**: No changes to tenant filtering logic; removing deprecated `tenant_id` query param that bypassed proper tenant context (Principles I & III).
4. ✅ **RBAC & Policies**: Route prefix changes don't affect policy engine. Admin routes remain policy-enforced (Principles III & VI).
5. ✅ **Auth Reuse**: No modifications to auth_core package; only router prefix changes in API layer (Principle VI).
6. ✅ **Switchable Persistence**: Database constraint change (email uniqueness) handled via Alembic migration; repository interfaces unchanged (Principle IV).
7. ✅ **Observability**: Audit events updated to include version metadata (v1.0.0). Metrics dashboards and log queries updated for new route patterns per NFR-027 (Principle V).
8. ✅ **API Versioning**: Breaking change documented in CHANGELOG-V1.0.md and MIGRATION-TO-V1.0.md. OpenAPI spec bumped to 1.0.0 (Principle V).
9. ✅ **Performance Budgets**: Benchmark tests ensure p95 latency within 5% of baseline per NFR-026 (Principle V).
10. ✅ **Unified Configuration**: New env var `RATE_LIMIT_USER_CREATION` (default: 100) follows single descriptor pattern (Principle VII).
11. ✅ **Developer Experience & Embed**: FR-121 adds Docker Compose (4 services) + native Makefile workflow. Both independent, <5 min bootstrap target (Principle VIII).
12. ⚠️ **Complexity**: Adding Docker Compose + SchemaSpy tooling increases initial setup complexity. **Justification**: Docker is optional (developers choose native or containerized). SchemaSpy provides production-grade ERD automation, reducing manual doc maintenance (Principle IX, Governance).
13. ✅ **Security Testing**: Rate limiting added (SEC-023). Email enumeration protection documented. No OWASP Top 10 regressions (Additional Constraints & Principle V).
14. ✅ **Code Quality & Simplicity**: This feature REMOVES code (deprecation middleware, legacy tests, backward compat branches). Net reduction in duplication and complexity (Principle IX).

**Constitution Compliance**: PASS with documented complexity justification.

Document any violation in Complexity Tracking with justification BEFORE continuing.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```text
# Hexagonal Architecture (Single Backend Project)
src/
├── domain/                  # Pure business logic (no framework deps)
│   ├── tenants/
│   ├── users/              # FR-116: Email uniqueness logic updated
│   ├── authz/              # Policy engine (unchanged)
│   ├── audit/
│   └── config/
├── auth_core/              # Reusable auth package (no changes)
├── adapters/
│   ├── api/
│   │   ├── app.py          # FR-115: Router prefix updates, FR-114: Remove deprecation middleware
│   │   ├── routers/
│   │   │   ├── tenants/    # FR-115: Prefix changes
│   │   │   ├── users.py    # FR-115: Prefix changes
│   │   │   ├── policies.py # FR-115: Prefix changes
│   │   │   └── audit.py
│   │   └── middleware/     # FR-114: Remove deprecation files
│   ├── persistence/        # FR-116: Repository email validation updated
│   ├── logging/
│   ├── observability/      # NFR-027: Version metadata added
│   ├── security/           # SEC-023: Rate limiting added
│   └── media/
├── services/
├── schemas/                # Pydantic models (no breaking changes expected)
└── cli/

alembic/
└── versions/               # FR-116: Email uniqueness migration

contracts/
├── openapi-base.yaml
├── openapi-auth-policy.yaml
├── openapi-observability.yaml
└── openapi-v1.0.yaml       # FR-119: New consolidated V1.0 spec

docs/
├── database-schema-v1.0.sql        # FR-117: Schema export
├── database-erd-v1.0.png           # FR-117: SchemaSpy ERD
├── database-indexes-v1.0.md        # FR-117: Index docs
├── migration-to-v1.0.md            # FR-120: Migration guide
├── CHANGELOG-V1.0.md               # FR-120: Breaking changes
└── CONTRIBUTING.md                 # FR-121: New contributor guide

config/
├── descriptor.toml         # FR-121: Add RATE_LIMIT_USER_CREATION
└── .env.example            # FR-121: New template

tests/
├── contract/               # FR-115: Update route paths
├── integration/            # FR-115: Update route paths
│   └── tenant_security/    # FR-116: Email uniqueness tests
└── unit/

docker-compose.yml          # FR-121: 4-service turnkey environment
Dockerfile                  # FR-121: API container
Makefile                    # FR-121: docker-up, docker-down targets
.env.example                # FR-121: Environment template
README.md                   # FR-121: Quick start guide
```

**Structure Decision**: Single hexagonal backend project. This is a cleanup feature modifying existing structure, not adding new domains. Changes are primarily:
- Removing files (deprecation middleware)
- Updating router prefixes (app.py, routers/)
- Adding migration (alembic/versions/)
- Adding documentation (docs/, contracts/)
- Adding dev automation (docker-compose.yml, Makefile updates)

## Phase 0: Outline & Research

### Research Tasks

**RT-001: Alembic Migration Patterns for UNIQUE Constraint Changes**
- **Context**: FR-116 requires changing from global `UNIQUE(email)` to composite `UNIQUE(email, tenant_id)`
- **Questions**:
  - How to safely drop existing constraint and add composite index?
  - Transaction safety considerations?
  - Rollback strategy (downgrade function)?
  - Handling existing data conflicts (duplicate emails within tenant)?
- **Output**: SQL patterns for upgrade/downgrade, pre-migration validation script approach

**RT-002: OpenAPI Spec Generation for Breaking Changes**
- **Context**: FR-119 requires publishing openapi-v1.0.yaml with deprecated endpoints removed
- **Questions**:
  - FastAPI automatic spec generation vs manual YAML curation?
  - How to mark endpoints as deprecated before removal (Sunset headers)?
  - Versioning strategy in OpenAPI info block?
  - Contract testing approach (schemathesis) for v1.0 spec?
- **Output**: OpenAPI generation workflow, version metadata structure

**RT-003: FastAPI Router Prefix Changes & Nesting**
- **Context**: FR-115 requires moving admin routes from `/api/v1/tenants` to `/api/v1/admin/tenants`
- **Questions**:
  - Router nesting patterns (`APIRouter` with sub-routers)?
  - Tags strategy for OpenAPI grouping?
  - Path parameter inheritance in nested routers?
  - Testing approach for route changes (avoid 404 regressions)?
- **Output**: Router refactoring pattern, testing checklist

**RT-004: Dev Environment Automation & Docker Compose Architecture**
- **Context**: FR-121 requires complete turnkey dev setup with Docker Compose (4 services) + native workflow
- **Questions**:
  - Docker Compose best practices for multi-service dev env?
  - Volume mount strategy for hot reload (API container)?
  - Healthcheck configuration for service dependencies?
  - Makefile targets for docker-up/down/reset?
  - Network isolation vs shared bridge?
- **Output**: docker-compose.yml structure, Makefile integration patterns

**RT-005: Email Enumeration Protection & Rate Limiting Strategies**
- **Context**: SEC-023 requires rate limiting (default: 100/hour/IP) to prevent email enumeration
- **Questions**:
  - FastAPI rate limiting middleware options (slowapi, fastapi-limiter)?
  - Storage backend for rate limit counters (Redis)?
  - Per-IP vs per-tenant vs per-user-session scoping?
  - Admin bypass mechanism (RBAC integration)?
  - HTTP 429 response format and headers (Retry-After)?
- **Output**: Rate limiting implementation strategy, configuration approach

### Consolidation

Create `research.md` with sections:

1. **Database Migration Strategy**
   - Decision: [Alembic migration pattern]
   - Rationale: [safety + rollback + validation]
   - Alternatives: [manual SQL, zero-downtime strategies]

2. **OpenAPI V1.0 Generation**
   - Decision: [FastAPI auto-gen + manual curation]
   - Rationale: [accuracy + maintainability]
   - Alternatives: [pure manual YAML, code-first tools]

3. **Router Architecture**
   - Decision: [nested APIRouter pattern]
   - Rationale: [modularity + OpenAPI grouping]
   - Alternatives: [flat routers with shared prefix]

4. **Dev Environment Strategy**
   - Decision: [Docker Compose 4-service + independent native workflow]
   - Rationale: [contributor flexibility + minimal friction]
   - Alternatives: [Docker-only, native-only]

5. **Rate Limiting Approach**
   - Decision: [slowapi or fastapi-limiter with Redis backend]
   - Rationale: [configurable + distributed-ready]
   - Alternatives: [in-memory counters, nginx-level limiting]

**Output**: research.md with all decisions documented

## Phase 1: Design & Contracts

Prerequisites: research.md complete

### 1. Data Model (`data-model.md`)

**Entities Modified**:

**User Entity**
- **Change**: Email uniqueness constraint
- **Before**: `CONSTRAINT users_email_key UNIQUE (email)` (global uniqueness)
- **After**: `CREATE UNIQUE INDEX idx_users_email_tenant ON users (email, tenant_id)` (per-tenant uniqueness)
- **Validation Rules**:
  - Email format: RFC 5322 compliant
  - Email case normalization: lowercase before storage
  - Uniqueness check: `SELECT 1 FROM users WHERE LOWER(email) = LOWER(?) AND tenant_id = ?`
  - Error on duplicate: `DomainError(code="EMAIL_ALREADY_EXISTS", message="Email '{email}' is already registered in this tenant")`
- **Migration Impact**: Existing users with same email across different tenants are allowed (no data conflict)

**Schema Version Metadata** (new table)
```sql
CREATE TABLE schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    description TEXT,
    checksum VARCHAR(64)  -- SHA256 of schema DDL
);
```

**No Entity Additions**: This is a cleanup feature; all changes are modifications to existing entities.

### 2. API Contracts (`contracts/`)

**contracts/openapi-v1.0.yaml** (consolidated V1.0 spec)

Structure:
```yaml
openapi: 3.1.0
info:
  title: githubspeckit Backend API
  version: 1.0.0
  description: Multi-tenant SaaS backend with RBAC, audit logging, and policy engine
  license:
    name: MIT

servers:
  - url: https://api.example.com
    description: Production
  - url: http://localhost:8000
    description: Local Development

paths:
  # Admin Routes (superadmin + tenant_admin within scope)
  /api/v1/admin/tenants:
    get: {...}      # List all tenants (superadmin) or tenant (tenant_admin)
    post: {...}     # Create tenant (superadmin)
  
  /api/v1/admin/tenants/{id}:
    get: {...}      # Get tenant
    put: {...}      # Update tenant
    delete: {...}   # Delete tenant (soft delete)
  
  /api/v1/admin/users:
    get: {...}      # List users (cross-tenant for superadmin)
    post: {...}     # Create user (with email uniqueness per-tenant)
  
  /api/v1/admin/policies:
    get: {...}      # List policies
    post: {...}     # Create policy
  
  /api/v1/admin/roles:
    get: {...}      # List roles
    post: {...}     # Create role
  
  /api/v1/admin/context/tenant:
    post: {...}     # Switch tenant context (tenant_admin+)
  
  # Tenant-Scoped Routes (authenticated users)
  /api/v1/tenants/{tenant_id}/users:
    get: {...}      # List users in tenant
  
  /api/v1/audit/events:
    get: {...}      # Query audit events (tenant-scoped)
  
  # Public Routes (no auth)
  /api/v1/auth/login:
    post: {...}     # JWT token issuance
  
  /api/v1/auth/refresh:
    post: {...}     # Token refresh
  
  /api/v1/health:
    get: {...}      # Health check (returns version: 1.0.0)

components:
  schemas:
    # Include all existing schemas from openapi-base.yaml, openapi-auth-policy.yaml, etc.
    # Update error responses to remove deprecation headers
  
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

**Breaking Changes Documented**:
- Removed: Query parameter `tenant_id` support (use headers instead)
- Removed: `X-API-Deprecation` and `Sunset` headers
- Changed: All admin routes now under `/api/v1/admin/*` prefix
- Changed: Email uniqueness scoped per-tenant (not global)

### 3. Contract Tests (Failing Initially)

**tests/contract/test_v1_admin_routes.py**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_tenants_list_requires_superadmin(client: AsyncClient):
    """GET /api/v1/admin/tenants requires superadmin role"""
    # Will fail initially until FR-115 implemented
    response = await client.get("/api/v1/admin/tenants")
    assert response.status_code == 401  # or 403 depending on auth

@pytest.mark.asyncio
async def test_admin_users_create_enforces_tenant_email_uniqueness(client: AsyncClient, auth_headers):
    """POST /api/v1/admin/users enforces per-tenant email uniqueness"""
    # Create user in tenant A
    response1 = await client.post("/api/v1/admin/users", json={
        "email": "test@example.com",
        "tenant_id": "tenant-a-uuid",
        ...
    }, headers=auth_headers)
    assert response1.status_code == 201
    
    # Duplicate in same tenant → 409
    response2 = await client.post("/api/v1/admin/users", json={
        "email": "test@example.com",
        "tenant_id": "tenant-a-uuid",
        ...
    }, headers=auth_headers)
    assert response2.status_code == 409
    assert "EMAIL_ALREADY_EXISTS" in response2.json()["code"]
    
    # Same email in different tenant → 201
    response3 = await client.post("/api/v1/admin/users", json={
        "email": "test@example.com",
        "tenant_id": "tenant-b-uuid",
        ...
    }, headers=auth_headers)
    assert response3.status_code == 201

# ... additional tests for all changed routes
```

**tests/contract/test_openapi_v1_compliance.py**
```python
import schemathesis

schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api_conforms_to_openapi_spec(case):
    """All endpoints match OpenAPI v1.0 spec"""
    case.call_and_validate()
```

### 4. Integration Test Scenarios (`quickstart.md`)

**quickstart.md** structure:
```markdown
# V1.0 Release Quickstart & Validation

## Prerequisites
- Python 3.13+
- PostgreSQL running
- Redis running (optional for basic tests)

## Setup
1. Clone repository and checkout `012-v1-cleanup-legacy-removal` branch
2. Run `make bootstrap` (or `make docker-up` for containerized)
3. Verify health: `curl http://localhost:8000/v1/health` → `{"status":"healthy","version":"1.0.0"}`

## Test Scenarios

### TS-001: Deprecated Routes Return 404
**Given**: V1.0 server running
**When**: Request old route `GET /api/v1/tenants` (without /admin prefix)
**Then**: Response 404 (route not found)

### TS-002: Admin Routes Require Authentication
**Given**: V1.0 server running
**When**: Request `GET /api/v1/admin/tenants` without auth
**Then**: Response 401 Unauthorized

### TS-003: Email Uniqueness Per-Tenant
**Given**: Authenticated as superadmin
**When**: Create user1@test.com in tenant A
**Then**: Success 201
**When**: Create user1@test.com in tenant B
**Then**: Success 201 (different tenant)
**When**: Create user1@test.com again in tenant A
**Then**: Error 409 with code EMAIL_ALREADY_EXISTS

### TS-004: OpenAPI Spec Version
**Given**: V1.0 server running
**When**: Request `GET /openapi.json`
**Then**: Response contains `"version": "1.0.0"` in info block

### TS-005: No Deprecation Headers
**Given**: V1.0 server running
**When**: Request any endpoint
**Then**: Response headers do NOT contain X-API-Deprecation or Sunset

### TS-006: Rate Limiting Applied
**Given**: V1.0 server with RATE_LIMIT_USER_CREATION=5
**When**: Attempt 6 POST /api/v1/admin/users from same IP within 1 hour
**Then**: 6th request returns 429 Too Many Requests

## Migration Validation
...
```

### 5. Agent Context Update

Execute:
```bash
.specify/scripts/bash/update-agent-context.sh copilot
```

**Expected Updates**:
- Tech Stack: Add "SchemaSpy (ERD generation)", "Docker Compose (4-service dev env)"
- Recent Deltas: Add "V1.0 cleanup: Removed deprecation middleware, unified admin routes, per-tenant email uniqueness"
- Constraints: Add "Breaking change release, <5% performance variance"

**Output**: `.github/copilot-instructions.md` updated with V1.0 context

## Phase 2: Task Planning Approach

Description: This section describes what the /tasks command will do - DO NOT execute during /plan.

**Task Generation Strategy**:

Tasks will be derived from Phase 1 design artifacts and organized into 10 categories matching the 8-day timeline:

### Pre-Phase 0: Database Audit & Tooling (Day 1) - 7 tasks
- Create `scripts/db_audit.sh` orchestration script
- Implement `scripts/detect_orphaned_tables.py`
- Implement `scripts/analyze_missing_indexes.py`
- Implement `scripts/check_sensitive_columns.py`
- Add `.github/workflows/db-audit.yml` (cron: Monday 9 AM UTC)
- Download and configure SchemaSpy (`tools/schemaspy.jar`)
- Create `.sqlfluff` configuration file + pre-commit hooks

### Category 1: Remove Deprecated Code (Days 2-3) - 8 tasks
- [P] Delete `src/adapters/api/deprecation.py`
- [P] Delete `src/adapters/api/middleware/deprecation_warning.py`
- Remove deprecation middleware registration from `app.py`
- Remove deprecated query parameter handling from routers
- Remove sunset header logic from response middleware
- [P] Remove backward compatibility branches in storage/media adapters
- [P] Delete legacy test files (`test_deprecated_*.py`)
- Run grep audit for "deprecated" comments and remove

### Category 2: Database Schema & Migration (Day 3) - 5 tasks
- Create Alembic migration: drop global email UNIQUE constraint
- Create Alembic migration: add composite UNIQUE index (email, tenant_id)
- Implement schema_version metadata table
- Create pre-migration validation script (check for email conflicts)
- Test migration upgrade/downgrade cycle

### Category 3: Router Prefix Updates (Days 3-4) - 10 tasks
- Update `src/adapters/api/routers/tenants/crud.py` → `/api/v1/admin` prefix
- Update `src/adapters/api/routers/users.py` → `/api/v1/admin` prefix
- Update `src/adapters/api/routers/policies.py` → `/api/v1/admin` prefix
- Update `src/adapters/api/routers/roles.py` → `/api/v1/admin` prefix
- Update `src/adapters/api/app.py` router includes with new prefixes
- [P] Update contract tests: test_tenants.py routes
- [P] Update contract tests: test_users.py routes
- [P] Update integration tests: tenant_security/ routes
- [P] Update unit tests: any hardcoded route references
- Verify no legacy `/api/v1/tenants` route exists (404 test)

### Category 4: Email Uniqueness Enforcement (Day 4) - 4 tasks
- Update user repository: add `get_by_email_and_tenant()` method
- Update user service: validate email uniqueness within tenant scope
- Update error messages: "Email already exists in this tenant"
- [P] Add contract tests: same email across tenants (allowed), same tenant (rejected)

### Category 5: Rate Limiting Implementation (Day 5) - 5 tasks
- Research and select rate limiting library (slowapi or fastapi-limiter)
- Add `RATE_LIMIT_USER_CREATION` to config descriptor
- Implement rate limiting middleware for POST /api/v1/admin/users
- Add admin bypass mechanism (RBAC integration)
- [P] Add security tests: rate limit enforcement, admin bypass

### Category 6: OpenAPI V1.0 Generation (Day 5) - 4 tasks
- Consolidate existing contract fragments into `contracts/openapi-v1.0.yaml`
- Update OpenAPI info block: version=1.0.0, remove deprecated endpoints
- Add rate limiting documentation to OpenAPI spec
- [P] Generate schemathesis contract tests from v1.0 spec

### Category 7: Documentation & Migration Guide (Day 6) - 6 tasks
- Create `docs/CHANGELOG-V1.0.md` with breaking changes list
- Create `docs/MIGRATION-TO-V1.0.md` step-by-step guide
- Update README.md: reference V1.0, add quick start
- Create `docs/database-schema-v1.0.sql` (pg_dump export)
- Generate `docs/database-erd-v1.0.png` via SchemaSpy
- Create `docs/database-indexes-v1.0.md` with index strategy

### Category 8: Dev Environment Setup (Day 7) - 8 tasks
- Create `docker-compose.yml` with 4 services (PostgreSQL, Redis, pgAdmin, API)
- Create `Dockerfile` for API container with hot-reload
- Add Makefile targets: docker-up, docker-down, docker-logs, docker-reset
- Create `.env.example` with all required environment variables
- Update README.md: Docker Compose quick start section
- Create `CONTRIBUTING.md` with dev workflow documentation
- Test native `make bootstrap` on clean macOS environment
- Test Docker `make docker-up` on clean Linux environment

### Category 9: Observability Updates (Day 7) - 3 tasks
- Add version metadata (v1.0.0) to audit event schema
- Update metrics dashboards for new route patterns (documentation)
- Update log aggregation queries for route changes (documentation)

### Category 10: Testing & Validation (Day 8) - 5 tasks
- Run full test suite: ensure 100% pass rate
- Execute quickstart.md validation scenarios end-to-end
- Run performance benchmarks: verify <5% variance from baseline
- Execute security regression tests: RBAC, tenancy boundaries
- Validate OpenAPI spec against OpenAPI 3.1.0 schema

**Ordering Strategy**:

1. **Pre-Phase 0 first** (database audit tooling setup)
2. **Sequential dependencies**:
   - Database migration BEFORE email uniqueness enforcement
   - Router updates BEFORE test updates
   - Code changes BEFORE documentation
3. **Parallel execution markers [P]**:
   - Independent file deletions
   - Parallel test file updates (different test files)
   - Parallel documentation generation (different docs)

**Estimated Total**: 65 tasks across 10 categories over 8 days (Pre-Phase 0: 1 day, Phases 0-5: 7 days)

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

Scope: These phases are beyond the scope of the /plan command.

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Docker Compose + SchemaSpy tooling (Principle XII) | Production-grade ERD automation reduces manual doc maintenance burden. Docker provides zero-friction onboarding for contributors without local PostgreSQL/Redis setup (addresses Constitution Principle VIII). | Manual ERD drawing: error-prone, stale quickly. Native-only setup: excludes contributors without DB experience or incompatible OS environments. |

**Net Impact**: Adding Docker Compose + SchemaSpy INCREASES initial complexity BUT REDUCES long-term maintenance and contributor friction. Both are optional (developers choose native or Docker). Trade-off justified per Governance item 5 (Complexity Gate) and Principle VIII (Developer Experience).


## Progress Tracking

This checklist is updated during execution flow.

**Phase Status**:

- [x] Phase 0: Research complete (/plan command) - research.md created with 5 key decisions
- [x] Phase 1: Design complete (/plan command) - data-model.md, quickstart.md, agent context updated
- [x] Phase 2: Task planning complete (/plan command - approach described, 65 tasks across 10 categories)
- [ ] Phase 3: Tasks generated (/tasks command) - Ready to execute `/tasks`
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS (with documented Docker/SchemaSpy complexity justification)
- [x] Post-Design Constitution Check: PASS (Phase 1 artifacts generated, no new violations)
- [x] All NEEDS CLARIFICATION resolved (clarifications completed in Session 2025-10-20)
- [x] Complexity deviations documented (Docker Compose + SchemaSpy justified in Complexity Tracking)

**Timeline**:

- Day 1: Pre-Phase 0 (Database audit tooling)
- Days 2-3: Remove deprecated code + database migration
- Days 3-4: Router prefix updates + email uniqueness
- Day 5: Rate limiting + OpenAPI v1.0
- Day 6: Documentation & migration guide
- Day 7: Dev environment setup + observability updates
- Day 8: Testing & validation

**Total Estimated Tasks**: 65 tasks across 10 categories

---
*Based on Constitution v1.5.1 - See `.specify/memory/constitution.md`*
