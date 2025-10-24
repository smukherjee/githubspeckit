# Admin Routes V1.0 Implementation

**Date**: 2025-10-20  
**Phase**: 3.3 - Admin Router Cleanup (T037-T041)  
**Status**: ✅ Complete

## Summary

Implemented POST endpoints for admin tenant and user management to support V1.0 contract tests. Admin routes now fully functional for superadmin operations across all tenants.

## Changes Made

### 1. Admin Tenants Router (`src/adapters/api/routers/admin/tenants.py`)

**Added Models**:
- `TenantCreateRequest`: Request model for creating tenants
  - `name`: Required tenant display name
  - `slug`: Optional URL-safe slug (auto-generated if omitted)
  - `owner_email`: Optional owner email

**Modified Models**:
- `TenantResponse`: Made `owner_email` optional (was required)

**New Endpoint**:
```python
POST /api/v1/admin/tenants
```

**Features**:
- Superadmin-only access (403 for non-superadmin)
- Auto-generates slug from name if not provided
- Checks for duplicate tenant names (409 conflict)
- Returns 201 Created with tenant details
- Proper error handling with rollback on failure

**Implementation Details**:
```python
@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    request_data: TenantCreateRequest,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TenantResponse:
    # Superadmin check
    # Slug generation
    # Duplicate check via repo.get_by_name()
    # Create Tenant domain entity
    # Save via repo.upsert()
    # Commit and return
```

### 2. Admin Users Router (`src/adapters/api/routers/admin/users.py`)

**Added Models**:
- `UserCreateRequest`: Request model for creating users
  - `email`: Required email address (EmailStr)
  - `password`: Required password (min 8 chars)
  - `tenant_id`: Required tenant assignment
  - `roles`: Optional list of roles (default empty)

**Modified Imports**:
- Added `uuid4` for user ID generation
- Added `Field` for Pydantic field constraints
- Added `User` domain model
- Added `default_hasher` from `auth_core.hashers`

**New Endpoint**:
```python
POST /api/v1/admin/users
```

**Features**:
- Superadmin-only access (403 for non-superadmin)
- Per-tenant email uniqueness enforcement (409 for duplicates within tenant)
- Case-insensitive email handling (normalize to lowercase)
- Password hashing via Argon2
- Created users are immediately `active` status
- Proper error handling with rollback on failure

**Implementation Details**:
```python
@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request_data: UserCreateRequest,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    # Superadmin check
    # Check email uniqueness within tenant
    # Hash password with Argon2
    # Create User domain entity
    # Save via repo.upsert()
    # Commit and return
```

### 3. Email Uniqueness Enforcement

**Per-Tenant Uniqueness**:
- Same email can exist in different tenants ✅
- Email must be unique within each tenant ✅
- Case-insensitive comparison (`email.lower()`)

**Error Response Format**:
- Changed from nested dict to simple string for consistency
- Old: `{"error": {"code": "EMAIL_EXISTS", "message": "..."}}`
- New: `"Email 'user@example.com' already exists in this tenant"`
- Matches test expectations and simpler error handling

## Testing Results

### Email Uniqueness Contract Tests

All 4 tests now **PASSING**:

1. **test_duplicate_email_same_tenant_rejected** ✅
   - Creates tenant
   - Creates user with email
   - Attempts to create second user with same email
   - Expects 409 Conflict
   - Verifies error message mentions "email"

2. **test_case_insensitive_email_uniqueness_same_tenant** ✅
   - Creates tenant
   - Creates user with `test@example.com`
   - Attempts to create user with `TEST@example.com`
   - Expects 409 Conflict (case-insensitive)

3. **test_same_email_different_tenants_allowed** ✅
   - Creates 2 tenants
   - Creates user with same email in each tenant
   - Both succeed with 201 Created
   - Verifies unique user IDs

4. **test_multiple_tenants_share_email_pool** ✅
   - Creates 3 tenants
   - Creates user with same email in all 3 tenants
   - All succeed with 201 Created
   - Verifies all users have unique IDs
   - Verifies all tenants are different

### Test Suite Status

**Before Admin Routes**:
- 40 failed, 337 passed, 55 skipped, 52 errors

**After Admin Routes**:
- **38 failed**, **339 passed**, 55 skipped, 52 errors

**Improvement**:
- ✅ 2 fewer failures
- ✅ 2 more passing tests
- ✅ Email uniqueness tests: 0/4 → 4/4 passing

## API Documentation

### POST /api/v1/admin/tenants

