# Quickstart: Tenant Context Security Refactor

**Feature**: 004-tenant-security-refactor  
**Date**: 2025-10-19  
**Purpose**: End-to-end test scenarios validating secure tenant context implementation

## Prerequisites

```bash
# Activate Python environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
make server-start
```

## Test Scenario 1: JWT-Based Tenant Context (Standard User)

**Goal**: Verify standard users can only access their own tenant's resources.

### Step 1: Login as Standard User

```bash
# Login to get JWT
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@acme-corp.com", "password": "password123"}'

# Response includes JWT with tenant_id claim
{
  "access_token": "eyJhbG...",  # JWT contains: {"tenant_id": "acme-corp-uuid", "sub": "user-uuid", "roles": ["user"]}
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Step 2: Access Own Tenant Resources (Success)

```bash
# List users in own tenant (implicit tenant from JWT)
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer eyJhbG..."

# Expected: 200 OK
# Returns users filtered by JWT tenant_id
```

### Step 3: Attempt Cross-Tenant Access (Denied)

```bash
# Try to access another tenant's users via path parameter
curl -X GET http://localhost:8000/api/v1/tenants/victim-corp-uuid/users \
  -H "Authorization: Bearer eyJhbG..."

# Expected: 403 Forbidden
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Access denied: Cannot access resources in tenant 'victim-corp-uuid'",
    "details": {
      "user_tenant_id": "acme-corp-uuid",
      "requested_tenant_id": "victim-corp-uuid",
      "policy_rule": "cross_tenant_isolation"
    }
  },
  "trace_id": "req-123e4567"
}
```

**Validation**:

- ✅ Standard user can access own tenant
- ✅ Standard user blocked from cross-tenant access
- ✅ Authorization decision logged in audit trail

---

## Test Scenario 2: Superadmin Cross-Tenant Access

**Goal**: Verify superadmin can access any tenant's resources.

### Step 1: Login as Superadmin

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@platform.com", "password": "admin-secret"}'

# Response JWT contains: {"tenant_id": "platform-uuid", "sub": "admin-uuid", "roles": ["superadmin"]}
```

### Step 2: Access Multiple Tenants (Success)

```bash
# Access Tenant A
curl -X GET http://localhost:8000/api/v1/tenants/acme-corp-uuid/users \
  -H "Authorization: Bearer <superadmin-jwt>"

# Expected: 200 OK (returns Acme Corp users)

# Access Tenant B
curl -X GET http://localhost:8000/api/v1/tenants/victim-corp-uuid/users \
  -H "Authorization: Bearer <superadmin-jwt>"

# Expected: 200 OK (returns Victim Corp users)
```

**Validation**:

- ✅ Superadmin can access any tenant
- ✅ Cross-tenant access logged with `auth.cross_tenant.allowed` event
- ✅ Policy rule `superadmin_global_access` applied

---

## Test Scenario 3: Superadmin Tenant Switching (Session-Based)

**Goal**: Verify superadmin can switch active tenant for UI workflows.

### Step 1: Switch to Target Tenant

```bash
curl -X POST http://localhost:8000/api/v1/admin/context/tenant \
  -H "Authorization: Bearer <superadmin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "acme-corp-uuid"}'

# Expected: 200 OK
{
  "active_tenant_id": "acme-corp-uuid",
  "tenant_name": "Acme Corp",
  "switched_at": "2025-10-19T12:34:56Z"
}
```

### Step 2: Subsequent Requests Use Session Tenant

```bash
# List users (no path parameter needed)
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <superadmin-jwt>" \
  -b "session=<session-cookie>"

# Expected: 200 OK
# Returns users from session tenant (acme-corp-uuid), not JWT tenant (platform-uuid)
```

### Step 3: Logout Clears Session

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <superadmin-jwt>"

# Next request without session uses JWT tenant again
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <superadmin-jwt>"

# Expected: Returns users from platform-uuid (JWT tenant)
```

**Validation**:

- ✅ Tenant switch persists in session
- ✅ Session tenant overrides JWT tenant (superadmin only)
- ✅ Logout clears session tenant
- ✅ Audit log includes `auth.tenant_switch` event

---

## Test Scenario 4: Backward Compatibility (Deprecation Period)

**Goal**: Verify query parameter `?tenant_id=` still works with deprecation warnings.

### Step 1: Use Deprecated Query Parameter

```bash
curl -X GET "http://localhost:8000/api/v1/users?tenant_id=acme-corp-uuid" \
  -H "Authorization: Bearer <jwt>"

# Expected: 200 OK (query param ignored, JWT tenant_id used)
# Response headers:
#   Deprecation: true
#   Sunset: 2025-11-19T00:00:00Z
#   Link: <https://docs.githubspeckit.com/migration/tenant-security>; rel="deprecation"
```

### Step 2: Check Logs for Deprecation Warning

```bash
# Server logs should contain:
# WARN: Deprecated query parameter ?tenant_id= used
#       endpoint=/api/v1/users user_id=user-uuid client_ip=127.0.0.1
```

### Step 3: After Sunset Date (2025-11-19)

```bash
curl -X GET "http://localhost:8000/api/v1/users?tenant_id=acme-corp-uuid" \
  -H "Authorization: Bearer <jwt>"

