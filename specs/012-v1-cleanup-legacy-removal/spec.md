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
- Q: Is the read-only `/api/v1/admin/roles` GET endpoint intentional, or should V1.0 include full CRUD operations for role management? → A: Hybrid - System roles (superadmin, tenant_admin, user) are pre-seeded and read-only, but allow custom role creation at hierarchy levels below tenant_admin
- Q: How should role assignment work in V1.0? → A: Hybrid - Support both user creation/update with role_id field AND dedicated assignment endpoints (POST/DELETE /api/v1/admin/users/{user_id}/roles/{role_id}) for flexibility
- Q: Does V1.0 support hierarchical role inheritance? → A: Permission-based - No inheritance, each role explicitly defines its permission set (most flexible, clearest security model)
- Q: How are system roles created and managed? → A: Script seeded via scripts/seed_infysight.py for initial setup, then automatically seeded (superadmin, tenant_admin, user) on each new tenant creation

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
- ✅ Public routes (auth, health) remain at `/api/v1/auth/*`, `/health`
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
| `/health` | GET | Public | None (unauthenticated) | N/A |
| `/api/v1/config` | GET | Public | None (unauthenticated) | N/A |
| `/api/v1/embed/exchange` | POST | Public | None (unauthenticated) | N/A |
| `/metrics` | GET | Public | None (monitoring) | N/A |
| `/api/v1/admin/tenants` | GET, POST | Admin | superadmin | Cross-tenant (superadmin sees all) |
| `/api/v1/admin/tenants/{id}` | GET, PUT, DELETE | Admin | superadmin, tenant_admin (own tenant) | Tenant-filtered for tenant_admin |
| `/api/v1/admin/users` | GET, POST | Admin | superadmin, tenant_admin | Cross-tenant for superadmin, tenant-scoped for tenant_admin |
| `/api/v1/admin/users/{id}` | GET, PUT, DELETE | Admin | superadmin, tenant_admin (same tenant) | Tenant-filtered |
| `/api/v1/admin/policies` | GET, POST | Admin | superadmin, tenant_admin | Tenant-scoped |
| `/api/v1/admin/policies/{id}` | GET, PUT, DELETE | Admin | superadmin, tenant_admin (same tenant) | Tenant-filtered |
| `/api/v1/admin/roles` | GET | Admin | superadmin, tenant_admin | System roles (read-only: superadmin, tenant_admin, user) |
| `/api/v1/admin/roles` | POST | Admin | tenant_admin, superadmin | Create custom roles below tenant_admin hierarchy |
| `/api/v1/admin/roles/{id}` | GET, PUT, DELETE | Admin | tenant_admin (own tenant), superadmin | Custom role management (system roles immutable) |
| `/api/v1/admin/users/{user_id}/roles/{role_id}` | POST | Admin | tenant_admin (same tenant), superadmin | Assign role to user (dedicated endpoint) |
| `/api/v1/admin/users/{user_id}/roles/{role_id}` | DELETE | Admin | tenant_admin (same tenant), superadmin | Revoke role from user |
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

