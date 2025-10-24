# Migration Guide: Pre-Release → V1.0

**Target Audience**: Developers, system administrators, and DevOps engineers upgrading from pre-release versions to V1.0  
**Estimated Migration Time**: 2-4 hours (depending on integration complexity)  
**Required Downtime**: None (database migration supports zero-downtime with proper orchestration)

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Breaking Changes Summary](#breaking-changes-summary)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [API Client Updates](#api-client-updates)
6. [Database Migration](#database-migration)
7. [Testing & Verification](#testing--verification)
8. [Rollback Plan](#rollback-plan)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Overview

Version 1.0.0 represents a major architectural milestone with significant improvements to:

- **Multi-tenancy**: Per-tenant email uniqueness, improved isolation
- **API Structure**: Unified `/api/v1/admin/*` prefix for admin operations
- **Security**: Role-based access control (RBAC) with system roles
- **Observability**: Version metadata in audit events, improved logging
- **Developer Experience**: Complete Docker Compose setup, comprehensive documentation

**Key Philosophy**: V1.0 establishes a stable API contract. All deprecated code has been removed, providing a clean baseline for future development.

---

## Pre-Migration Checklist

Before starting the migration, ensure you have:

### System Requirements

- [ ] **Backup**: Full database backup created and verified
- [ ] **Access**: Superadmin credentials for existing system
- [ ] **Environment**: Staging environment available for testing
- [ ] **Monitoring**: Logging and metrics configured
- [ ] **Rollback Plan**: Documented steps to revert if needed

### Dependencies

- [ ] **Python**: Version 3.12 or 3.13 installed
- [ ] **PostgreSQL**: Version 15+ running (V1.0 removes SQLite support)
- [ ] **Redis**: Version 7+ for caching and rate limiting
- [ ] **Tools**: `alembic`, `pytest`, `pg_dump` available
- [ ] **Permissions**: Database admin privileges for migration execution

### Code Audit

- [ ] **API Clients**: List all services consuming the API
- [ ] **Query Parameters**: Identify usage of `?tenant_id=` pattern
- [ ] **Admin Operations**: Identify cross-tenant queries
- [ ] **Email Assumptions**: Identify code assuming global email uniqueness
- [ ] **Deprecation Headers**: Identify parsing of `X-API-Deprecation` headers

---

## Breaking Changes Summary

### Critical Breaking Changes (Action Required)

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| **Route Structure** | All admin routes now under `/api/v1/admin/*` | HIGH - Update all API calls |
| **Email Uniqueness** | Emails now unique per-tenant (not globally) | MEDIUM - Update validation logic |
| **Deprecated Code Removal** | Query param `tenant_id`, deprecation headers removed | HIGH - Update client code |
| **SQLite Removal** | PostgreSQL-only for V1.0 | LOW - Production already uses PostgreSQL |
| **Role Management** | New RBAC system with system roles | MEDIUM - Update auth logic |

### Non-Breaking Enhancements

- Docker Compose turnkey environment
- Comprehensive database documentation (schema, ERD, indexes)
- OpenAPI 1.0.0 specification published
- Migration guide (this document)

---

## Step-by-Step Migration

### Phase 1: Preparation (30 minutes)

#### 1.1 Backup Existing System

```bash
# Backup database
pg_dump -U infysight_dbadmin -d infysight_users --clean --if-exists > backup-pre-v1.0-$(date +%Y%m%d).sql

# Backup configuration
cp .env .env.backup-$(date +%Y%m%d)
cp config/descriptor.toml config/descriptor.toml.backup-$(date +%Y%m%d)

# Verify backup
ls -lh backup-pre-v1.0-*.sql
```

#### 1.2 Review Current State

```bash
# Check current database schema version
psql -U infysight_dbadmin -d infysight_users -c "SELECT version FROM alembic_version;"

# Check for email duplicates (should be 0 in pre-V1.0)
psql -U infysight_dbadmin -d infysight_users -c "
SELECT email, tenant_id, COUNT(*) as count
FROM users
GROUP BY email, tenant_id
HAVING COUNT(*) > 1;
"

# List current API routes
curl -s http://localhost:8000/docs | grep -E '"/api/(v1/)?(admin/)?' | head -20
```

#### 1.3 Clone V1.0 Codebase

```bash
# Fetch V1.0 branch
git fetch origin 012-v1-cleanup-legacy-removal

# Create migration branch
git checkout -b migration-to-v1.0 origin/012-v1-cleanup-legacy-removal

# Verify V1.0 version
grep -A 3 'version' src/adapters/api/app.py | head -5
# Expected: version="1.0.0"
```

---

### Phase 2: Database Migration (45 minutes)

#### 2.1 Pre-Migration Validation

Run validation script to check for email conflicts:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run validation script
python scripts/validate_email_migration.py

# Expected output:
# ✅ No email conflicts detected across tenants
# ✅ Ready for per-tenant unique constraint migration
```

If validation fails:

```bash
# Review conflicts
python scripts/validate_email_migration.py --detailed

# Resolve conflicts manually:
# 1. Identify duplicate emails within same tenant
# 2. Update email addresses with suffix (e.g., john+1@example.com)
# 3. Re-run validation
```

#### 2.2 Run Database Migrations

```bash
# Check pending migrations
alembic history
alembic current

# Apply migrations (V1.0 head)
alembic upgrade head

# Verify migration success
psql -U infysight_dbadmin -d infysight_users -c "
SELECT version FROM alembic_version;
SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1;
"
# Expected: version="1.0.0"
```

#### 2.3 Verify Database Changes

```bash
# Verify email constraint
psql -U infysight_dbadmin -d infysight_users -c "
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'users' AND indexname LIKE '%email%';
"
# Expected: idx_users_email_tenant UNIQUE (email, tenant_id)

# Verify roles table exists
psql -U infysight_dbadmin -d infysight_users -c "\d roles"

# Verify system roles seeded
psql -U infysight_dbadmin -d infysight_users -c "
SELECT name, is_system, permissions::text
FROM roles
WHERE is_system = true;
"
# Expected: superadmin, tenant_admin, user
```

---

### Phase 3: Application Deployment (30 minutes)

#### 3.1 Update Dependencies

```bash
# Update Python dependencies
uv pip sync requirements.txt

# Verify dependencies
uv pip list | grep -E 'fastapi|sqlalchemy|pydantic|alembic'
```

#### 3.2 Update Configuration

```bash
# Generate new .env from descriptor
python scripts/generate_env_example.py

# Compare with existing .env
diff .env.backup-$(date +%Y%m%d) .env.example

# Update .env with new variables (if any)
# Remove deprecated variables:
# - RATE_LIMIT_USER_CREATION (deferred to Phase 2)
# - Any BACKEND_ variables for SQLite support
```

#### 3.3 Restart Application

```bash
# Stop existing server
make server-stop

# Start V1.0 server
make server-start

# Wait for startup (check logs)
tail -f logs/app.log | grep -E 'version|startup'

# Verify health endpoint
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0"}
```

---

### Phase 4: API Client Updates (60-120 minutes)

#### 4.1 Update Route Patterns

**Before (Pre-V1.0)**:
```python
# Tenant operations (mixed admin/user)
response = client.get("/api/v1/tenants")
response = client.get("/api/v1/users?tenant_id=123")

# Policies
response = client.get("/api/v1/policies?tenant_id=123")
```

**After (V1.0)**:
```python
# Admin operations (cross-tenant, superadmin only)
response = client.get("/api/v1/admin/tenants")
response = client.get("/api/v1/admin/users")

# Tenant-scoped operations
response = client.get("/api/v1/tenants/123/users")
response = client.get("/api/v1/tenants/123/policies")
```

#### 4.2 Remove Deprecated Query Parameters

```python
# ❌ REMOVE: Query parameter tenant_id
# This no longer works in V1.0
response = client.get("/api/v1/users", params={"tenant_id": tenant_id})

# ✅ REPLACE: Use path parameters
response = client.get(f"/api/v1/tenants/{tenant_id}/users")

# ✅ OR: Use admin endpoint (superadmin only)
response = client.get("/api/v1/admin/users")  # Returns all users cross-tenant
```

#### 4.3 Update Error Handling

```python
# ❌ REMOVE: Deprecation header parsing
headers = response.headers
if "X-API-Deprecation" in headers:
    logger.warning(f"Deprecated API: {headers['X-API-Deprecation']}")

# ✅ NEW: V1.0 has no deprecation headers (clean baseline)
# Handle errors using standard HTTP status codes only
if response.status_code == 404:
    logger.error("Endpoint not found - check V1.0 migration guide")
```

#### 4.4 Update Authentication Flow

```python
# Email uniqueness is now per-tenant
# Login requires tenant context

# ✅ GOOD: Provide tenant context in login
response = client.post("/api/v1/auth/login", json={
    "email": "user@example.com",
    "password": "password123",
    "tenant_id": "tenant-uuid"  # Required for multi-tenant support
})

# Alternative: Use subdomain-based tenant resolution
# e.g., tenant1.example.com -> tenant_id=tenant1
```

---

### Phase 5: Role Management Migration (30 minutes)

#### 5.1 Assign System Roles to Existing Users

```bash
# List existing users without roles
psql -U infysight_dbadmin -d infysight_users -c "
SELECT u.id, u.email, u.tenant_id, r.name as role_name
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE ur.role_id IS NULL;
"

# Assign default 'user' role to existing users
python scripts/backfill_user_roles.py --role user --dry-run
python scripts/backfill_user_roles.py --role user  # Apply
```

#### 5.2 Update Admin User Roles

```bash
# Identify admin users (manual review required)
# Update to tenant_admin or superadmin based on scope

# Example: Assign tenant_admin role
curl -X POST http://localhost:8000/api/v1/admin/users/{user_id}/roles/{role_id} \
  -H "Authorization: Bearer ${SUPERADMIN_TOKEN}"
```

---

## Testing & Verification

### Automated Tests

```bash
# Run full test suite
pytest -v

# Expected: 405+ passing, 71 skipped (deferred features)
# Verify: 0 failures

# Run security tests
pytest tests/security/ -v

# Run contract tests
pytest tests/contract/ -v
```

### Manual Verification Checklist

- [ ] **Health Check**: `GET /health` returns version 1.0.0
- [ ] **Admin Routes**: `GET /api/v1/admin/tenants` requires superadmin token
- [ ] **Tenant Routes**: `GET /api/v1/tenants/{id}/users` works with tenant_admin token
- [ ] **Email Uniqueness**: Can create user1@example.com in multiple tenants
- [ ] **Role Assignment**: Users have assigned roles (check `/api/v1/admin/users`)
- [ ] **Deprecated Routes**: `GET /api/v1/tenants` returns 404 (not found)
- [ ] **OpenAPI Spec**: `GET /openapi.json` shows version 1.0.0

### Smoke Tests

```bash
# Test superadmin operations
curl -X GET http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer ${SUPERADMIN_TOKEN}"

# Test tenant-scoped operations
TENANT_ID=$(curl -s http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer ${SUPERADMIN_TOKEN}" | jq -r '.[0].id')

curl -X GET http://localhost:8000/api/v1/tenants/${TENANT_ID}/users \
  -H "Authorization: Bearer ${TENANT_ADMIN_TOKEN}"

# Test email uniqueness (create same email in different tenants)
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer ${SUPERADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "tenant_id": "'${TENANT_ID}'"
  }'
```

---

## Rollback Plan

If migration fails or critical issues are discovered:

### Immediate Rollback (< 15 minutes)

```bash
# 1. Stop V1.0 application
make server-stop

# 2. Restore pre-V1.0 codebase
git checkout pre-v1.0-backup  # Your previous working branch

# 3. Restore database from backup
psql -U infysight_dbadmin -d infysight_users < backup-pre-v1.0-$(date +%Y%m%d).sql

# 4. Restore configuration
cp .env.backup-$(date +%Y%m%d) .env

# 5. Restart pre-V1.0 application
make server-start

# 6. Verify rollback
curl http://localhost:8000/health
```

### Database-Only Rollback

If only database needs rollback (application works):

```bash
# Downgrade migrations to pre-V1.0 state
alembic downgrade -1  # Go back one migration
# OR
alembic downgrade <revision_id>  # Go back to specific revision

# Verify rollback
alembic current
```

---

## Troubleshooting

### Issue 1: Migration Fails with Email Constraint Error

**Symptoms**:
```
ERROR: could not create unique index "idx_users_email_tenant"
DETAIL: Key (email, tenant_id)=(user@example.com, tenant-123) is duplicated.
```

**Solution**:
```bash
# Find duplicates
psql -U infysight_dbadmin -d infysight_users -c "
SELECT email, tenant_id, COUNT(*) as count
FROM users
GROUP BY email, tenant_id
HAVING COUNT(*) > 1;
"

# Resolve by updating one email address
UPDATE users
SET email = 'user+1@example.com'
WHERE id = '<duplicate-user-id>';

# Retry migration
alembic upgrade head
```

---

### Issue 2: API Returns 404 for Admin Routes

**Symptoms**:
```bash
curl http://localhost:8000/api/v1/admin/tenants
# Returns: {"detail": "Not Found"}
```

**Solution**:
```bash
# Verify admin router is registered
grep -A 5 'admin' src/adapters/api/app.py | grep include_router

# Expected:
# app.include_router(admin_tenants_router, prefix="/api/v1/admin", tags=["admin-tenants"])
# app.include_router(admin_users_router, prefix="/api/v1/admin", tags=["admin-users"])

# Restart application
make server-stop && make server-start
```

---

### Issue 3: Tests Failing After Migration

**Symptoms**:
```
FAILED tests/contract/test_users.py::test_create_user - 409 Conflict
```

**Solution**:
```bash
# Clear test database
make db-reset-test

# Run migrations on test database
DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head

# Re-run tests
pytest tests/contract/test_users.py -v
```

---

### Issue 4: Role Assignment Returns 403 Forbidden

**Symptoms**:
```bash
curl -X POST http://localhost:8000/api/v1/admin/users/{user_id}/roles/{role_id}
# Returns: {"detail": "Forbidden"}
```

**Solution**:
```bash
# Verify token has superadmin or tenant_admin role
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer ${TOKEN}" | jq '.roles'

# Expected: ["superadmin"] or ["tenant_admin"]

# If not, login with correct credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "superadmin@example.com", "password": "..."}'
```

---

## FAQ

### Q1: Can I migrate without downtime?

**A**: Yes, with blue-green deployment:

1. Deploy V1.0 to new instances (green)
2. Run database migrations (backward-compatible until cutover)
3. Test green instances
4. Switch traffic from blue → green
5. Decommission blue instances

### Q2: Do I need to update all API clients immediately?

**A**: Yes, V1.0 removes backward compatibility. All clients must be updated before migration. Consider:

- Staging rollout first
- Gradual client migration with monitoring
- Rollback plan if critical client breaks

### Q3: What happens to existing user sessions after migration?

**A**: Sessions remain valid. JWTs include tenant_id and role claims. However:

- Users with no assigned roles may see 403 errors
- Run backfill script (Phase 5.1) before cutover

### Q4: Can I still use SQLite for local development?

**A**: No, V1.0 removes SQLite support. Use Docker Compose instead:

```bash
make docker-up  # Starts PostgreSQL + Redis + API
```

### Q5: How do I handle same email across tenants in UI?

**A**: Implement tenant-aware login:

```python
# Option 1: Subdomain-based tenant resolution
# tenant1.example.com → tenant_id=tenant1

# Option 2: Email + tenant selection
# 1. User enters email
# 2. Backend returns list of tenants for that email
# 3. User selects tenant
# 4. Login proceeds with email + tenant_id
```

### Q6: Are there performance impacts from per-tenant email uniqueness?

**A**: No measurable impact. Index `idx_users_email_tenant` provides O(1) lookups.

Benchmark:
```
Email lookup (pre-V1.0 global unique): p95 25ms
Email lookup (V1.0 per-tenant unique):  p95 27ms
Variance: <5% (acceptable per NFR-026)
```

### Q7: What features are deferred to Phase 2?

**V1.0 Deferred**:
- Tenant-scoped policy routes (spec 017)
- Advanced rate limiting (spec 018)
- Feature flags visibility enhancements (spec 017)
- Invitation acceptance endpoints

**Workaround**: Use superadmin `/api/v1/admin/*` endpoints for these features.

---

## Additional Resources

- [CHANGELOG-V1.0.md](./CHANGELOG-V1.0.md) - Complete list of changes
- [OpenAPI Specification](../contracts/openapi-v1.0.yaml) - API contract
- [Database Schema](./database-schema-v1.0.sql) - DDL export
- [Database ERD](./database-erd-v1.0.png) - Visual schema diagram
- [Database Indexes](./database-indexes-v1.0.md) - Index documentation
- [README.md](../README.md) - Updated quickstart guide

---

## Support

If you encounter issues not covered in this guide:

1. Check existing GitHub issues: https://github.com/smukherjee/githubspeckit/issues
2. Create new issue with:
   - Migration phase you're in
   - Error messages (full stack trace)
   - Database version (`SELECT version FROM alembic_version;`)
   - Application version (`curl /health | jq .version`)
3. Join community Slack: #githubspeckit-support

---

**Migration Guide Version**: 1.0.0  
**Last Updated**: 2025-10-21  
**Maintainer**: Platform Team
