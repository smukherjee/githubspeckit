# Feature Specification: V1.0 Release - Legacy Code Removal & Cleanup

**Feature ID**: 012  
**Priority**: 🔴 CRITICAL (Pre-V1.0 Release)  
**Status**: Planning  
**Owner**: Platform Team  
**Timeline**: 5-7 days  
**Related Specs**: 010 (Route Prefix), 011 (Email Uniqueness), 004 (Tenant Security Refactor)

---

## Overview

Prepare the codebase for V1.0 production release by removing all backward compatibility code, legacy APIs, deprecated patterns, and test scaffolding. Establish a clean baseline with unified API routes under `/api/v1/admin/*`, enforce per-tenant email uniqueness, and publish the finalized database schema as the V1.0 canonical structure.

This is a **breaking change release** that removes all deprecated features and establishes V1.0 as the stable API contract going forward.

---

## Clarifications

### Session 2025-10-20

- Q: What services should the Docker Compose setup include for the dev environment? → A: PostgreSQL + Redis + pgAdmin + API container (complete turnkey environment)
- Q: How should the native `make bootstrap` and Docker Compose workflows interact? → A: Make-primary - Docker Compose file exists but `make docker-up` is separate target, not integrated (developers can work natively without Docker until needed)
- Q: Which tool should generate the Entity-Relationship Diagram for `docs/database-erd-v1.0.png`? → A: SchemaSpy (Java-based, comprehensive HTML docs + ERD, minimal dev load, production-grade)
- Q: What rate limiting threshold should be applied to user creation attempts to prevent email enumeration? → A: Configurable via environment variable with default of 100 attempts/hour/IP
- Q: Is blue-green deployment strategy implementation in-scope for V1.0, or just documentation? → A: Out of scope - Remove from NFR-026, focus on code cleanup only
- Q: Should log export endpoint integrate with Prometheus/Grafana for real-time dashboards? → A: V1.0 implementation provides detailed JSON logs for debugging/forensics only. V2.0 will add Grafana Loki integration for real-time log dashboards. Current `/metrics` endpoint already Prometheus-compatible for metrics visualization.

---

## Business Context

### Problem Statement

The current codebase contains:
1. **Deprecated middleware** (`DeprecationMiddleware`, `DeprecationWarningMiddleware`) handling backward compatibility for `tenant_id` query parameters
2. **Legacy route patterns** mixing flat `/api/*` with hierarchical `/api/v1/admin/*` structures
3. **Dual email uniqueness implementations** (global vs per-tenant) causing confusion
4. **Legacy test fixtures and scaffolding** from earlier development phases
5. **Commented migration notes** and TODO markers for "remove after v1.0"
6. **Multiple versioning artifacts** (v0, v1) without a clean single version baseline

### Success Criteria

- ✅ Zero deprecated code paths in production codebase
- ✅ All API routes follow consistent `/api/v1/admin/*` structure (per spec 010)
- ✅ Email uniqueness enforced per-tenant with proper constraints (per spec 011)
- ✅ Database schema finalized and documented as V1.0 canonical
- ✅ All tests green with legacy test code removed
- ✅ OpenAPI spec reflects only V1.0 endpoints
- ✅ Documentation updated for V1.0 API contract
- ✅ Migration guide published for any users on pre-release versions

---

## Functional Requirements

### FR-114: Remove All Backward Compatibility Code

**User Story**: As a platform engineer, I want to remove all deprecated middleware and compatibility layers so the codebase has a single, clean code path for V1.0.

**Acceptance Criteria**:
- ✅ `DeprecationMiddleware` removed from `app.py`
- ✅ `DeprecationWarningMiddleware` removed from middleware stack
- ✅ Files `deprecation.py` and `middleware/deprecation_warning.py` deleted
- ✅ All "deprecated" comments and annotations removed
- ✅ Query parameter `tenant_id` support removed from all endpoints
- ✅ Sunset header logic removed
- ✅ Backward compatibility branches in storage/media adapters removed

**Technical Details**:
```python
# REMOVE FILES:
src/adapters/api/deprecation.py
src/adapters/api/middleware/deprecation_warning.py

# REMOVE FROM app.py:
from adapters.api.deprecation import DeprecationMiddleware
app.add_middleware(DeprecationMiddleware)

# CLEAN UP:
- All `if "tenant_id" in query_params` branches
- All sunset date configurations
- Legacy feature-flags deprecation warnings
```

