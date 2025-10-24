# Quickstart: V1.0 Release Validation & Migration Testing

**Feature**: 012-v1-cleanup-legacy-removal  
**Purpose**: Integration test scenarios and manual validation checklist for V1.0 release  
**Date**: 2025-10-20

---

## Prerequisites

Before running these scenarios:

- ✅ Python 3.13+ installed
- ✅ PostgreSQL running (native or Docker)
- ✅ Redis running (optional for basic tests, required for rate limiting validation)
- ✅ V1.0 codebase deployed (branch: `012-v1-cleanup-legacy-removal`)
- ✅ Database migrations applied (`alembic upgrade head`)
- ✅ Seed data loaded (`python scripts/seed_infysight.py`)

---

## Setup

### Option A: Native Environment

```bash
# Clone and bootstrap
git clone https://github.com/sujoymukherjee-corp/githubspeckit.git
cd githubspeckit
git checkout 012-v1-cleanup-legacy-removal

# Bootstrap complete environment
make bootstrap

# Verify health
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}
```

### Option B: Docker Compose

```bash
# Clone and start services
git clone https://github.com/sujoymukherjee-corp/githubspeckit.git
cd githubspeckit
git checkout 012-v1-cleanup-legacy-removal

# Start all 4 services (PostgreSQL, Redis, pgAdmin, API)
make docker-up

# Verify health
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}
```

---

## Test Scenarios

### TS-001: Health Check Returns V1.0 Version

**Given**: V1.0 server running  
**When**: Request health endpoint

```bash
curl http://localhost:8000/health
```

**Then**: Response confirms V1.0

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

**Status**: ⏹️ NOT STARTED

---

### TS-002: Deprecated Routes Removed from API

**Given**: V1.0 server running (deprecated routes removed)  
**When**: Verify deprecated routes not registered in OpenAPI schema

```bash
# Check OpenAPI schema for routes containing 'tenants' or 'users'
curl -s http://localhost:8000/openapi.json | \
  jq -r '.paths | keys[]' | grep -E '/(tenants|users)'
```

**Then**: Deprecated routes `/api/v1/tenants` and `/api/v1/users` are NOT in schema

**Expected Output** (should NOT contain deprecated routes):
```
/api/v1/admin/tenants
/api/v1/admin/users
/api/v1/admin/users/{user_id}/roles/{role_id}
/api/v1/tenants/{tenant_id}/audit
/api/v1/tenants/{tenant_id}/users
/api/v1/users/{user_id}/profile
/api/v1/users/{user_id}/profile/photo
```

**Security Note**: Accessing removed routes (e.g., `curl http://localhost:8000/api/v1/tenants`) returns 401 Unauthorized (not 404) due to `TenantContextMiddleware` running before route matching. This is **more secure** as it doesn't leak information about which endpoints exist to unauthenticated users.

**Status**: ⏹️ NOT STARTED

---

### TS-003: Admin Routes Require Authentication

**Given**: V1.0 server with RBAC enforcement  
**When**: Request admin routes without authentication

```bash
curl -X GET http://localhost:8000/api/v1/admin/tenants
```

**Then**: Response 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

**Status**: ⏹️ NOT STARTED

---

### TS-004: Successful Admin Login Returns JWT

**Given**: Seeded superadmin user (`infysightsa@infysight.com`)  
**When**: POST credentials to login endpoint

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=infysightsa@infysight.com&password=infysightsa123"
```

**Then**: Response 200 with JWT token

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Status**: ⏹️ NOT STARTED

**Capture Token**:
```bash
export TOKEN="<paste_access_token_here>"
```

---

### TS-005: Admin Routes Accessible With Valid Token

**Given**: Valid JWT token from TS-004  
**When**: Request admin route with `Authorization: Bearer` header

```bash
curl -X GET http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN"
```

**Then**: Response 200 with tenant list

```json
{
  "items": [
    {
      "id": "<tenant-uuid>",
      "name": "infysight",
      "slug": "infysight",
      "created_at": "2025-10-20T00:00:00Z"
    }
  ],
  "total": 1
}
```

**Status**: ⏹️ NOT STARTED

---

### TS-006: Email Uniqueness Enforced Per-Tenant (Same Tenant Conflict)

**Given**: Authenticated as superadmin  
**When**: Attempt to create duplicate email in same tenant

```bash
# Create first user
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "Test123!",
    "tenant_id": "<infysight-tenant-id>",
    "role": "user"
  }'
# Expected: 201 Created

# Attempt duplicate in same tenant
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type": application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "Test123!",
    "tenant_id": "<infysight-tenant-id>",
    "role": "user"
  }'
```

**Then**: Second request returns 409 Conflict

```json
{
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "Email 'testuser@example.com' is already registered in this tenant",
    "trace_id": "abc-123-def"
  }
}
```

**Status**: ⏹️ NOT STARTED

---

### TS-007: Email Uniqueness Allows Same Email Across Different Tenants

**Given**: Authenticated as superadmin with two tenants (infysight + test-tenant-b)  
**When**: Create same email in different tenants

```bash
# Create user in tenant A
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "shared@example.com",
    "password": "Test123!",
    "tenant_id": "<tenant-a-id>",
    "role": "user"
  }'
