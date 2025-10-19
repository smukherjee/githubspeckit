# Router Migration Audit Report (T041)

**Feature**: 004-tenant-security-refactor  
**Date**: 2025-10-19  
**Task**: T041 - Audit existing routers for tenant_id query parameter usage

---

## Summary

Audited 11 router files for `tenant_id` query parameter usage. Found **2 routers** using query parameters that need migration.

### Routers Requiring Migration

1. **audit.py** ✅ Needs Migration
   - Endpoint: `GET /v1/audit/events`
   - Query param: `tenant_id: Optional[str] = None`
   - Usage: Filter audit events by tenant
   - Migration: Use `tenant_context.effective_tenant_id`

2. **policies.py** ✅ Needs Migration
   - Endpoint: `GET /v1/policies`
   - Query param: `tenant_id: str | None = None`
   - Usage: Superadmin cross-tenant access
   - Migration: Use `tenant_context.effective_tenant_id` OR require path parameter

### Routers NOT Using Query Parameters

3. **invitations.py** ❌ No Migration Needed
   - Uses `current_user.tenant_id` only
   - No query parameter

4. **roles.py** ❌ No Migration Needed
   - Read-only role hierarchy
   - No tenant scoping needed

5. **feature_flags.py** ❌ No Migration Needed (to verify)

6. **embed.py** ❌ No Migration Needed (to verify)

7. **profile.py** ❌ No Migration Needed (to verify)

8. **users.py** ⚠️ Partially Migrated
   - Already has `/me` endpoint (T040 complete)
   - Legacy endpoints may still use query params (to verify)

9. **auth.py** ❌ No Migration Needed
   - Authentication endpoints
   - No tenant scoping in endpoints

10. **tenants.py** (file) ❌ No Migration Needed
    - Tenant CRUD operations
    - No query parameter usage

11. **admin/** (package) ✅ Already Migrated
    - T035-T036 complete
    - Uses path parameters and middleware

---

## Detailed Audit

### 1. audit.py - REQUIRES MIGRATION (T042)

**Current Implementation**:
```python
@router.get("/events")
async def list_events(
    tenant_id: Optional[str] = None,  # ← QUERY PARAMETER
    action: Optional[str] = None,
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
```

**Usage Pattern**:
- Optional query parameter for filtering
- Used by both superadmin (cross-tenant) and tenant users (own tenant)
- No explicit RBAC check in endpoint

**Migration Strategy**:
1. Remove `tenant_id` query parameter
2. Inject `tenant_context: TenantContext` from request.state
3. Use `tenant_context.effective_tenant_id` for filtering
4. Superadmin can switch tenants via session (POST /admin/context/tenant)

**Breaking Change**: Yes - clients using `?tenant_id=` will receive deprecation warning

---

### 2. policies.py - REQUIRES MIGRATION (T043)

**Current Implementation**:
```python
@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    response: Response,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    tenant_id: str | None = None,  # ← QUERY PARAMETER
    include_deleted: bool = False
) -> list[PolicyResponse]:
```

**Usage Pattern**:
- Superadmin can specify `tenant_id` to list policies for any tenant
- Tenant admin must use own `tenant_id` (enforced)
- Explicit RBAC check: `if tenant_id != current_user.tenant_id: raise 403`

**Migration Strategy**:
1. Remove `tenant_id` query parameter
2. Inject `tenant_context: TenantContext` from request.state
3. Use `tenant_context.effective_tenant_id` for filtering
4. Superadmin switches tenant via session (not query param)

**Breaking Change**: Yes - superadmin clients must use session switching

---

### 3. invitations.py - NO MIGRATION NEEDED

**Current Implementation**:
```python
# Uses current_user.tenant_id only
# No query parameters
```

**Status**: ✅ Already compliant with new architecture

---

### 4. roles.py - NO MIGRATION NEEDED

**Current Implementation**:
```python
@router.get("/roles")
async def list_roles(
    current_user: CurrentUser = Depends(get_current_user)
) -> RolesListResponse:
```

**Status**: ✅ No tenant scoping needed (global role hierarchy)

---

## Migration Plan (T042-T048)

### Priority 1: Core Data Routes (T042-T043)

**T042**: Migrate `audit.py` - Audit events filtering
**T043**: Migrate `policies.py` - Policy listing

### Priority 2: Verify & Document (T044-T048)

**T044**: Verify `invitations.py` - Already compliant
**T045**: Verify `roles.py` - No tenant scoping needed
**T046**: Verify `feature_flags.py` - Check for query params
**T047**: Verify `embed.py` - Check for query params
**T048**: Verify `profile.py` - Check for query params

---

## Testing Strategy

### Contract Tests
- Update existing contract tests to remove `?tenant_id=` usage
- Add new tests for tenant context from JWT
- Add tests for superadmin session switching

### Integration Tests
- Test deprecation warnings (before sunset date)
- Test 400 Bad Request (after sunset date)
- Test RBAC enforcement with new context extraction

### Backward Compatibility
- DeprecationWarningMiddleware handles `?tenant_id=` during transition
- Clients have 30 days to migrate (until 2025-11-19)

---

## Migration Checklist

- [x] **T041**: Audit all routers for query param usage
- [ ] **T042**: Migrate audit.py
- [ ] **T043**: Migrate policies.py
- [ ] **T044**: Verify invitations.py
- [ ] **T045**: Verify roles.py
- [ ] **T046**: Verify feature_flags.py
- [ ] **T047**: Verify embed.py
- [ ] **T048**: Verify profile.py

---

## Risk Assessment

### High Risk
- **policies.py**: Critical RBAC functionality
- **audit.py**: Security audit trail access

### Medium Risk
- None identified

### Low Risk
- **invitations.py**: Already compliant
- **roles.py**: No tenant scoping

### Mitigation
1. Implement deprecation warnings first (DeprecationWarningMiddleware)
2. Run full integration test suite after each migration
3. Keep backward compatibility for 30 days
4. Document migration guide for API clients

---

**Status**: Audit Complete - Ready for T042-T048 implementation  
**Next**: Start with T042 (audit.py migration)