**Testing**:
- Verify no tests reference deprecated middleware
- Confirm startup without deprecation middleware succeeds
- All integration tests pass without compatibility code

---

### FR-115: Unified Route Prefix Structure

**User Story**: As an API consumer, I want all admin endpoints under `/api/v1/admin/*` for clear organizational hierarchy and consistent URL patterns.

**Acceptance Criteria**:
- ✅ All admin routes use prefix `/api/v1/admin/*`
- ✅ Tenant-scoped resource routes use `/api/v1/tenants/{tenant_id}/*` pattern
- ✅ Public routes (auth, health) remain at `/api/v1/auth/*`, `/api/v1/health`
- ✅ Legacy flat route `/api/*` completely removed
- ✅ Router includes updated in `app.py`
- ✅ OpenAPI spec reflects new structure
- ✅ All tests updated with new route patterns

**Route Mapping** (Current → V1.0):

| Current Route | V1.0 Route | Scope |
|--------------|------------|-------|
| `/api/v1/tenants` (CREATE/LIST) | `/api/v1/admin/tenants` | Admin |
| `/api/v1/tenants/{id}` (GET/PUT/DELETE) | `/api/v1/admin/tenants/{id}` | Admin |
| `/api/v1/users` | `/api/v1/admin/users` | Admin (cross-tenant) |
| `/api/v1/tenants/{tenant_id}/users` | **KEEP** | Tenant-scoped |
| `/api/v1/policies` | `/api/v1/admin/policies` | Admin |
| `/api/v1/audit/events` | **KEEP** (tenant-scoped) | User |
| `/api/v1/admin/context/tenant` | **KEEP** | Admin (already correct) |
| `/api/v1/roles` | `/api/v1/admin/roles` | Admin |
| `/api/v1/feature-flags` | `/api/v1/admin/feature-flags` | Admin |

**Route Classification Matrix** (Complete V1.0 Endpoint Catalog):

| Endpoint | Method | RBAC Scope | Roles Allowed | Tenant Isolation |
|----------|--------|------------|---------------|------------------|
| `/api/v1/auth/login` | POST | Public | None (unauthenticated) | N/A |
| `/api/v1/auth/refresh` | POST | Public | None (unauthenticated) | N/A |
| `/api/v1/auth/revoke` | POST | Authenticated | Any authenticated user | N/A |
| `/api/v1/health` | GET | Public | None (unauthenticated) | N/A |
| `/api/v1/config` | GET | Public | None (unauthenticated) | N/A |
| `/api/v1/embed/exchange` | POST | Public | None (unauthenticated) | N/A |
| `/metrics` | GET | Public | None (monitoring) | N/A |
| `/api/v1/admin/tenants` | GET, POST | Admin | superadmin | Cross-tenant (superadmin sees all) |
| `/api/v1/admin/tenants/{id}` | GET, PUT, DELETE | Admin | superadmin, tenant_admin (own tenant) | Tenant-filtered for tenant_admin |
| `/api/v1/admin/users` | GET, POST | Admin | superadmin, tenant_admin | Cross-tenant for superadmin, tenant-scoped for tenant_admin |
| `/api/v1/admin/users/{id}` | GET, PUT, DELETE | Admin | superadmin, tenant_admin (same tenant) | Tenant-filtered |
| `/api/v1/admin/policies` | GET, POST | Admin | superadmin, tenant_admin | Tenant-scoped |
| `/api/v1/admin/policies/{id}` | GET, PUT, DELETE | Admin | superadmin, tenant_admin (same tenant) | Tenant-filtered |
| `/api/v1/admin/roles` | GET | Admin | superadmin, tenant_admin | Global (read-only) |
| `/api/v1/admin/feature-flags` | GET, POST | Admin | superadmin, tenant_admin | Tenant-scoped |
| `/api/v1/admin/context/tenant` | POST | Admin | superadmin, tenant_admin | Cross-tenant switch (superadmin only) |
| `/api/v1/tenants/{tenant_id}/users` | GET | Tenant-Scoped | Any authenticated user in tenant | Tenant-filtered by path param |
| `/api/v1/tenants/{tenant_id}/policies` | GET | Tenant-Scoped | Any authenticated user in tenant | Tenant-filtered by path param |
| `/api/v1/audit/events` | GET | Tenant-Scoped | Any authenticated user | Tenant-filtered automatically |
| `/api/v1/users/{id}/profile` | GET, PUT | User | Owner, tenant_admin, superadmin | Tenant-filtered |
| `/api/v1/users/{id}/profile/photo` | POST, DELETE | User | Owner, tenant_admin | Tenant-filtered |
| `/api/v1/logs/export` | GET | **Admin** | **superadmin, tenant_admin** | **Tenant-filtered for tenant_admin, cross-tenant for superadmin** |
| `/api/v1/metrics/snapshot` | GET | Public | None (monitoring) | N/A |

