# Tasks: API Consolidation & RBAC Enhancement

**Input**: Revised implementation plan from `specs/002-react-admin-frontend/plan-revised.md`  
**Prerequisites**: plan-revised.md (required), constitution.md

## Executive Summary

This task plan **removes duplicate code** from Phase 3.3 and **enhances existing APIs** with:
- CSV user import
- Consistent soft-delete (`disabled` field)
- Automatic tenant isolation
- Role hierarchy endpoint
- Superadmin-only cross-tenant operations

**Total Tasks**: 19 (5 cleanup + 4 enhancement + 2 features + 5 testing + 3 documentation)  
**Estimated Effort**: 2-3 days solo, 1 day team of 2-3

---

## Phase 1: Cleanup - Delete Duplicate Code

**Critical**: Must complete before any other work

### T001: Delete Admin Endpoint Files ✅ COMPLETE

**Action**: Remove duplicate `/api/v1/admin/*` endpoints

```bash
rm -rf src/adapters/api/admin/
```

**Files Deleted**:
- tenants.py (285 lines)
- users.py (108 lines)
- policies.py (117 lines)
- feature_flags.py (108 lines)
- invitations.py (104 lines)
- audit_events.py (72 lines)
- bulk_operations.py (52 lines)
- \_\_init\_\_.py (23 lines)

**Total**: 875 lines deleted (confirmed)

**Validation**: ✅ `ls src/adapters/api/admin` returns "No such file or directory"

---

### T002: Delete Admin Schema Files ✅ COMPLETE

**Action**: Remove duplicate Pydantic schemas

```bash
rm -rf src/schemas/admin/
```

**Files Deleted**:
- common.py
- tenants.py
- users.py
- policies.py
- feature_flags.py
- invitations.py
- audit_events.py

**Total**: 7 files deleted

**Validation**: ✅ `ls src/schemas/admin` returns "No such file or directory"

---

### T003: Delete Admin Contract Tests ✅ COMPLETE

**Action**: Remove 18 duplicate test files

```bash
rm -rf tests/contract/admin/
```

**Files Deleted**:
- test_tenants_contract.py
- test_users_contract.py
- test_policies_contract.py
- test_feature_flags_contract.py
- test_invitations_contract.py
- test_audit_events_contract.py
- test_bulk_operations_contract.py
- (+ 11 more test files)

**Total**: 18 test files deleted

**Validation**: ✅ pytest tests/ -k "admin" --collect-only returns 0 tests

---

### T004: Update App Router Registration ✅ COMPLETE

**Action**: Remove admin router from `src/adapters/api/app.py`

**File**: `src/adapters/api/app.py`

**Delete Lines**:
```python
from adapters.api.admin import admin_router  # Line ~30
app.include_router(admin_router)  # Line ~196
```

**Validation**: ✅ App imports successfully without errors

---

### T005: Document Deletion ✅ COMPLETE

**Action**: Update `docs/ADMIN_API_IMPLEMENTATION_STATUS.md`

**File**: `docs/ADMIN_API_IMPLEMENTATION_STATUS.md`