4. **Verify**: Run health check at `/health` confirms V1.0
```

### FR-122: Role Management & Hierarchy Implementation

**User Story**: As a platform administrator, I want a complete role management system with system roles (read-only) and custom role creation capabilities, so I can implement flexible RBAC across tenants.

**Acceptance Criteria**:
- ✅ **Roles table** created with schema:
  - `id` (UUID, PK)
  - `name` (VARCHAR, NOT NULL)
  - `tenant_id` (UUID, FK to tenants, NULL for system roles)
  - `is_system` (BOOLEAN, default FALSE)
  - `permissions` (JSONB, array of permission strings)
  - `created_at`, `updated_at`, `created_by`, `updated_by` (audit fields)
  - **Constraint**: `UNIQUE(name, tenant_id)` (tenant-scoped role names)
- ✅ **System roles pre-seeded** via migration/seed script:
  - `superadmin` (tenant_id=NULL, is_system=TRUE): Cross-tenant access, all permissions
  - `tenant_admin` (tenant_id=NULL, is_system=TRUE): Tenant-scoped admin, manage users/roles/policies within tenant
  - `user` (tenant_id=NULL, is_system=TRUE): Basic authenticated user, read-only access to own resources
- ✅ **Role hierarchy enforced**:
  - Permission-based (no inheritance): Each role explicitly defines its permission set
  - Custom roles can only be created at hierarchy levels BELOW tenant_admin (no privilege escalation)
  - System roles (`is_system=TRUE`) are immutable (cannot be modified or deleted)
- ✅ **Role assignment**:
  - `user_roles` junction table: `user_id`, `role_id`, `assigned_at`, `assigned_by`
  - Users have exactly ONE role per tenant (enforced at application layer)
  - Support both user creation with `role_id` AND dedicated assignment endpoints
- ✅ **API endpoints** (all under `/api/v1/admin/roles`):
  - `GET /api/v1/admin/roles` - List all roles (system + tenant custom roles)
  - `POST /api/v1/admin/roles` - Create custom role (tenant_admin only, below hierarchy)
  - `GET /api/v1/admin/roles/{id}` - Get role details
  - `PUT /api/v1/admin/roles/{id}` - Update custom role (system roles rejected)
  - `DELETE /api/v1/admin/roles/{id}` - Delete custom role (system roles rejected)
  - `POST /api/v1/admin/users/{user_id}/roles/{role_id}` - Assign role to user
  - `DELETE /api/v1/admin/users/{user_id}/roles/{role_id}` - Revoke role from user
- ✅ **Schema documentation**:
  - Roles table DDL in `docs/database-schema-v1.0.sql`
  - User-role relationship documented in ERD (`docs/database-erd-v1.0.png`)
  - Permission model documented (list of available permissions)
- ✅ **RBAC enforcement**:
  - System roles: Only superadmin can view/assign system roles
  - Custom roles: tenant_admin can create/manage within their tenant
  - Tenant isolation: Custom roles scoped to `tenant_id`, not visible to other tenants

**Database Schema**:
```sql
-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,  -- NULL for system roles
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Array of permission strings
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT unique_role_name_per_tenant UNIQUE(name, tenant_id)
);

-- User-Role junction table
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

-- Seed system roles (via migration or seed script)
INSERT INTO roles (id, name, tenant_id, is_system, permissions, description) VALUES
(gen_random_uuid(), 'superadmin', NULL, TRUE, 
 '["*"]'::jsonb,  -- All permissions
 'System administrator with cross-tenant access'),
(gen_random_uuid(), 'tenant_admin', NULL, TRUE,
 '["tenant:*", "users:*", "roles:create", "roles:update", "roles:delete", "policies:*"]'::jsonb,
 'Tenant administrator with full control within tenant scope'),
(gen_random_uuid(), 'user', NULL, TRUE,
 '["users:read_own", "profile:update_own"]'::jsonb,
 'Standard authenticated user with read-only access to own resources');

-- Indexes
CREATE INDEX idx_roles_tenant ON roles(tenant_id);
CREATE INDEX idx_roles_system ON roles(is_system) WHERE is_system = TRUE;
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

**Permission Model** (initial set, extensible):
- `*` - All permissions (superadmin only)
- `tenant:read`, `tenant:update`, `tenant:delete` - Tenant management
- `users:create`, `users:read`, `users:update`, `users:delete`, `users:read_own` - User management
- `roles:create`, `roles:read`, `roles:update`, `roles:delete` - Role management
- `policies:create`, `policies:read`, `policies:update`, `policies:delete` - Policy management
- `profile:update_own` - User profile updates

**Testing**:
- Test: Create custom role as tenant_admin → success
- Test: Create custom role with superadmin permissions → 403 Forbidden (hierarchy violation)
- Test: Modify system role → 400 Bad Request (immutable)
- Test: Assign role across tenants → 403 Forbidden (tenant isolation)
- Test: User with custom role can perform permitted actions
- Test: System role seeding is idempotent (safe to run multiple times)

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

## Scope Boundaries

### ✅ Included in V1.0 (This Phase)