**Request**:
```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "owner_email": "admin@acme.com"
}
```

**Response** (201 Created):
```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "owner_email": "admin@acme.com",
  "status": "active",
  "created_at": "2025-10-20T14:30:00Z"
}
```

**Errors**:
- `403 Forbidden`: User is not superadmin
- `409 Conflict`: Tenant name already exists
- `500 Internal Server Error`: Database error

### POST /api/v1/admin/users

**Request**:
```json
{
  "email": "user@acme.com",
  "password": "SecurePass123!",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "roles": ["user"]
}
```

**Response** (201 Created):
```json
{
  "user_id": "456e7890-e89b-12d3-a456-426614174111",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@acme.com",
  "status": "active",
  "roles": ["user"],
  "created_at": "2025-10-20T14:35:00Z"
}
```

**Errors**:
- `403 Forbidden`: User is not superadmin
- `409 Conflict`: Email already exists in this tenant
- `500 Internal Server Error`: Database error

## Architecture Notes

### Domain Model Usage

**Tenants**:
- Uses `Tenant` dataclass from `domain.tenants.models`
- Fields: `tenant_id` (str), `name`, `status` (TenantStatus enum)
- Repository: `SQLAlchemyTenantRepository.upsert()`

**Users**:
- Uses `User` dataclass from `domain.users.models`
- Fields: `user_id` (str), `tenant_id`, `email`, `password_hash`, `status`, `roles`
- Repository: `SQLAlchemyUserRepository.upsert()`
- Password hashing: `auth_core.hashers.default_hasher.hash()`

### Authorization

Both endpoints check `tenant_context.is_superadmin`:
```python
if not tenant_context.is_superadmin:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": "SUPERADMIN_REQUIRED", "message": "..."}}
    )
```

### Database Operations

**Transaction Management**:
```python
try:
    # Create domain entity
    # Save via repository
    await db.commit()
    return response
except HTTPException:
    raise
except Exception as e:
    await db.rollback()
    raise HTTPException(status_code=500, ...)
```

## Dependencies

### Database Migration

Admin routes depend on Phase 3.3 Database Migration:
- ✅ Composite unique index `idx_users_email_tenant` on `(email, tenant_id)`
- ✅ Global `users_email_key` constraint dropped
- ✅ PostgreSQL-only (SQLite support removed)

### Auth Core

Password hashing:
```python
from auth_core.hashers import default_hasher

password_hash = default_hasher.hash(plaintext_password)
```

Uses Argon2id with configurable parameters from environment.

## Future Enhancements

### Phase 3.3: Email Uniqueness Enforcement (T042-T045)

Next tasks (not blocking for admin routes):
- Add `get_by_email_and_tenant()` repository method
- Update service validation layer
- Improve error messages with domain-specific exceptions
- Add email normalization helper

### Admin CRUD Completeness

Current: CREATE + READ  
Missing: UPDATE + DELETE

Would add:
- `PUT /api/v1/admin/tenants/{id}` - Update tenant
- `DELETE /api/v1/admin/tenants/{id}` - Disable tenant
- `PUT /api/v1/admin/users/{id}` - Update user
- `DELETE /api/v1/admin/users/{id}` - Disable user

### Pagination

Current: In-memory pagination after DB query  
Future: Database-level pagination for performance:
```python
query = select(UserModel).limit(per_page).offset(start_idx)
```

### Filtering & Search

Add query parameters:
- `?status=active` - Filter by status
- `?search=john@` - Search by email prefix
- `?role=admin` - Filter by role

## Tasks Completed

- [x] **T037**: Verify working admin routes functional ✅
- [x] **T038**: Remove incomplete policy routes from app.py (not needed - policy routes already deferred)
- [x] **T039**: Update contract tests: test_tenants.py routes (tests already use correct paths)
- [x] **T040**: Update contract tests: test_users.py routes (tests already use correct paths)
- [x] **T041**: Verify no legacy routes exist (404 test) (tests verify deprecated routes return 404)

## Related Documentation

- `docs/SQLITE_REMOVAL_V1.0.md` - PostgreSQL-only migration
- `specs/012-v1-cleanup-legacy-removal/tasks.md` - Task breakdown
- `tests/contract/test_email_uniqueness_*.py` - Contract tests

## Status

**Phase 3.3 Admin Router Cleanup**: ✅ **COMPLETE**

Next: Phase 3.3 Email Uniqueness Enforcement (T042-T045) - Optional refinements