**RBAC Scope Definitions**:
- **Public**: No authentication required, accessible to anyone
- **Admin**: Requires `superadmin` or `tenant_admin` role (specific permissions vary by endpoint)
- **Tenant-Scoped**: Authenticated users can access resources within their tenant only
- **User**: Resource owner + authorized admins can access

**Implementation**:
```python
# app.py updates:
app.include_router(tenants_crud.router, prefix="/api/v1/admin", tags=["admin-tenants"])
app.include_router(users.router, prefix="/api/v1/admin", tags=["admin-users"])
app.include_router(policies.router, prefix="/api/v1/admin", tags=["admin-policies"])
app.include_router(roles.router, prefix="/api/v1/admin", tags=["admin-roles"])
app.include_router(feature_flags.router, prefix="/api/v1/admin", tags=["admin-feature-flags"])

# Remove legacy:
# app.include_router(tenants_crud.router, prefix="/api")  # DELETE THIS
```

**Testing**:
- All route tests updated to use `/api/v1/admin/*` paths
- Contract tests verify OpenAPI paths match implementation
- RBAC tests confirm admin-only enforcement on admin routes

---

### FR-116: Per-Tenant Email Uniqueness

**User Story**: As a system architect, I want email addresses to be unique per-tenant (not globally) so different tenants can independently manage their user namespaces.

**Acceptance Criteria**:
- ✅ Database constraint: `UNIQUE(email, tenant_id)` on users table
- ✅ Remove any global `UNIQUE(email)` constraint
- ✅ Alembic migration created for constraint change
- ✅ User creation validates email uniqueness within tenant scope
- ✅ Error messages updated: "Email already exists in this tenant"
- ✅ Tests cover: same email across different tenants (allowed), duplicate email same tenant (rejected)

**Database Migration**:
```sql
-- Alembic migration: upgrade()
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;  -- Remove global unique
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_tenant 
ON users (email, tenant_id);

-- Alembic migration: downgrade()
DROP INDEX IF EXISTS idx_users_email_tenant;
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);  -- Restore global (risky!)
```

**Validation Logic**:
```python
# In user repository/service:
async def create_user(...):
    # Check uniqueness within tenant
    existing = await self.get_by_email_and_tenant(email, tenant_id)
    if existing:
        raise DomainError(
            code="EMAIL_ALREADY_EXISTS",
            message=f"Email '{email}' is already registered in this tenant"
        )
```

**Testing**:
- Test: Create user1@example.com in tenant A → success
- Test: Create user1@example.com in tenant B → success (different tenant)
- Test: Create user1@example.com again in tenant A → 409 Conflict
- Test: Migration rollback works (downgrade test)

---

### FR-117: Database Schema V1.0 Finalization

**User Story**: As a database administrator, I want a published V1.0 schema document that serves as the canonical reference for all production deployments.

**Acceptance Criteria**:
- ✅ Database schema exported to `docs/database-schema-v1.0.sql`
- ✅ Entity-relationship diagram generated via **SchemaSpy** to `docs/database-erd-v1.0.png`
- ✅ All foreign key constraints documented
- ✅ Index strategy documented with justifications
- ✅ Tenant isolation patterns clearly marked
- ✅ Migration path from any pre-release version documented
- ✅ Schema includes version metadata table
- ✅ SchemaSpy HTML documentation published (includes interactive ERD, table details, relationships)