**Core Cleanup**:
- Remove all deprecated middleware and backward compatibility code
- Unified route prefix structure (`/api/v1/admin/*`)
- Per-tenant email uniqueness enforcement
- Database schema V1.0 finalization with full documentation

**Role Management** (FR-122):
- Complete role management system with CRUD operations
- System roles (superadmin, tenant_admin, user) pre-seeded and immutable
- Custom role creation for tenant admins
- Role assignment endpoints
- Permission-based hierarchy (no inheritance)
- Roles table schema documentation in ERD

**Developer Experience**:
- Complete Makefile automation (`make bootstrap`, `make dev`, `make test`)
- Docker Compose turnkey environment (PostgreSQL, Redis, pgAdmin, API)
- Comprehensive documentation (README, CONTRIBUTING, migration guide)
- Database ERD generation via SchemaSpy

**Observability**:
- Basic metrics endpoint (`/metrics` - Prometheus-compatible)
- Log export endpoint (`/api/v1/logs/export` - JSON forensics)
- Structured logging with redaction

### 🔄 Deferred to Phase 2 (Future Specs)

**Policy Engine Enhancements** (Spec 017 - Planned):
- Advanced policy evaluation engine (tri-state: ALLOW/DENY/ABSTAIN)
- Policy inheritance and composition
- Policy audit trail and versioning
- Dynamic policy updates without restart

**Advanced Rate Limiting** (Spec 018 - Planned):
- Tiered rate limiting (per-tenant, per-user, per-endpoint)
- Distributed rate limiting across multiple API instances
- Rate limit bypass tokens for integrations
- Configurable rate limit strategies (sliding window, token bucket)

**Feature Flags System** (Spec 018 - Planned):
- Feature flag CRUD operations
- Tenant-specific feature enablement
- A/B testing support
- Feature flag analytics and usage tracking

**Advanced Observability** (Spec 019 - Planned):
- Grafana Loki integration for real-time log dashboards
- Distributed tracing with Jaeger/Zipkin
- Custom metrics dashboards
- Alerting rules and notification channels

**Multi-Database Support** (Future):
- MySQL/MariaDB adapter
- Database migration tooling for cross-platform moves

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
- ✅ Create roles table migration with system role seeding
- ✅ Create user_roles junction table migration
- ✅ Test migrations on staging database
- ✅ Generate V1.0 schema documentation (including roles ERD)
- ✅ Create schema metadata table

### Phase 3: Role Management Implementation (Days 3-4)

- ✅ Implement roles domain model and repository
- ✅ Create role CRUD API endpoints (`/api/v1/admin/roles/*`)
- ✅ Implement role assignment endpoints (`/api/v1/admin/users/{user_id}/roles/{role_id}`)
- ✅ Add permission-based authorization middleware
- ✅ Implement role hierarchy validation (prevent privilege escalation)
- ✅ Seed system roles (superadmin, tenant_admin, user)
- ✅ Add role management tests (unit + integration)
- ✅ Document permission model

### Phase 4: Route Structure Migration (Day 5)

- ✅ Update all admin routers to use `/api/v1/admin` prefix
- ✅ Update app.py router includes
- ✅ Update all test files with new routes
- ✅ Regenerate OpenAPI spec

### Phase 5: Remove Deprecated Code (Day 6)

- ✅ Delete deprecation middleware files
- ✅ Remove deprecation middleware from app.py
- ✅ Clean up deprecation comments and TODOs
- ✅ Remove backward compatibility branches

### Phase 6: Testing & Validation (Day 7)

- ✅ Run full test suite
- ✅ Contract tests against new OpenAPI spec
- ✅ Performance benchmarks
- ✅ Security regression tests (RBAC with roles)

### Phase 7: Documentation (Day 8)

- ✅ Write CHANGELOG-V1.0.md
- ✅ Write MIGRATION-TO-V1.0.md
- ✅ Update README and quickstart guide
- ✅ Publish OpenAPI spec
- ✅ Document role management and permission model
- ✅ Create SchemaSpy ERD with roles relationships

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