# Expected: 201 Created

# Create same email in tenant B
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "shared@example.com",
    "password": "Test123!",
    "tenant_id": "<tenant-b-id>",
    "role": "user"
  }'
# Expected: 201 Created (allowed: different tenant)
```

**Then**: Both creations succeed with 201 status

**Status**: ⏹️ NOT STARTED

---

### TS-008: OpenAPI Spec Version Is 1.0.0

**Given**: V1.0 server running  
**When**: Request OpenAPI spec

```bash
curl http://localhost:8000/openapi.json | jq '.info.version'
```

**Then**: Version is "1.0.0"

```bash
# Output:
"1.0.0"
```

**Status**: ⏹️ NOT STARTED

---

### TS-009: No Deprecation Headers In Responses

**Given**: V1.0 server (deprecation middleware removed)  
**When**: Request any endpoint

```bash
curl -i http://localhost:8000/v1/health
```

**Then**: Response headers DO NOT contain:
- ❌ `X-API-Deprecation`
- ❌ `Sunset`
- ❌ `X-Deprecation-Notice`

**Status**: ⏹️ NOT STARTED

---

### TS-010: Rate Limiting Applied To User Creation

**Given**: V1.0 server with `RATE_LIMIT_USER_CREATION=5` (configured for testing)  
**When**: Attempt 6 POST /api/v1/admin/users from same IP within 1 hour

```bash
# Set rate limit to 5 for testing (in .env or config)
export RATE_LIMIT_USER_CREATION=5

# Restart API server
make server-stop && make server-start

# Attempt 6 user creations with unique emails
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/admin/users \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"ratelimit$i@example.com\",
      \"password\": \"Test123!\",
      \"tenant_id\": \"<tenant-id>\",
      \"role\": \"user\"
    }"
  echo "\n---"
done
```

**Then**: 6th request returns 429 Too Many Requests

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "retry_after": 3600
    }
  }
}
```

**Headers**: `Retry-After: 3600` (seconds)

**Status**: ⏹️ NOT STARTED

---

### TS-011: Database Schema Version Tracked

**Given**: V1.0 migrations applied  
**When**: Query schema_version table

```sql
-- Connect to PostgreSQL
psql -U postgres -d infysight_users

-- Query schema version
SELECT version, description, applied_at 
FROM schema_version 
ORDER BY applied_at DESC 
LIMIT 1;
```

**Then**: V1.0 version marker exists

```
 version |        description         |        applied_at
---------+---------------------------+---------------------------
 1.0.0   | V1.0 release: Per-tenant  | 2025-10-20 10:00:00+00
         | email uniqueness          |
```

**Status**: ⏹️ NOT STARTED

---

### TS-012: SchemaSpy Documentation Generated

**Given**: SchemaSpy tool configured  
**When**: Run documentation generation

```bash
make docs-db
```

**Then**: HTML documentation and ERD generated

**Verify**:
```bash
ls -la docs/schemaspy/
# Expected:
# - index.html
# - tables/
# - diagrams/ (contains ERD PNGs)

# Serve docs locally
make docs-db-serve
# Access: http://localhost:8080
```

**Status**: ⏹️ NOT STARTED

---

### TS-013: Docker Compose Full Stack Startup

**Given**: Clean environment (no running containers)  
**When**: Start all services via Docker Compose

```bash
make docker-up
```

**Then**: All 4 services healthy

**Verify**:
```bash
docker-compose ps
# Expected:
# NAME                 STATUS              PORTS
# postgres             Up (healthy)        0.0.0.0:5432->5432/tcp
# redis                Up                  0.0.0.0:6379->6379/tcp
# pgadmin              Up                  0.0.0.0:5050->80/tcp
# api                  Up                  0.0.0.0:8000->8000/tcp

# Test API health
curl http://localhost:8000/v1/health
# Expected: {"status":"healthy","version":"1.0.0"}

# Test pgAdmin (web UI)
open http://localhost:5050
# Login: admin@example.com / admin
```

**Status**: ⏹️ NOT STARTED

---

## Migration Validation

### MV-001: Migration Upgrade Succeeds

**Given**: Pre-V1.0 database state  
**When**: Run Alembic upgrade

```bash
alembic upgrade head
```

**Then**: No errors, composite index created

**Verify**:
```sql
-- Check index exists
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname = 'idx_users_email_tenant';

-- Expected output:
--        indexname        |                    indexdef
-- ------------------------+-------------------------------------------------------
--  idx_users_email_tenant | CREATE UNIQUE INDEX idx_users_email_tenant ON users
--                         | USING btree (email, tenant_id)
```

**Status**: ⏹️ NOT STARTED

---

### MV-002: Migration Downgrade Works (If No Conflicts)