**Deliverables**:
1. **`docs/database-schema-v1.0.sql`**: Full DDL export (PostgreSQL)
2. **`docs/database-erd-v1.0.png`**: Entity-relationship diagram
3. **`docs/database-indexes-v1.0.md`**: Index documentation with performance notes
4. **`docs/migration-to-v1.0.md`**: Migration guide from pre-release versions

**Schema Metadata Table**:
```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    description TEXT,
    checksum VARCHAR(64)  -- SHA256 of schema DDL
);

INSERT INTO schema_version (version, description) 
VALUES ('1.0.0', 'Initial V1.0 release schema');
```

**Testing**:
- Fresh database creation from V1.0 schema file succeeds
- All Alembic migrations from empty DB reach V1.0 head
- Schema checksum validation test

---

### FR-118: Legacy Test Code Removal

**User Story**: As a test maintainer, I want to remove all deprecated test fixtures, legacy test patterns, and commented-out test code to keep the test suite clean and maintainable.

**Acceptance Criteria**:
- ✅ All commented-out tests removed
- ✅ Legacy fixture patterns removed (if any duplicates exist)
- ✅ Tests for deprecated middleware removed
- ✅ Tests for old route paths removed
- ✅ Test helpers for backward compatibility removed
- ✅ Skipped tests reviewed: either fixed or permanently removed
- ✅ Test coverage maintained at >85% overall, >90% domain

**Cleanup Targets**:
```python
# REMOVE:
tests/integration/test_deprecated_tenant_id_param.py  # If exists
tests/contract/test_legacy_routes.py  # If exists
# Any tests with @pytest.mark.skip(reason="legacy")

# UPDATE:
# All test fixtures to use only V1.0 routes
# All test assertions to expect V1.0 error messages
```

**Testing**:
- Full test suite runs in <60 seconds
- No skipped tests related to legacy features
- Coverage report shows no untested legacy branches

---

### FR-119: OpenAPI Spec V1.0 Publication

**User Story**: As an API consumer, I want a published V1.0 OpenAPI specification that documents only the current stable API without any deprecated endpoints.

**Acceptance Criteria**:
- ✅ OpenAPI spec generated: `contracts/openapi-v1.0.yaml`
- ✅ Spec version set to `1.0.0`
- ✅ All deprecated endpoints removed from spec
- ✅ New `/api/v1/admin/*` routes documented
- ✅ Schema examples include realistic data
- ✅ Security schemes documented (JWT bearer)
- ✅ Rate limiting info included in spec
- ✅ Spec published to public location (e.g., GitHub Pages, docs site)

**OpenAPI Metadata**:
```yaml
openapi: 3.1.0
info:
  title: githubspeckit Backend API
  version: 1.0.0
  description: |
    Multi-tenant SaaS backend with RBAC, audit logging, and policy engine.
    
    **Base URL**: `https://api.example.com`
    
    **Authentication**: Bearer JWT tokens (obtained via `/api/v1/auth/login`)
    
    **Versioning**: This is V1.0, the stable release API contract.
  contact:
    name: API Support
    email: api-support@example.com
  license:
    name: MIT
servers:
  - url: https://api.example.com
    description: Production
  - url: http://localhost:8000
    description: Local Development
```

**Testing**:
- OpenAPI spec validates against OpenAPI 3.1.0 schema
- All documented endpoints are reachable
- Schemathesis contract tests pass against live API

---

### FR-120: Documentation & Migration Guide

**User Story**: As a developer upgrading from pre-release, I want clear documentation of what changed in V1.0 and how to migrate my integration.

**Acceptance Criteria**:
- ✅ `docs/CHANGELOG-V1.0.md` created with all breaking changes
- ✅ `docs/MIGRATION-TO-V1.0.md` provides step-by-step upgrade guide
- ✅ README updated to reference V1.0 as current version
- ✅ API quickstart guide updated with V1.0 routes
- ✅ All internal documentation references updated (no v0, pre-release mentions)

**Migration Guide Structure**:
```markdown
# Migration Guide: Pre-Release → V1.0

## Breaking Changes

### 1. Route Structure Changes
**Before**: `/api/v1/tenants` (mixed admin/user)
**After**: `/api/v1/admin/tenants` (admin-only)

**Action Required**: Update all API client calls to use `/api/v1/admin/*` prefix

### 2. Email Uniqueness Scope
**Before**: Email globally unique (cross-tenant)
**After**: Email unique per-tenant

