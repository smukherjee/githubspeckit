# Phase 3 Debt Implementation Status

**Date**: 2025-10-05  
**Objective**: Fix Phase 3 debt items (event loop, database backing for invitations/audit/embed)

## ✅ Completed Items

### 1. Database-Backed Repositories (DONE)

**SQLAlchemyInvitationRepository**:
- ✅ Created in `src/adapters/persistence/repositories.py`
- ✅ Implements async CRUD operations
- ✅ Tenant isolation enforced
- ✅ Token stored as SHA-256 hash

**SQLAlchemyAuditAppender**:
- ✅ Created in `src/adapters/persistence/repositories.py`
- ✅ Implements append-only audit log
- ✅ Database-backed with pagination support
- ✅ Metadata redaction enforced

### 2. Dependency Injection Updates (DONE)

- ✅ Updated `src/adapters/api/deps.py`:
  - Added `SQLAlchemyInvitationRepository` import
  - Added `SQLAlchemyAuditAppender` import  
  - Updated `get_invitation_repo()` to return database-backed repository
  - Updated `get_invitation_service()` with proper Depends injection
  - Created `AuditService` class replacing `InMemoryAuditService`
  - Added `get_audit_appender()` and `get_audit_service()` with database backing

### 3. Router Updates (DONE)

**Audit Router** (`src/adapters/api/routers/audit.py`):
- ✅ Updated to use `SQLAlchemyAuditAppender`
- ✅ Queries database for audit events
- ✅ Supports filtering by tenant_id, action, time range
- ✅ Returns paginated results

### 4. Event Loop Fixes (DONE)

- ✅ Updated `pytest.ini`: Added `asyncio_mode = auto`
- ✅ Updated `tests/api/integration/conftest.py`:
  - Removed manual event_loop fixture (pytest-asyncio handles it)
  - Added proper engine disposal with sleep for connection cleanup
  - Fixed session-scoped fixtures

### 5. UUID Conversion Fixes (DONE)

- ✅ Fixed `tenant_domain_to_model()`: Handle non-UUID values like "system"
- ✅ Fixed `user_domain_to_model()`: Handle non-UUID values like "system"
- ✅ Created `to_uuid_or_none()` helper function for safe conversion

## ⚠️ Remaining Issues

### 1. Invitation Service Integration (PARTIAL)

**Status**: Repository created but service may need updates

**Error**: `AttributeError` when accepting invitations  
**File**: `src/services/invitations_service.py`

**Action Needed**:
- Check if InvitationService expects sync or async repository methods
- Update service to use async/await for repository calls
- Test invitation acceptance flow end-to-end

### 2. Policy Endpoints Missing (NOT REGISTERED)

**Status**: Routes return 404

**Missing Endpoints**:
- `/api/v1/policies/dry-run` (POST)
- `/api/v1/policies/register` (POST)

**Files to Check**:
- `src/adapters/api/routers/policies.py`
- `src/adapters/api/app.py` (router registration)

**Action Needed**:
- Verify policy router exists
- Ensure router is registered in app.py with `/api` prefix
- Implement policy dry-run logic
- Implement policy registration logic

### 3. OpenAPI Bundle Path Mismatch (MINOR)

**Status**: Tests expect `/v1/` but app serves `/api/v1/`

**Error**: `Missing path /v1/invitations/{invitation_id}/accept`

**Action Needed**:
- Update test expectations to use `/api/v1/` prefix
- OR update OpenAPI bundle generation to include both prefixes
- Document the `/api` prefix convention

### 4. Response Format Mismatches (MINOR)

**Tests Failing**:
- `test_auth_login_success_and_error_shapes`
- `test_feature_flags_crud_basic`
- `test_user_disable_restore_contract`

**Issue**: Tests expect `tenant_id` in response but getting different structure

**Action Needed**:
- Review test expectations vs actual response format
- Update tests or router responses for consistency

## 📊 Test Results Summary

**Contract Tests**: 8 failed, 7 passed, 12 skipped  
**Integration Tests**: Not fully tested yet

**Passing**:
- ✅ Embed exchange contract
- ✅ Health/config endpoints
- ✅ Metrics endpoints
- ✅ Config error report
- ✅ Audit query (basic)

**Failing**:
- ❌ Auth login (response format)
- ❌ Feature flags CRUD (response format)
- ❌ Invitation accept (AttributeError in service)
- ❌ Policy dry-run (404 - route missing)
- ❌ Policy registration (404 - route missing)
- ❌ User disable/restore (response format)
- ❌ OpenAPI bundle (path prefix mismatch)

## 🎯 Next Steps

### Priority 1: Fix Invitation Service
1. Update `InvitationService` to use async repository methods
2. Ensure proper error handling
3. Test invitation accept flow

### Priority 2: Register Policy Routes
1. Check if policy router exists
2. Register in app.py with correct prefix
3. Implement stub policy dry-run and registration

### Priority 3: Fix Response Formats
1. Review failing test expectations
2. Align router responses with test expectations
3. Update tests if needed for consistency

### Priority 4: Event Loop Stabilization
1. Run full integration test suite
2. Monitor for event loop closure errors
3. Adjust fixtures/cleanup if needed

## 📝 Implementation Notes

### UUID Handling Pattern
```python
def to_uuid_or_none(value: Optional[str]) -> Optional[UUID]:
    """Convert string to UUID, return None if not a valid UUID."""
    if not value:
        return None
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        # Not a valid UUID (e.g., "system"), store as NULL
        return None
```

### Audit Service Pattern
```python
class AuditService:
    def __init__(self, appender: SQLAlchemyAuditAppender) -> None:
        self.appender = appender

    async def log(self, *, action_type: str, tenant_id: str | None, metadata: dict | None = None) -> None:
        event = AuditEvent(...)
        await self.appender.append(event)
```

### Dependency Injection Pattern
```python
async def get_invitation_repo(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyInvitationRepository:
    return SQLAlchemyInvitationRepository(session)

async def get_invitation_service(
    invitation_repo: SQLAlchemyInvitationRepository = Depends(get_invitation_repo)
) -> InvitationService:
    return InvitationService(repo=invitation_repo)
```

## ✅ Completion Criteria

- [ ] All contract tests passing (target: 19+ passed)
- [ ] All integration tests passing
- [ ] No event loop closure errors
- [ ] Database-backed invitations, audit, and embed
- [ ] Policy endpoints functional
- [ ] Response formats consistent
- [ ] Documentation updated
