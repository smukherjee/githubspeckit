# Feature Specification: Tenant Context Security Refactor

**Feature ID**: 004  
**Priority**: 🔴 BLOCKING (MUST DO BEFORE /implement)  
**Status**: Planning  
**Owner**: Backend Team  
**Timeline**: 1 week (40 hours)  
**Related Findings**: S1 (CRITICAL), A1 (HIGH)

## Overview

Remediate OWASP A01:2021 Broken Access Control vulnerability by refactoring tenant_id from user-controlled query parameters to secure JWT claims + path parameters pattern. This prevents Insecure Direct Object Reference (IDOR) attacks where attackers can manipulate tenant_id values to access other tenants' data.

## Problem Statement

### Current Vulnerable Pattern

All current API endpoints accept tenant_id as a query parameter:

```
GET /api/v1/users?tenant_id=acme-corp-123
GET /api/v1/policies?tenant_id=acme-corp-123
```

**OWASP Violations**:
- **A01:2021 Broken Access Control**: User-controlled tenant_id allows attackers to modify values
- **CWE-639**: Authorization Bypass Through User-Controlled Key
- **Data Leakage**: tenant_id visible in browser history, Referer headers, proxy logs, CDN logs

**Attack Vector**:
```
# Legitimate request
GET /api/v1/users?tenant_id=acme-corp-123

# Attacker modifies parameter
GET /api/v1/users?tenant_id=victim-corp-789
```

If backend doesn't validate tenant_id against JWT claims, attacker gains unauthorized access.

### Compliance Impact

- **PCI-DSS 6.5.8**: Requires protection against authorization bypass
- **HIPAA Security Rule**: Tenant isolation critical for PHI protection
- **GDPR Article 32**: Data breach risk from inadequate access controls
- **SOC 2 CC6.1**: Logical access controls must prevent unauthorized access

## Solution Approach

### Secure Tenant Context Patterns

#### Pattern 1: JWT Claims Only (Standard Users)
Extract tenant_id from authenticated JWT token, not user input:

```python
# Current (INSECURE)
@router.get("/users")
async def list_users(tenant_id: str, current_user: User):
    return await user_repo.find_by_tenant(tenant_id)  # ❌ Uses user input

# Secure (JWT-based)
@router.get("/users")
async def list_users(current_user: User):
    tenant_id = current_user.tenant_id  # ✅ From verified JWT
    return await user_repo.find_by_tenant(tenant_id)
```

#### Pattern 2: Path Parameters (Superadmin Only)
For cross-tenant operations, use explicit path parameters with authorization checks:

```python
# Superadmin cross-tenant access
@router.get("/tenants/{tenant_id}/users")
async def list_tenant_users(tenant_id: str, current_user: User):
    if not current_user.is_superadmin:
        raise HTTPException(403, "Superadmin required for cross-tenant access")
    return await user_repo.find_by_tenant(tenant_id)
```

#### Pattern 3: Session-Based Context (UI Tenant Switching)
For superadmin UI, allow tenant switching via session:

```python
# Set active tenant in session
@router.post("/admin/context/tenant")
async def switch_tenant(tenant_id: str, current_user: User, session: Session):
    if not current_user.is_superadmin:
        raise HTTPException(403, "Superadmin required")
    session["active_tenant_id"] = tenant_id
    return {"active_tenant_id": tenant_id}

# Use session context in subsequent requests
@router.get("/users")
async def list_users(current_user: User, session: Session):
    tenant_id = session.get("active_tenant_id") or current_user.tenant_id
    return await user_repo.find_by_tenant(tenant_id)
```

## Functional Requirements

### FR-089: JWT-Based Tenant Context Extraction
**Priority**: P0 (CRITICAL)  
**Description**: All standard user API endpoints MUST extract tenant_id from JWT claims, never from query parameters.

**Acceptance Criteria**:
- ✅ Tenant context middleware extracts tenant_id from JWT `tenant_id` claim
- ✅ Middleware injects TenantContext(tenant_id, user_id, roles) into request state
- ✅ All repository methods receive tenant_id from context, not parameters
- ✅ Query parameter `tenant_id` is ignored or raises ValidationError

### FR-090: Path-Based Superadmin Tenant Scoping
**Priority**: P0 (CRITICAL)  
**Description**: Superadmin cross-tenant operations MUST use RESTful path parameters with explicit authorization checks.

**Acceptance Criteria**:
- ✅ New endpoint pattern: `/api/v1/tenants/{tenant_id}/users`
- ✅ Authorization middleware verifies `is_superadmin` flag before allowing access
- ✅ Path parameter tenant_id takes precedence over JWT claim for superadmin
- ✅ Non-superadmin requests to cross-tenant paths return 403 Forbidden

### FR-091: Session-Based Tenant Switching for UI
**Priority**: P1 (HIGH)  
**Description**: Admin UI supports superadmin tenant switching without re-authentication.