# Expected: 400 Bad Request
{
  "error": {
    "code": "DEPRECATED_PARAMETER",
    "message": "Query parameter '?tenant_id=' is no longer supported",
    "details": {
      "sunset_date": "2025-11-19T00:00:00Z",
      "migration_guide": "https://docs.githubspeckit.com/migration/tenant-security"
    }
  }
}
```

**Validation**:

- ✅ Deprecated parameter works during grace period
- ✅ Deprecation headers present in responses
- ✅ Warning logged for monitoring
- ✅ Hard error after sunset date

---

## Test Scenario 5: Authorization Middleware Enforcement

**Goal**: Verify all routes pass through authorization middleware.

### Step 1: Standard User Attempts Admin Route

```bash
curl -X GET http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer <user-jwt>"

# Expected: 403 Forbidden
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Admin role required for this endpoint",
    "details": {
      "user_roles": ["user"],
      "required_roles": ["superadmin", "tenant_admin"],
      "policy_rule": "admin_role_required"
    }
  }
}
```

### Step 2: Tenant Admin Accesses Own Tenant Admin Routes

```bash
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer <tenant-admin-jwt>"

# Expected: 200 OK
# Returns users from tenant admin's tenant only (JWT tenant_id)
```

### Step 3: Tenant Admin Attempts Cross-Tenant Admin Route

```bash
curl -X GET http://localhost:8000/api/v1/tenants/other-tenant-uuid/users \
  -H "Authorization: Bearer <tenant-admin-jwt>"

# Expected: 403 Forbidden
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Access denied: Cannot access resources in tenant 'other-tenant-uuid'",
    "details": {
      "policy_rule": "cross_tenant_isolation"
    }
  }
}
```

**Validation**:

- ✅ Non-admin users blocked from admin routes
- ✅ Tenant admins scoped to own tenant
- ✅ Authorization logged with policy rule applied

---

## Test Scenario 6: Performance Validation

**Goal**: Verify middleware overhead meets performance budgets.

### Step 1: Baseline Request (No Middleware)

```bash
# Directly call repository method (benchmark baseline)
pytest tests/performance/test_baseline_latency.py

# Expected: ~50ms p95 (database query time only)
```

### Step 2: Request with Full Middleware Stack

```bash
# End-to-end API request through middleware
pytest tests/performance/test_middleware_overhead.py

# Expected: ~55ms p95 (50ms DB + <5ms middleware overhead)
```

### Step 3: Load Test (1000 concurrent requests)

```bash
# Run load test
locust -f tests/performance/locustfile.py --users 1000 --spawn-rate 100

# Expected metrics:
# - JWT extraction: <3ms p95
# - Session read (Redis): <5ms p95
# - Policy evaluation: <1ms p95
# - Total overhead: <5ms p95 ✅
```

**Validation**:

- ✅ JWT extraction overhead <5ms (p95)
- ✅ Middleware overhead <2ms (p99)
- ✅ No database queries for tenant validation
- ✅ Performance budget met

---

## Test Scenario 7: Audit Trail Verification

**Goal**: Verify all authorization decisions logged for compliance.

### Step 1: Generate Test Traffic

```bash
# Execute multiple authorization scenarios
./scripts/test_authorization_scenarios.sh
```

### Step 2: Export Audit Logs

```bash
curl -X POST http://localhost:8000/api/v1/admin/logs/export \
  -H "Authorization: Bearer <superadmin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2025-10-19T00:00:00Z",
    "end_time": "2025-10-19T23:59:59Z",
    "categories": ["security.tenant_context", "auth.cross_tenant", "auth.tenant_switch"]
  }'

# Expected: JSON file with all tenant-related auth events
```

### Step 3: Validate Log Completeness

```bash
# Check audit log contains:
# 1. Tenant context extraction (every request)
# 2. Authorization decisions (allow/deny with policy rule)
# 3. Cross-tenant access attempts (denied + allowed)
# 4. Tenant switching events (superadmin only)
```

**Validation**:

- ✅ 100% of requests have tenant context log entry
- ✅ All denied access attempts logged at WARN level
- ✅ All superadmin cross-tenant access logged at INFO level
- ✅ Logs exportable for compliance audits

---

## Test Scenario 8: OWASP ZAP Security Scan

**Goal**: Verify IDOR vulnerabilities remediated.

### Step 1: Run Authenticated Scan

```bash
# Run OWASP ZAP authenticated scan
make security-authenticated

# Scan includes:
# - IDOR tests (modify tenant_id in path/query)
# - Session hijacking attempts
# - Authorization bypass tests
```

### Step 2: Review Findings

```bash
# Check ZAP report for OWASP A01:2021 findings
cat reports/security/zap-authenticated-report.html

# Expected: 0 HIGH/CRITICAL findings related to tenant isolation
```

**Validation**:

- ✅ No IDOR vulnerabilities detected
- ✅ Cross-tenant access blocked in all scenarios
- ✅ OWASP A01:2021 Broken Access Control: PASS

---

## Cleanup

```bash
# Stop server
make server-stop

# Clear test sessions
redis-cli FLUSHDB  # If using Redis sessions
```

## Success Criteria

All scenarios must pass:

- ✅ Scenario 1: Standard users tenant-isolated
- ✅ Scenario 2: Superadmin cross-tenant access works
- ✅ Scenario 3: Session-based tenant switching works
- ✅ Scenario 4: Backward compatibility maintained (30 days)
- ✅ Scenario 5: Authorization middleware enforces policies
- ✅ Scenario 6: Performance overhead <5ms (p95)
- ✅ Scenario 7: 100% audit coverage
- ✅ Scenario 8: 0 OWASP ZAP HIGH/CRITICAL findings

## Next Steps

After quickstart validation:

1. Run full contract test suite: `pytest tests/contract/`
2. Run integration tests: `pytest tests/integration/`
3. Update Copilot context: `.specify/scripts/bash/update-agent-context.sh copilot`
4. Ready for `/tasks` command to generate implementation tasks