**Given**: V1.0 database with no duplicate emails across tenants  
**When**: Run Alembic downgrade

```bash
alembic downgrade -1
```

**Then**: Global unique constraint restored

**Verify**:
```sql
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'users'::regclass 
AND conname = 'users_email_key';

-- Expected output:
--    conname     | contype
-- ---------------+---------
--  users_email_key |  u       (unique constraint)
```

**WARNING**: Downgrade will fail if duplicate emails exist across tenants. This is expected and documented in MIGRATION-TO-V1.0.md.

**Status**: ⏹️ NOT STARTED

---

## Performance Validation

### PV-001: Email Lookup Performance Within Tolerance

**Given**: V1.0 database with 10,000 users across 100 tenants  
**When**: Run performance benchmark

```bash
pytest tests/performance/test_user_lookup_benchmark.py -v
```

**Then**: p95 latency <30ms (target), <50ms (acceptable)

**Metrics**:
- Email lookup by tenant: p50 <15ms, p95 <30ms, p99 <50ms
- User creation with uniqueness check: p50 <50ms, p95 <100ms

**Status**: ⏹️ NOT STARTED

---

### PV-002: Overall API Performance Maintained

**Given**: V1.0 deployment vs pre-V1.0 baseline  
**When**: Run load test suite

```bash
pytest tests/performance/ -v --benchmark-only
```

**Then**: <5% variance in p95 latency across all endpoints (per NFR-026)

**Status**: ⏹️ NOT STARTED

---

## Documentation Validation

### DV-001: README Quick Start Works End-to-End

**Given**: Fresh checkout on clean machine  
**When**: Follow README.md quick start instructions  
**Then**: API health check succeeds in <5 minutes

**Status**: ⏹️ NOT STARTED

---

### DV-002: CONTRIBUTING.md References V1.0 Practices

**Given**: CONTRIBUTING.md created/updated  
**When**: Review for V1.0-specific guidance  
**Then**: Includes:
- ✅ Branch naming convention (`012-v1-cleanup-legacy-removal`)
- ✅ Test requirements (coverage ≥85%)
- ✅ PR review process
- ✅ Code quality gates (ruff, mypy)

**Status**: ⏹️ NOT STARTED

---

### DV-003: Migration Guide Completeness

**Given**: MIGRATION-TO-V1.0.md created  
**When**: Review for completeness  
**Then**: Includes:
- ✅ Breaking changes list
- ✅ Step-by-step migration instructions
- ✅ Rollback procedure
- ✅ API client update examples
- ✅ Expected downtime/impact

**Status**: ⏹️ NOT STARTED

---

## Security Validation

### SV-001: RBAC Enforcement On Admin Routes

**Given**: Non-admin user token  
**When**: Attempt to access `/api/v1/admin/*` routes  
**Then**: Response 403 Forbidden (not 401)

**Status**: ⏹️ NOT STARTED

---

### SV-002: Tenant Isolation Maintained

**Given**: User in tenant A with admin token  
**When**: Attempt to access tenant B resources  
**Then**: Response 403 or filtered results (no cross-tenant data leakage)

**Status**: ⏹️ NOT STARTED

---

## Completion Checklist

### Functional Requirements

- [ ] TS-001: Health check version
- [ ] TS-002: Deprecated routes 404
- [ ] TS-003: Admin auth required
- [ ] TS-004: JWT login works
- [ ] TS-005: Admin routes accessible
- [ ] TS-006: Email uniqueness same tenant
- [ ] TS-007: Email uniqueness cross-tenant
- [ ] TS-008: OpenAPI version
- [ ] TS-009: No deprecation headers
- [ ] TS-010: Rate limiting enforced
- [ ] TS-011: Schema version tracked
- [ ] TS-012: SchemaSpy docs generated
- [ ] TS-013: Docker Compose startup

### Migration

- [ ] MV-001: Upgrade succeeds
- [ ] MV-002: Downgrade works (conditional)

### Performance

- [ ] PV-001: Email lookup <30ms p95
- [ ] PV-002: <5% variance overall

### Documentation

- [ ] DV-001: README quick start <5 min
- [ ] DV-002: CONTRIBUTING.md complete
- [ ] DV-003: MIGRATION-TO-V1.0.md complete

### Security

- [ ] SV-001: RBAC admin enforcement
- [ ] SV-002: Tenant isolation

**Total**: 22 scenarios

**Status**: 0/22 completed (⏹️ NOT STARTED)

---

## Notes

- Replace `<tenant-id>`, `<tenant-a-id>`, `<tenant-b-id>` with actual UUIDs from your seeded data
- Replace `$TOKEN` with actual JWT from TS-004 login response
- All `curl` commands assume `http://localhost:8000` (adjust for deployed environments)
- Rate limiting tests require lowering `RATE_LIMIT_USER_CREATION` config for easier testing

---

**Version**: 1.0  
**Status**: Ready for execution  
**Next Step**: Run scenarios sequentially, mark status as completed (✅) or failed (❌)