**Action Required**: Review user management logic if you relied on global email uniqueness

### 3. Deprecation Headers Removed
**Before**: Responses included `X-API-Deprecation` headers
**After**: No deprecation headers (clean V1.0 API)

**Action Required**: Remove any client logic parsing deprecation headers

## Step-by-Step Migration

1. **Database**: Run Alembic migration to V1.0 head
   ```bash
   alembic upgrade head
   ```

2. **API Clients**: Update route prefixes
   ```python
   # Old:
   response = client.get("/api/v1/tenants")
   
   # New:
   response = client.get("/api/v1/admin/tenants")
   ```

3. **Tests**: Update test fixtures and assertions

4. **Verify**: Run health check at `/api/v1/health` confirms V1.0
```

---

## Non-Functional Requirements

### NFR-026: Performance Maintained

**Requirement**: V1.0 cleanup must not degrade performance.

**Acceptance Criteria**:
- ✅ Benchmark tests show p95 latency within 5% of pre-V1.0
- ✅ Database query plans reviewed for new constraints
- ✅ Index strategy validated for per-tenant email uniqueness

---

### NFR-027: Observability Continuity

**Requirement**: All observability (logs, metrics, traces) must continue functioning through V1.0 transition.

**Acceptance Criteria**:
- ✅ Audit events include version metadata (v1.0.0)
- ✅ Metrics dashboards updated for new route patterns
- ✅ Log aggregation queries updated for route changes
- ✅ Distributed tracing continues without gaps

---

### FR-121: Complete Dev Environment Setup

**Requirement**: Provide turnkey dev environment automation for open source contributors with <5 minute setup time from repository clone to running API.

**Implementation**:
- **Makefile automation** (comprehensive targets already implemented):
  - `make bootstrap` - Complete fresh installation (PostgreSQL setup, migrations, seed data, server start)
  - `make dev` - Install all dev dependencies (includes pytest-asyncio, coverage, mypy, ruff)
  - `make test` - Run complete test suite
  - `make db-reset` - Drop, recreate, migrate, and seed database
  - `make redis-start` - Start Redis server in background
  - `make server-start` - Start API server in background (with hot reload)
  - `make server-stop` - Stop API server
  - `make health` - Verify API health endpoint
- **Dependency management**:
  - All runtime and dev dependencies declared in `pyproject.toml`
  - Lock file (`requirements.txt`) autogenerated with SHA256 hashes via `uv export`
  - ✅ **Redis**: `redis>=6.4.0` (present)
  - ✅ **PostgreSQL**: `psycopg[binary]>=3.1.0`, `asyncpg>=0.29.0` (present)
  - ✅ **SQLite**: `aiosqlite>=0.19.0` (present for local dev/test)
  - ✅ **Dev tools**: pytest>=8.2, pytest-asyncio>=1.2.0, coverage>=7.5, mypy>=1.10, ruff>=0.13.2
- **Database initialization**:
  - `scripts/seed_infysight.py` creates initial tenant and superadmin:
    - **Tenant**: `infysight` (slug: `infysight`)
    - **Superadmin**: `infysightsa@infysight.com` (password: `infysightsa123`, role: superadmin)
- **Redis usage**: Caching, rate limiting, session storage (optional for basic API functionality)
- **Development workflow**: Hot reload enabled via `uvicorn --reload`

**Quick Start Flow** (target: <5 minutes):
```bash
# 1. Clone repository
git clone https://github.com/sujoymukherjee-corp/githubspeckit.git
cd githubspeckit

# 2. Prerequisites check
# - Python 3.13 (or 3.12+)
# - PostgreSQL running (psql accessible)
# - Redis running (optional, auto-start via Makefile)

# 3. Bootstrap complete environment
make bootstrap
# Output:
# - Creates .venv with all dependencies
# - Creates PostgreSQL database "infysight_users"
# - Runs Alembic migrations
# - Seeds infysight tenant + superadmin user
# - Starts API server on http://localhost:8000

# 4. Verify health
curl http://localhost:8000/v1/health
# Expected: {"status":"healthy","version":"1.0.0"}