**Acceptance Criteria**:
- ✅ Endpoint: `POST /api/v1/admin/context/tenant` with `{"tenant_id": "..."}`
- ✅ Session stores `active_tenant_id` for duration of session
- ✅ Subsequent requests use session tenant_id if present, else JWT tenant_id
- ✅ Session tenant_id cleared on logout
- ✅ Only superadmin users can switch tenants

### FR-092: Authorization Middleware Enforcement
**Priority**: P0 (CRITICAL)  
**Description**: All API requests MUST pass through authorization middleware validating tenant context.

**Acceptance Criteria**:
- ✅ Middleware runs before route handlers
- ✅ Validates: JWT tenant_id matches extracted tenant_id (for standard users)
- ✅ Validates: User has permission to access requested tenant
- ✅ Returns 403 if user.tenant_id != requested_tenant_id AND NOT superadmin
- ✅ Audit event logged for unauthorized access attempts

### FR-093: Backward Compatibility Deprecation
**Priority**: P2 (MEDIUM)  
**Description**: Provide 30-day deprecation period for existing clients using query parameters.

**Acceptance Criteria**:
- ✅ If `?tenant_id=` query param present, log deprecation warning
- ✅ Response header: `Deprecation: true` + `Sunset: 2025-11-19`
- ✅ Documentation updated with migration guide
- ✅ After sunset date, query parameter raises 400 Bad Request

## Non-Functional Requirements

### NFR-089: Performance Impact
**Description**: Tenant context extraction must not degrade API latency.

**Acceptance Criteria**:
- ✅ JWT claim extraction adds <5ms overhead (p95)
- ✅ Middleware overhead <2ms per request (p99)
- ✅ No database queries for tenant validation (use JWT claims)

### NFR-090: Audit Logging
**Description**: All tenant context extraction and authorization decisions logged.

**Acceptance Criteria**:
- ✅ Log entry includes: tenant_id, user_id, endpoint, authorized (true/false), reason
- ✅ Failed authorization attempts logged at WARN level
- ✅ Successful cross-tenant access (superadmin) logged at INFO level
- ✅ Logs exportable for security analysis

### NFR-091: OWASP Compliance
**Description**: Implementation must pass OWASP ZAP automated security tests.

**Acceptance Criteria**:
- ✅ ZAP baseline scan: 0 HIGH/CRITICAL findings
- ✅ ZAP authenticated scan: No IDOR vulnerabilities detected
- ✅ Manual penetration test: Cross-tenant access blocked for standard users

## Technical Constraints

1. **Zero Database Schema Changes**: Solution must work with existing tenant_id columns
2. **JWT Structure**: tenant_id already exists in JWT claims (no JWT changes needed)
3. **Backward Compatibility**: 30-day deprecation period for query parameter pattern
4. **Session Backend**: Use FastAPI session middleware (encrypted cookies or Redis)
5. **OpenAPI Updates**: All endpoint specs must reflect new patterns

## Success Criteria

### Exit Criteria
- ✅ S1 finding resolved: No tenant_id in query parameters for standard users
- ✅ A1 finding resolved: Authorization middleware enforces tenant isolation
- ✅ All 22 contract tests updated and passing
- ✅ All 7 integration tests updated and passing
- ✅ OWASP ZAP authenticated scan: 0 IDOR findings
- ✅ Performance tests: <5ms JWT overhead, <2ms middleware overhead
- ✅ Documentation: Migration guide published

### Metrics
- **Security**: 0 IDOR vulnerabilities in ZAP scans
- **Performance**: p95 latency increase <5ms
- **Adoption**: 100% of endpoints migrated to secure pattern
- **Audit**: 100% of authorization decisions logged

## Dependencies

- Existing JWT authentication (already implemented)
- FastAPI dependency injection system
- Session middleware (to be added: `starlette.middleware.sessions`)
- OpenAPI schema generation pipeline

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking existing clients | HIGH | 30-day deprecation period + migration guide |
| Performance regression | MEDIUM | JWT caching, minimal middleware logic |
| Session hijacking | MEDIUM | Encrypted session cookies + CSRF protection |
| Superadmin privilege escalation | HIGH | Explicit authorization checks + audit logging |

## Out of Scope

- OAuth2/OIDC integration (separate feature: 005-oauth2-oidc-integration)
- Multi-factor authentication (future enhancement)
- Role-based tenant switching UI (UI team responsibility)
- Tenant hierarchy/parent-child relationships (future enhancement)

## Appendix

### Related Documents
- OWASP A01:2021: Broken Access Control
- CWE-639: Authorization Bypass Through User-Controlled Key
- Security Analysis Report: Finding S1, A1
- Constitution Principle III: Multi-Tenancy & Least Privilege

### Reference Implementation
See: `specs/002-react-admin-frontend/research.md` Section 5 for current (insecure) pattern.