**Add Section** (at top):
```markdown
## DEPRECATED: Admin Endpoints Removed

**Date**: 2025-01-18  
**Reason**: Duplicate functionality - all admin operations handled by existing `/api/v1/*` endpoints

**Deleted Code**:
- 8 admin endpoint files (875 lines)
- 7 admin schema files
- 18 admin contract tests
- **Total**: ~1,500 lines removed

**Replacement**:
All functionality available via existing production endpoints:
- `/api/v1/users` - Full CRUD with RBAC
- `/api/v1/tenants` - Full CRUD with RBAC
- `/api/v1/policies` - Full CRUD with RBAC
- `/api/v1/feature-flags` - Full CRUD with RBAC
- `/api/v1/invitations` - Full CRUD with RBAC
- `/api/v1/audit/events` - Query with filters

**Enhanced Functionality** (see tasks-revised.md):
- CSV import for bulk user management
- Role hierarchy endpoint
- Enforced tenant isolation
- Consistent soft-delete pattern
```

**Validation**: ✅ File updated, git diff shows new section

---

## Phase 2: Enhance Existing APIs

**Delete Lines**:
```python
from adapters.api.admin import admin_router  # Line ~30
app.include_router(admin_router)  # Line ~196
```

**Validation**: 
```bash
python -c "from src.adapters.api.app import create_app; app = create_app(); print([r.path for r in app.routes if 'admin' in r.path])"
# Should print: []
```

---

### T005: Document Deletion

**Action**: Update `docs/ADMIN_API_IMPLEMENTATION_STATUS.md`

**File**: `docs/ADMIN_API_IMPLEMENTATION_STATUS.md`

**Add Section** (at top):
```markdown
## DEPRECATED: Admin Endpoints Removed

**Date**: 2025-01-18  
**Reason**: Duplicate functionality - all admin operations handled by existing `/api/v1/*` endpoints

**Deleted Code**:
- 8 admin endpoint files (869 lines)
- 7 admin schema files
- 18 admin contract tests
- **Total**: ~1,500 lines removed

**Replacement**:
All functionality available via existing production endpoints:
- `/api/v1/users` - Full CRUD with RBAC
- `/api/v1/tenants` - Full CRUD with RBAC
- `/api/v1/policies` - Full CRUD with RBAC
- `/api/v1/feature-flags` - Full CRUD with RBAC
- `/api/v1/invitations` - Full CRUD with RBAC
- `/api/v1/audit/events` - Query with filters

**Enhanced Functionality** (see tasks T006-T019):
- CSV import for bulk user management
- Role hierarchy endpoint
- Enforced tenant isolation
- Consistent soft-delete pattern
```

**Validation**: File updated, git diff shows new section

---

## Phase 2: Enhance Existing APIs

### T006: Rename Tenant Soft-Delete Status

**Action**: Standardize `TenantStatus.soft_deleted` → `TenantStatus.disabled`

**Files**:

1. **src/domain/tenants/models.py**:
   ```python
   class TenantStatus(str, Enum):
       active = "active"
       disabled = "disabled"  # Was: soft_deleted
       invited = "invited"
       expired = "expired"
   ```

2. **Create Alembic Migration**:
   ```bash
   alembic revision -m "rename_tenant_soft_deleted_to_disabled"
   ```
   
   **Migration Content** (`alembic/versions/XXXX_rename_tenant_soft_deleted_to_disabled.py`):
   ```python
   def upgrade():
       op.execute("UPDATE tenants SET status = 'disabled' WHERE status = 'soft_deleted'")
   
   def downgrade():
       op.execute("UPDATE tenants SET status = 'soft_deleted' WHERE status = 'disabled'")
   ```

3. **Update Repository** (`src/adapters/persistence/repositories.py`):
   Replace all `TenantStatus.soft_deleted` → `TenantStatus.disabled`

4. **Update Router** (`src/adapters/api/routers/tenants.py`):
   Replace all `soft_deleted` → `disabled`

5. **Update Tests** (`tests/integration/test_tenants.py`, `tests/contract/test_tenants_contract.py`):
   Replace all `soft_deleted` → `disabled`

**Validation**: 
```bash
grep -r "soft_deleted" src/
# Should return 0 results
```

---

### T007: Fix GET APIs to Return Disabled Records

**Action**: Update all list endpoints to return disabled records by default

**Endpoints**:
1. GET `/api/v1/users`
2. GET `/api/v1/tenants`
3. GET `/api/v1/policies`
4. GET `/api/v1/feature-flags`

**Pattern** (apply to each):
```python
@router.get("")
async def list_resources(
    include_disabled: bool = Query(True, description="Include disabled records (default: true)"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """List resources.
    
    By default, returns ALL records including disabled.
    Use ?include_disabled=false to hide disabled records.
    """
    repo = SQLAlchemyResourceRepository(session)
    
    # Tenant isolation
    tenant_id = None if current_user.is_superadmin() else current_user.tenant_id
    
    # Get records
    resources = await repo.list_by_tenant(
        tenant_id=tenant_id,
        include_disabled=include_disabled
    )
    
    return {
        "data": [r.to_dict() for r in resources],
        "total": len(resources)
    }
```

**Files to Update**:
- `src/adapters/api/routers/users.py`
- `src/adapters/api/routers/tenants.py`
- `src/adapters/api/routers/policies.py`
- `src/adapters/api/routers/feature_flags.py`

**Validation**:
```bash
# Test with disabled records
curl "http://localhost:8000/api/v1/users" -H "Authorization: Bearer $TOKEN"
# Should include disabled users

# Test filtering
curl "http://localhost:8000/api/v1/users?include_disabled=false" -H "Authorization: Bearer $TOKEN"
# Should exclude disabled users
```

---

### T008: Add CSV Import Service

**Action**: Create CSV parsing and validation service

**New File**: `src/services/csv_import_service.py`

**Implementation** (see plan-revised.md, Phase 2, T008 for full code)

**Key Features**:
- CSV parsing with validation
- Email format validation
- Required field checking
- Dry-run preview mode
- Tenant isolation enforcement
- Detailed error reporting with line numbers

**Validation**:
```python
# Unit test
pytest tests/unit/services/test_csv_import_service.py -v
```

---

### T009: Add CSV Import Endpoint

**Action**: Add POST `/api/v1/users/import` to users router

**File**: `src/adapters/api/routers/users.py`

**Add Endpoint**:
```python
from fastapi import UploadFile, File, Query

@router.post("/import")
async def import_users_csv(
    file: UploadFile = File(..., description="CSV file with user data"),
    dry_run: bool = Query(False, description="Preview import without committing"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service)
):
    """Import users from CSV file.
    
    CSV Format:
    email,roles,tenant_id,full_name,job_title
    user@example.com,user,tenant-123,John Doe,Engineer
    
    RBAC:
    - tenant_admin: Can import users to own tenant only
    - superadmin: Can import users to any tenant
    
    Query Parameters:
    - dry_run: If true, validates CSV but doesn't create users (default: false)
    
    Returns:
    - success: bool
    - imported: int (number of users created)
    - errors: list (validation errors with line numbers)
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "File must be CSV format (.csv extension)")
    
    # Read CSV content
    content = await file.read()
    csv_text = content.decode('utf-8')
    
    # Import via service
    service = CSVImportService(SQLAlchemyUserRepository(session))
    result = await service.import_users(
        csv_content=csv_text,
        dry_run=dry_run,
        current_user_tenant_id=current_user.tenant_id,
        is_superadmin=current_user.is_superadmin()
    )
    
    # Audit log
    if not dry_run and result.get("success"):
        await audit.emit(
            action="users.bulk_import",
            resource_type="user",
            details={"imported": result["imported"]},
            tenant_id=current_user.tenant_id,
            actor_id=current_user.user_id
        )
    
    return result
```

**Validation**:
```bash
# Test valid import
curl -X POST http://localhost:8000/api/v1/users/import \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -F "file=@users.csv"

# Test dry run
curl -X POST "http://localhost:8000/api/v1/users/import?dry_run=true" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -F "file=@users.csv"
```

---

## Phase 3: New Features

### T010: Create Role Hierarchy Endpoint

**Action**: Add GET `/api/v1/roles` endpoint

**New File**: `src/adapters/api/routers/roles.py`

**Implementation** (see plan-revised.md, Phase 3, T010 for full code)

**Role Definitions**:
- superadmin (level 0) - Global admin, cannot be assigned via API
- tenant_admin (level 1) - Tenant-scoped admin, can assign developer/analyst/user/service_account/support_readonly
- developer (level 2) - Feature flags and deployment
- analyst (level 2) - Read-only audit and reports
- user (level 3) - Standard application access
- service_account (level 3) - API access for automation
- support_readonly (level 3) - Support troubleshooting

**Register Router** (`src/adapters/api/app.py`):
```python
from adapters.api.routers import roles as roles_router
app.include_router(roles_router.router, prefix="/api")
```

**Validation**:
```bash
curl http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer $USER_TOKEN"
# Should return 7 roles sorted by hierarchy_level
```

---

### T011: Add Cross-Tenant RBAC Validation Helpers

**Action**: Create reusable RBAC validation functions

**New File**: `src/adapters/api/rbac.py`

**Functions**:
1. `validate_cross_tenant_access(current_user, resource_tenant_id, operation)`
2. `validate_role_assignment(current_user, target_role)`

**Implementation** (see plan-revised.md, Phase 3, T011 for full code)

**Update Existing Endpoints** to use validation:
- POST `/api/v1/users` - Validate cross-tenant creation
- PUT `/api/v1/users/{user_id}` - Validate cross-tenant update
- DELETE `/api/v1/users/{user_id}` - Validate cross-tenant delete
- POST `/api/v1/tenants` - Superadmin only
- POST `/api/v1/policies` - Validate tenant
- POST `/api/v1/feature-flags` - Validate tenant

**Pattern**:
```python
from adapters.api.rbac import validate_cross_tenant_access, validate_role_assignment

@router.post("")
async def create_user(
    request: UserCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    # Validate cross-tenant access
    validate_cross_tenant_access(current_user, request.tenant_id, "user creation")
    
    # Validate role assignment
    for role in request.roles:
        validate_role_assignment(current_user, role)
    
    # Proceed with creation...
```

**Validation**:
```bash
# Non-superadmin attempts cross-tenant creation
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@other.com", "tenant_id": "other-tenant", "roles": ["user"]}'
# Should return 403: Cross-tenant user creation requires superadmin role
```

---

## Phase 4: Testing & Validation

### T012: Create Cross-Tenant RBAC Tests

**New File**: `tests/integration/test_cross_tenant_rbac.py`

**Tests**:
1. `test_tenant_admin_cannot_create_user_in_other_tenant` - Expect 403
2. `test_superadmin_can_create_user_in_any_tenant` - Expect 201
3. `test_tenant_admin_cannot_assign_superadmin_role` - Expect 403
4. `test_tenant_admin_can_assign_user_role` - Expect 201
5. `test_tenant_admin_cannot_update_user_in_other_tenant` - Expect 403
6. `test_tenant_admin_cannot_delete_user_in_other_tenant` - Expect 403
7. `test_non_superadmin_cannot_create_tenant` - Expect 403
8. `test_non_superadmin_cannot_list_other_tenant_resources` - Expect filtered results

**Implementation** (see plan-revised.md, Phase 4, T012 for test code)

**Validation**:
```bash
pytest tests/integration/test_cross_tenant_rbac.py -v
# All 8 tests should pass
```

---

### T013: Create CSV Import Tests

**New File**: `tests/integration/test_csv_import.py`

**Tests**:
1. `test_csv_import_valid` - Import 2 users, expect success
2. `test_csv_import_dry_run` - Dry run doesn't create users
3. `test_csv_import_invalid_email` - Reject invalid email format
4. `test_csv_import_missing_required_field` - Reject missing fields
5. `test_csv_import_cross_tenant_blocked_for_tenant_admin` - Expect error
6. `test_csv_import_superadmin_cross_tenant` - Expect success
7. `test_csv_import_duplicate_email` - Handle duplicates gracefully
8. `test_csv_import_large_file` - Import 100 users, validate performance

**Implementation** (see plan-revised.md, Phase 4, T013 for test code)

**Validation**:
```bash
pytest tests/integration/test_csv_import.py -v
# All 8 tests should pass
```

---

### T014: Create Role Hierarchy Tests

**New File**: `tests/integration/test_role_hierarchy.py`

**Tests**:
1. `test_list_roles_authenticated` - User can list roles
2. `test_list_roles_unauthenticated` - Blocked with 401
3. `test_role_hierarchy_order` - Superadmin first, user last
4. `test_role_assignment_permissions` - Verify can_assign rules
5. `test_tenant_admin_cannot_assign_superadmin` - Blocked

**Implementation** (see plan-revised.md, Phase 4, T014 for test code)

**Validation**:
```bash
pytest tests/integration/test_role_hierarchy.py -v
# All 5 tests should pass
```

---

### T015: Update Existing Contract Tests

**Action**: Update contract tests to validate new behaviors

**Files to Update**:

1. **tests/contract/test_users_contract.py**:
   - Add `test_csv_import_endpoint_exists`
   - Add `test_list_users_includes_disabled_by_default`
   - Update `test_create_user_cross_tenant_blocked`

2. **tests/contract/test_tenants_contract.py**:
   - Update `test_list_tenants_includes_disabled`
   - Add `test_create_tenant_superadmin_only`

3. **tests/contract/test_policies_contract.py**:
   - Add `test_list_policies_includes_disabled`

4. **tests/contract/test_feature_flags_contract.py**:
   - Add `test_list_flags_includes_disabled`

**New File**: `tests/contract/test_roles_contract.py`
- `test_list_roles_returns_7_roles`
- `test_roles_sorted_by_hierarchy`

**Validation**:
```bash
pytest tests/contract/ -v
# All contract tests should pass
```

---

### T016: Performance Testing

**Action**: Validate performance requirements

**New File**: `tests/performance/test_api_performance.py`

**Tests**:
1. `test_csv_import_performance_100_users` - <5s
2. `test_role_listing_performance` - <50ms
3. `test_list_users_performance_1000_records` - <200ms
4. `test_cross_tenant_validation_performance` - <10ms overhead

**Implementation**:
```python
import pytest
from httpx import AsyncClient
import time

@pytest.mark.asyncio
@pytest.mark.performance
async def test_csv_import_performance(async_client, superadmin_headers):
    """CSV import of 100 users completes in <5s."""
    # Generate CSV with 100 users
    csv_lines = ["email,roles,tenant_id"]
    for i in range(100):
        csv_lines.append(f"perfuser{i}@test.com,user,test-tenant")
    csv_content = "\n".join(csv_lines)
    
    files = {"file": ("users.csv", BytesIO(csv_content.encode()), "text/csv")}
    
    start = time.time()
    response = await async_client.post(
        "/api/v1/users/import",
        files=files,
        headers=superadmin_headers
    )
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 5.0, f"Import took {duration:.2f}s (expected <5s)"
    assert response.json()["imported"] == 100
```

**Validation**:
```bash
pytest tests/performance/test_api_performance.py -v -m performance
# All performance tests should pass
```

---

## Phase 5: Documentation

### T017: Update OpenAPI Contracts

**Action**: Add new endpoint contracts

**Files**:

1. **specs/002-react-admin-frontend/contracts/openapi-users.yaml**:
   Add `/api/v1/users/import` endpoint definition

2. **New File**: `specs/002-react-admin-frontend/contracts/openapi-roles.yaml`:
   Define `/api/v1/roles` endpoint

3. **Update**: `specs/002-react-admin-frontend/contracts/openapi-admin.yaml`:
   Mark as DEPRECATED, point to `/api/v1/*` endpoints

**Validation**:
```bash
python scripts/build_openapi_bundle.py
# Should generate valid OpenAPI 3.0 bundle
```

---

### T018: Update Quickstart Guide

**File**: `specs/002-react-admin-frontend/quickstart.md`

**Add Sections**:
1. CSV User Import (basic + dry run examples)
2. Role Hierarchy (list roles example)
3. Tenant Isolation (cross-tenant blocked examples)
4. Soft-Delete Filtering (include_disabled parameter)

**Example**:
```markdown
## CSV User Import

### Basic Import
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/users/import \\
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \\
  -F "file=@users.csv"
\`\`\`

### Dry Run Preview
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/users/import?dry_run=true \\
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \\
  -F "file=@users.csv"
\`\`\`

## Role Hierarchy

\`\`\`bash
curl http://localhost:8000/api/v1/roles \\
  -H "Authorization: Bearer $USER_TOKEN"
\`\`\`
```

**Validation**: All quickstart commands execute successfully

---

### T019: Update Specification

**File**: `specs/002-react-admin-frontend/spec.md`

**Revisions**:
1. **Title**: Change to "API Consolidation & RBAC Enhancement"
2. **Remove**: All references to `/api/v1/admin/*` endpoints
3. **Add FR-088**: CSV import for bulk user management
4. **Add FR-089**: Role hierarchy endpoint
5. **Add FR-090**: Automatic tenant isolation for non-superadmin
6. **Add FR-091**: Cross-tenant operation validation
7. **Update NFR-002**: Add CSV import performance (<5s for 100 users)
8. **Update Acceptance Scenarios**: Replace admin endpoint examples with `/api/v1/*`

**Example Update**:
```markdown
### Functional Requirements

#### Bulk Operations

- **FR-088**: System MUST support CSV import for bulk user creation
- **FR-089**: System MUST provide role hierarchy endpoint listing all available roles
- **FR-090**: System MUST automatically filter resources by tenant_id for non-superadmin users
- **FR-091**: System MUST validate cross-tenant operations and block non-superadmin users

#### RBAC Enhancements

- **FR-092**: Only superadmin users MUST be able to perform CRUD operations across tenants
- **FR-093**: tenant_admin users MUST be able to assign roles: developer, analyst, user, service_account, support_readonly
- **FR-094**: tenant_admin users MUST NOT be able to assign superadmin role
- **FR-095**: CSV import MUST enforce tenant isolation (non-superadmin can only import to own tenant)
```

**Validation**: Spec accurately reflects implemented functionality

---

## Dependencies

```
Cleanup (T001-T005) → Enhancement (T006-T009) → Features (T010-T011) → Testing (T012-T016) → Documentation (T017-T019)

Key Blockers:
- T001-T005 MUST complete before any other work (delete duplicate code)
- T006-T007 block T015 (contract test updates)
- T008-T009 block T013 (CSV import tests)
- T010-T011 block T012, T014 (RBAC tests)
- All implementation (T001-T011) blocks documentation (T017-T019)
```

---

## Parallel Execution Examples

### Phase 1: Cleanup (Sequential)
```bash
# Must run in order
Task T001: rm -rf src/adapters/api/admin/
Task T002: rm -rf src/schemas/admin/
Task T003: rm -rf tests/contract/admin/
Task T004: Update app.py
Task T005: Document deletion
```

### Phase 2: Enhancement (Partial Parallel)
```bash
# T006-T007 can run in parallel
Task T006: Rename TenantStatus.soft_deleted [P]
Task T007: Fix GET APIs to return disabled [P]

# T008-T009 sequential (T009 depends on T008)
Task T008: Create CSV import service
Task T009: Add CSV import endpoint
```

### Phase 3: Features (Parallel)
```bash
# T010-T011 can run in parallel
Task T010: Create role hierarchy endpoint [P]
Task T011: Add RBAC validation helpers [P]
```

### Phase 4: Testing (Parallel)
```bash
# T012-T016 can run in parallel after implementation complete
Task T012: Cross-tenant RBAC tests [P]
Task T013: CSV import tests [P]
Task T014: Role hierarchy tests [P]
Task T015: Update contract tests [P]
Task T016: Performance tests [P]
```

### Phase 5: Documentation (Parallel)
```bash
# T017-T019 can run in parallel
Task T017: Update OpenAPI contracts [P]
Task T018: Update quickstart guide [P]
Task T019: Update specification [P]
```

---

## Summary

- **Total Tasks**: 19
- **Parallel Tasks**: 11 marked [P]
- **Estimated Effort**: 16-24 hours (2-3 days solo, 1 day team)
- **Code Impact**:
  - **Deleted**: ~1,500 lines (admin endpoints + schemas + tests)
  - **Added**: ~780 lines (CSV import, roles, RBAC, tests)
  - **Net**: -720 lines (48% reduction)

## Validation Checklist

**Before Task Execution**:
- [x] Plan reviewed and approved
- [x] Constitution check passed
- [x] Duplicate code identified
- [x] Enhancement requirements defined

**After Phase 1 (Cleanup)**:
- [ ] Admin directory deleted
- [ ] Admin schemas deleted
- [ ] Admin tests deleted
- [ ] App router updated
- [ ] Deletion documented

**After Phase 2 (Enhancement)**:
- [ ] Tenant status renamed to disabled
- [ ] GET APIs return disabled records
- [ ] CSV import service created
- [ ] CSV import endpoint added

**After Phase 3 (Features)**:
- [ ] Role hierarchy endpoint created
- [ ] RBAC validation helpers added
- [ ] Cross-tenant validation enforced

**After Phase 4 (Testing)**:
- [ ] Cross-tenant RBAC tests pass
- [ ] CSV import tests pass
- [ ] Role hierarchy tests pass
- [ ] Contract tests updated and pass
- [ ] Performance tests pass

**After Phase 5 (Documentation)**:
- [ ] OpenAPI contracts updated
- [ ] Quickstart guide updated
- [ ] Specification revised

---

## Next Steps

1. **Get User Approval**: Confirm this plan before executing
2. **Execute Phase 1**: Delete all duplicate admin code
3. **Execute Phase 2**: Add CSV import and fix soft-delete
4. **Execute Phase 3**: Create role hierarchy and RBAC validation
5. **Execute Phase 4**: Run all tests and validate performance
6. **Execute Phase 5**: Update all documentation

**Ready to begin**: Awaiting user confirmation to proceed with T001

---

*Based on Constitution v1.5.1 and plan-revised.md*