# 5. Login and test
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=infysightsa@infysight.com&password=infysightsa123"
```

**Acceptance Criteria**:
- [x] `make bootstrap` completes without errors on macOS/Linux
- [x] PostgreSQL database created and seeded with `infysight` tenant and `infysightsa@infysight.com` superadmin
- [x] Redis server starts successfully (or provides clear instructions if not installed)
- [x] API server starts and responds to health checks within 30 seconds
- [x] All dependencies (redis, postgresql, sqlite) declared in `pyproject.toml` and synchronized to `requirements.txt`
- [ ] **README.md** updated with:
  - [ ] Quick start guide (<5 min to first API call)
  - [ ] Prerequisites (Python, PostgreSQL, optional Redis)
  - [ ] Troubleshooting section (common setup issues)
- [ ] **CONTRIBUTING.md** created documenting:
  - [ ] Dev workflow (branch strategy, commit conventions)
  - [ ] Testing requirements (unit + integration tests required for PRs)
  - [ ] Code quality gates (ruff, mypy, coverage ≥85%)
  - [ ] PR process and review expectations
- [ ] **`.env.example`** created with all required environment variables:
  - [ ] `DATABASE_URL` (default: `postgresql+asyncpg://...`)
  - [ ] `REDIS_URL` (default: `redis://localhost:6379/0`)
  - [ ] `SECRET_KEY` (placeholder, must be regenerated for production)
  - [ ] `LOG_LEVEL` (default: `INFO`)
- [ ] **Docker Compose** complete turnkey environment for contributors without local setup:
  - [ ] `docker-compose.yml` with **4 services**: PostgreSQL 15, Redis 7, pgAdmin 4, API container (Python 3.13)
  - [ ] PostgreSQL service: Port 5432, persistent volume `postgres_data`, healthcheck
  - [ ] Redis service: Port 6379, persistent volume `redis_data`
  - [ ] pgAdmin service: Port 5050 (web UI), pre-configured server connection to PostgreSQL
  - [ ] API service: Port 8000, built from `Dockerfile`, depends on PostgreSQL + Redis, hot-reload via volume mount
  - [ ] **Network**: Single bridge network `githubspeckit-net` for service communication
  - [ ] **Makefile integration**: 
    - `make docker-up` - Start all services (detached mode)
    - `make docker-down` - Stop and remove containers
    - `make docker-logs` - Tail logs from all services
    - `make docker-reset` - Full cleanup (containers + volumes)
  - [ ] **Independent workflow**: Docker and native `make bootstrap` do NOT interact (user chooses one path)

**Technical Details**:
- **Hot reload**: `uvicorn --reload` watches file changes, restarts server automatically
- **Testing**: `pytest-asyncio` for async tests, `httpx.AsyncClient` for API integration tests
- **Database abstraction**: SQLAlchemy async, supports PostgreSQL (primary) and SQLite (dev/test)
- **Observability**: OpenTelemetry instrumentation, structured logging with JSON output
- **Security**: Argon2id password hashing, JWT tokens (python-jose), RBAC + policy engine

**Release Readiness Checklist**:
- [ ] All Makefile targets tested on clean macOS and Linux environments
- [ ] Bootstrap flow validated end-to-end (<5 min from clone to API health check)
- [ ] Documentation reviewed by external contributor (usability test)
- [ ] All acceptance criteria for FR-121 marked complete
- [ ] Version bumped to `v1.0.0` in `pyproject.toml` and `__version__`
- [ ] CHANGELOG.md includes V1.0 release notes with breaking changes highlighted
- [ ] GitHub release created with binaries/wheels (if applicable)

---

## Technical Architecture

### Component Changes

```mermaid
graph TD
    A[API Gateway] --> B[V1.0 Routes]
    B --> C[/api/v1/admin/*]
    B --> D[/api/v1/auth/*]
    B --> E[/api/v1/tenants/{id}/*]
    
    C --> F[Admin Services]
    E --> G[Tenant Services]
    D --> H[Auth Services]
    
    F --> I[Database V1.0 Schema]
    G --> I
    H --> I
    
    I --> J[UNIQUE email,tenant_id]
    I --> K[schema_version table]
    
    style C fill:#f9f,stroke:#333
    style J fill:#9f9,stroke:#333
    style K fill:#9f9,stroke:#333
```

### Observability Architecture (V1.0)

