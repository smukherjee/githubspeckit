# Seed Script Fix for V1.0 Role Management

**Date**: October 21, 2025  
**Issue**: Seed script failed with UUID validation error  
**Status**: ✅ FIXED  

## Problem

The seed script `scripts/seed_infysight.py` was trying to assign role **names** (strings like "superadmin", "tenant_admin", "user") to users, but the new V1.0 schema uses a separate `user_roles` junction table with `role_id` as a UUID foreign key to `roles.id`.

### Error Message
```
sqlalchemy.exc.DBAPIError: invalid input for query argument $2: 'superadmin' 
(invalid UUID 'superadmin': length must be between 32..36 characters, got 10)
[SQL: INSERT INTO user_roles (user_id, role_id, assigned_at, assigned_by) 
VALUES ($1::UUID, $2::UUID, $3::TIMESTAMP WITH TIME ZONE, $4::UUID)]
```

### Root Cause

**OLD Behavior** (Pre-FR-122):
- User domain model had `roles: List[str]` field with role names
- Persistence layer stored role names directly
- No separate `roles` table

**NEW Behavior** (V1.0 with FR-122):
- `roles` table stores role definitions with UUID primary key (`id`)
- `user_roles` junction table links users to roles via UUIDs
- User domain model still has `roles: List[str]` but now these must be role **UUIDs** not names

The seed script was still passing role **names** like `["superadmin"]` instead of role **UUIDs** like `["00000000-0000-0000-0000-000000000001"]`.

## Solution

Updated `scripts/seed_infysight.py` to:

### 1. Query System Role UUIDs
```python
# Get system role UUIDs by name (FR-122)
from sqlalchemy import text
role_uuid_query = text("""
    SELECT id, name FROM roles 
    WHERE is_system = true AND name IN ('superadmin', 'tenant_admin', 'user')
""")
role_result = await session.execute(role_uuid_query)
role_uuid_map = {row[1]: str(row[0]) for row in role_result.all()}
# Result: {'superadmin': '00000000-0000-0000-0000-000000000001', ...}
```

### 2. Use Role UUIDs in User Creation
```python
users_to_create = [
    {
        "user_id": superadmin_id,
        "email": "infysightsa@infysight.com",
        "roles": [role_uuid_map["superadmin"]],  # UUID not name ✅
        "role_names": ["superadmin"],  # For logging only
        "password_hash": superadmin_password,
        "full_name": "InfySight Superadmin"
    },
    # ... tenant_admin, user
]
```

### 3. Validation
Added check to ensure all 3 system roles exist:
```python
if len(role_uuid_map) != 3:
    logger.error("missing_system_roles", 
               found=list(role_uuid_map.keys()),
               expected=["superadmin", "tenant_admin", "user"])
    raise RuntimeError(f"Expected 3 system roles, found {len(role_uuid_map)}")
```

## Verification

### Test Users Created
```sql
SELECT user_id, email, status FROM users;
```
**Result**:
- ✅ infysightsa@infysight.com (active)
- ✅ infysightadmin@infysight.com (active)
- ✅ infysightuser@infysight.com (active)

### Role Assignments
```sql
SELECT ur.user_id, u.email, r.name as role_name 
FROM user_roles ur 
JOIN users u ON ur.user_id = u.user_id 
JOIN roles r ON ur.role_id = r.id 
ORDER BY u.email;
```
**Result**:
- ✅ infysightadmin@infysight.com → tenant_admin
- ✅ infysightsa@infysight.com → superadmin
- ✅ infysightuser@infysight.com → user

### User Details
```sql
SELECT user_id, full_name FROM user_details ORDER BY full_name;
```
**Result**:
- ✅ InfySight Standard User
- ✅ InfySight Superadmin
- ✅ InfySight Tenant Admin

## Test Credentials

All users created with deterministic UUIDs and test passwords:

### Superadmin
```json
{
  "email": "infysightsa@infysight.com",
  "password": "infysightsa123",
  "roles": ["superadmin"],
  "tenant": "infysight",
  "user_id": "a5053ec7-a656-53ef-98c4-8713a68b2b9b",
  "tenant_id": "c79911ec-beb1-5c45-833d-4a9847b88024"
}
```

### Tenant Admin
```json
{
  "email": "infysightadmin@infysight.com",
  "password": "infysightadmin123",
  "roles": ["tenant_admin"],
  "tenant": "infysight",
  "user_id": "8146c7c0-27c1-555f-87f2-00bc403e7ff6",
  "tenant_id": "c79911ec-beb1-5c45-833d-4a9847b88024"
}
```

### Standard User
```json
{
  "email": "infysightuser@infysight.com",
  "password": "infysightuser123",
  "roles": ["user"],
  "tenant": "infysight",
  "user_id": "f933db58-9ac1-56e8-af7d-cb8484b26346",
  "tenant_id": "c79911ec-beb1-5c45-833d-4a9847b88024"
}
```

## Database State

### Tenants: 1
- infysight (active)

### Users: 3
- superadmin (infysightsa@infysight.com)
- tenant_admin (infysightadmin@infysight.com)
- user (infysightuser@infysight.com)

### User Roles: 3
All assignments use proper UUID foreign keys to `roles.id`:
- User a5053ec7... → Role 00000000-0000-0000-0000-000000000001 (superadmin)
- User 8146c7c0... → Role 00000000-0000-0000-0000-000000000002 (tenant_admin)
- User f933db58... → Role 00000000-0000-0000-0000-000000000003 (user)

### User Details: 3
All users have full_name populated

## Running the Seed Script

```bash
# Activate virtual environment
source .venv/bin/activate

# Run seed script (idempotent - safe to run multiple times)
python scripts/seed_infysight.py

# Expected output:
✅ system_roles_loaded (roles={'superadmin': '...001', 'tenant_admin': '...002', 'user': '...003'})
✅ tenant_created (tenant_id=c79911ec-beb1-5c45-833d-4a9847b88024, name=infysight)
✅ user_created (user_id=a5053ec7..., email=infysightsa@infysight.com, roles=['superadmin'])
✅ user_created (user_id=8146c7c0..., email=infysightadmin@infysight.com, roles=['tenant_admin'])
✅ user_created (user_id=f933db58..., email=infysightuser@infysight.com, roles=['user'])
✅ user_details_created (user_id=a5053ec7..., full_name=InfySight Superadmin)
✅ user_details_created (user_id=8146c7c0..., full_name=InfySight Tenant Admin)
✅ user_details_created (user_id=f933db58..., full_name=InfySight Standard User)
✅ seed_complete (users_created=3)
```

## Impact on Tests

Tests that depend on seeded data should now work correctly:
- Authentication tests (login with test credentials)
- RBAC tests (role-based access control)
- User profile tests (user_details table populated)
- Tenant isolation tests (all users in infysight tenant)

## Related Changes

- **Migration**: `alembic/versions/20251021_0000_v1_0_0_consolidated_schema.py` (seeds 3 system roles)
- **Domain Model**: `src/domain/users/models.py` (User.roles is List[str] of UUIDs)
- **Persistence**: `src/adapters/persistence/repositories.py` (SQLAlchemyUserRepository._update_roles)
- **Database Schema**: `user_roles` table with UUID role_id FK to roles.id

## Next Steps

1. ✅ **Seed script fixed** - Database ready for testing
2. ⏳ **Run test suite** - Validate all tests pass with seeded data
3. ⏳ **Docker testing** - Ensure seed script runs in containerized environment
4. 📝 **Document credentials** - Add to README/CONTRIBUTING for developers

---

**Status**: ✅ COMPLETE  
**Database**: Seeded with 1 tenant, 3 users, 3 role assignments, 3 user details  
**Credentials**: All test users have deterministic UUIDs and known passwords