**Metrics (Prometheus-Compatible)**:
- Endpoint: `GET /metrics` (Prometheus text format)
- Purpose: Real-time numeric metrics (counters, gauges, histograms)
- Integration: Prometheus scrapes `/metrics` → Grafana visualizes via Prometheus datasource
- Metrics Available:
  - `active_users` (gauge, per-tenant)
  - `auth_failures_total` (counter, per-tenant)
  - `policy_denials_total` (counter, per-tenant)
  - `rate_limit_hits_total` (counter, per-tenant)
  - `policy_evaluation_latency_seconds` (histogram)

**Logs (JSON Export for Forensics)**:
- Endpoint: `GET /api/v1/logs/export` (JSON format, **authenticated**)
- Purpose: On-demand export for compliance, debugging, forensic analysis
- Filters: `tenant_id`, `category`, `correlation_id`, `since`, `until`, `limit`
- **NOT for real-time dashboards**: Grafana cannot query REST JSON endpoints directly
- **V2.0 Roadmap**: Add Grafana Loki integration for real-time log aggregation + searchable dashboards

**Data Flow Separation**:
```
Application Metrics → PromClientAdapter → /metrics → Prometheus → Grafana (real-time dashboards)
Application Logs → InMemoryStructuredLogSink → /api/v1/logs/export → JSON download (forensic analysis)
```

**V2.0 Enhancement** (Deferred):
```
Application Logs → LokiLogSink → Loki → Grafana (unified metrics + logs dashboards)
```

### Removed Components

- **Deprecation Middleware**: `DeprecationMiddleware`, `DeprecationWarningMiddleware`
- **Legacy Routes**: Flat `/api/*` patterns
- **Compatibility Code**: Query parameter `tenant_id` support, sunset headers
- **Legacy Tests**: Deprecated middleware tests, old route tests

### Data Model Changes

**Users Table**:
```sql
-- OLD CONSTRAINT:
CONSTRAINT users_email_key UNIQUE (email)

-- NEW CONSTRAINT:
CREATE UNIQUE INDEX idx_users_email_tenant ON users (email, tenant_id);
```

---

## Security Considerations

### SEC-023: Email Enumeration Protection

**Risk**: Per-tenant email uniqueness could enable email enumeration attacks across tenants.

**Mitigation**:
- **Rate limiting**: User creation attempts limited to configurable threshold (default: 100 attempts/hour/IP)
  - Configured via environment variable: `RATE_LIMIT_USER_CREATION` (default: `100`)
  - Returns HTTP 429 (Too Many Requests) when exceeded
  - Scope: Per source IP address
  - Exemptions: Admin API tokens with appropriate RBAC can bypass for bulk operations
- Generic error messages ("Email already exists") without tenant hints
- Audit log suspicious patterns (rapid email checks across tenants)

### SEC-024: Migration Data Integrity

**Risk**: Email constraint changes could cause data corruption if not carefully migrated.

**Mitigation**:
- Pre-migration validation script checks for duplicate emails within tenants
- Migration runs inside transaction
- Post-migration verification confirms all emails unique per tenant

---

## Testing Strategy

### Test Plan

| Test Type | Coverage | Focus |
|-----------|----------|-------|
| Unit | Domain logic | Email validation, user creation |
| Integration | API endpoints | New route structure, error responses |
| Contract | OpenAPI spec | Schema validation, path matching |
| Migration | Database | Constraint creation, rollback |
| Performance | Benchmarks | p95 latency maintained |
| Security | RBAC | Admin route protection |

### Test Scenarios

1. **Route Migration**:
   - Old route `/api/v1/tenants` → 404 Not Found
   - New route `/api/v1/admin/tenants` → 200 OK (with auth)
   - Non-admin user tries `/api/v1/admin/*` → 403 Forbidden

2. **Email Uniqueness**:
   - Same email, different tenants → Both succeed
   - Same email, same tenant → Second fails with 409
   - Case sensitivity: user@example.com vs User@EXAMPLE.com → Normalized

3. **Backward Compatibility Removal**:
   - Request with `?tenant_id=xxx` → Ignored (no error, no special handling)
   - No deprecation headers in response
   - Middleware startup without deprecation components → Success

4. **Database Migration**:
   - Upgrade from latest pre-release → V1.0 head succeeds
   - Constraint violation during migration → Transaction rolled back
   - Downgrade from V1.0 → Pre-release head succeeds (if needed)

---

## Implementation Plan

### Phase 1: Preparation & Audit (Day 1)
- ✅ Audit all deprecated code locations
- ✅ Create V1.0 cleanup checklist
- ✅ Set up staging environment for testing
- ✅ Backup production database schema

### Phase 2: Database Schema (Day 2)
- ✅ Create Alembic migration for email constraint
- ✅ Test migration on staging database
- ✅ Generate V1.0 schema documentation
- ✅ Create schema metadata table

### Phase 3: Route Structure (Days 3-4)
- ✅ Update all admin routers to use `/api/v1/admin` prefix
- ✅ Update app.py router includes
- ✅ Update all test files with new routes
- ✅ Regenerate OpenAPI spec

### Phase 4: Remove Deprecated Code (Day 5)
- ✅ Delete deprecation middleware files
- ✅ Remove deprecation middleware from app.py
- ✅ Clean up deprecation comments and TODOs
- ✅ Remove backward compatibility branches

### Phase 5: Testing & Validation (Day 6)
- ✅ Run full test suite
- ✅ Contract tests against new OpenAPI spec
- ✅ Performance benchmarks
- ✅ Security regression tests

### Phase 6: Documentation (Day 7)
- ✅ Write CHANGELOG-V1.0.md
- ✅ Write MIGRATION-TO-V1.0.md
- ✅ Update README and quickstart guide
- ✅ Publish OpenAPI spec

---

## Dependencies

- **Blocked By**: None (this is a cleanup feature)
- **Blocks**: V1.0 production release, public API documentation
- **Related**: 
  - Spec 010: Route Prefix Decision (decides on `/api/v1/admin/*`)
  - Spec 011: Email Uniqueness Clarification (decides on per-tenant)
  - Spec 004: Tenant Security Refactor (context switching implementation)

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking existing integrations | HIGH | MEDIUM | Publish migration guide early, version bump signals breaking change |
| Database migration failure | HIGH | LOW | Test thoroughly in staging, have rollback plan |
| Performance degradation from new constraints | MEDIUM | LOW | Index strategy validated, benchmarks run |
| Incomplete cleanup leaves technical debt | LOW | MEDIUM | Comprehensive checklist, code review |
| Documentation gaps confuse users | MEDIUM | MEDIUM | Peer review docs, early access program |

---

## Success Metrics

- ✅ **Zero** deprecation warnings in logs
- ✅ **Zero** legacy route access (404s)
- ✅ **100%** test pass rate after cleanup
- ✅ **<5% variance** in performance benchmarks
- ✅ **API spec validated** against OpenAPI 3.1.0
- ✅ **Migration guide tested** by at least 2 external reviewers

---

## Rollback Plan

If V1.0 must be rolled back:

1. **Database**: Run Alembic downgrade to previous version
2. **Code**: Revert Git tag to pre-V1.0 commit
3. **Config**: Restore deprecation middleware temporarily
4. **Communication**: Notify all API consumers of rollback

**Rollback Decision Criteria**:
- Critical bug discovered in production within 24 hours
- >10% error rate increase
- Data integrity issue detected

---

## Post-Release

### Monitoring

- Alert on 404s to old route patterns (indicates client not migrated)
- Monitor email constraint violations
- Track V1.0 adoption via health check version queries

### Support

- Dedicated Slack channel for V1.0 migration questions
- Weekly office hours for first month
- Migration success stories documented

---

## Appendix

### A. Deprecation Code Audit

**Files to Remove**:
- `src/adapters/api/deprecation.py`
- `src/adapters/api/middleware/deprecation_warning.py`

**Files to Update**:
- `src/adapters/api/app.py`: Remove middleware registration
- `src/adapters/api/routers/audit.py`: Remove migration notes
- `src/adapters/api/routers/policies.py`: Remove migration notes
- `src/adapters/api/routers/tenants/users.py`: Remove migration notes
- `src/adapters/persistence/db_config.py`: Remove deprecated params
- `src/adapters/media/storage.py`: Remove backward compat code

### B. Route Mapping Full List

(See FR-115 for comprehensive route mapping)

### C. Database Constraint SQL

(See FR-116 for SQL snippets)

---

**Version**: 1.0  
**Created**: 2025-01-20  
**Last Updated**: 2025-01-20  
**Status**: Ready for Planning Phase
