# Database Synchronization Check Report
**Date**: October 17, 2025  
**Feature**: 003-user-profile-details

## Summary

Both databases have the same migration version (**56ba10e5592d**) which includes:
- v1.0.0 base schema
- User details table (5b0206f95039)
- Audit events FK constraints removal (94da136ac201)
- Merge migration (56ba10e5592d)

However, the **seed data is out of sync**.

## Database Status

### SQLite (test.db)

**Migration Version**: ✅ 56ba10e5592d  
**Location**: `./test.db`  
**Usage**: Integration tests

**Tables**:
- ✅ tenants: 1 record
- ✅ users: 3 records
- ✅ user_roles: 3 records
- ✅ user_details: 0 records ⚠️
- ✅ audit_events: 0 records

**Users**:
1. `infysightsa@infysight.com` (superadmin) - id: a5053ec7-a656-53ef-98c4-8713a68b2b9b
2. `infysightadmin@infysight.com` (tenant_admin) - id: 8146c7c0-27c1-555f-87f2-00bc403e7ff6
3. `infysightuser@infysight.com` (user) - id: f933db58-9ac1-56e8-af7d-cb8484b26346

**User Details**: ⚠️ **0 records** (should have at least superadmin profile)

**Issues**:
- ❌ Missing user_details record for superadmin
- ⚠️ Test users created but no profiles

---

### PostgreSQL (githubspeckit_test)

**Migration Version**: ✅ 56ba10e5592d  
**Connection**: `postgresql+asyncpg://infysight_dbadmin:***@localhost/githubspeckit_test`  
**Usage**: Integration tests (PostgreSQL)

**Tables**:
- ✅ tenants: 2 records
- ✅ users: 1 record
- ✅ user_roles: 1 record
- ✅ user_details: 1 record ✅
- ✅ audit_events: 0 records

**Users**:
1. `infysightsa@infysight.com` (superadmin) - id: a5053ec7-a656-53ef-98c4-8713a68b2b9b

**User Details**: ✅ **1 record**
- InfySight Superadmin (id: a5053ec7-a656-53ef-98c4-8713a68b2b9b)

**Issues**:
- ❌ Missing tenant_admin and regular user (only superadmin present)
- ℹ️ Extra tenant (2 instead of 1)

---

## Sync Issues

### 1. User Count Mismatch
- **SQLite**: 3 users
- **PostgreSQL**: 1 user
- **Impact**: Test fixtures may fail on PostgreSQL when expecting infysightadmin/infysightuser

### 2. User Details Mismatch
- **SQLite**: 0 user_details records
- **PostgreSQL**: 1 user_details record
- **Impact**: Profile tests will fail on SQLite

### 3. Tenant Count Mismatch
- **SQLite**: 1 tenant
- **PostgreSQL**: 2 tenants
- **Impact**: Unknown why PostgreSQL has 2 tenants

---

## Root Causes

### SQLite Issues
1. **User details not created**: The seed script (`scripts/seed_infysight.py`) successfully creates user_details for PostgreSQL but not for SQLite
2. **Test users created by tests**: The extra users (infysightadmin, infysightuser) are created by test fixtures in `tests/conftest.py`, not by the seed script
3. **Photo upload issue**: Background task creates user_details but doesn't commit to SQLite properly

### PostgreSQL Issues
1. **Only superadmin seeded**: The seed script only creates one user (infysightsa)
2. **Missing test users**: Tests expecting infysightadmin/infysightuser will fail on PostgreSQL

---

## Recommendations

### Immediate Actions

1. **Update SQLite**: Run seed script to create user_details for superadmin
   ```bash
   source .venv/bin/activate
   python scripts/seed_infysight.py
   ```

2. **Seed PostgreSQL with all test users**: Modify seed script to create all 3 test users:
   - infysightsa@infysight.com (superadmin)
   - infysightadmin@infysight.com (tenant_admin)
   - infysightuser@infysight.com (user)

3. **Fix background task session handling**: The photo upload background task isn't committing to SQLite properly (needs investigation)

### Long-term Solutions

1. **Unified seed script**: Create a seed script that works identically for both SQLite and PostgreSQL
2. **Database fixtures**: Use pytest fixtures to ensure consistent test data
3. **Migration tests**: Add tests to verify migrations produce identical schemas on both databases
4. **Seed verification**: Add post-seed checks to verify all expected data exists

---

## Next Steps

1. ✅ Run sync check script: `python scripts/check_db_sync.py`
2. ⏳ Update seed script to create all 3 users
3. ⏳ Re-seed both databases
4. ⏳ Verify sync with check script
5. ⏳ Fix background task session issue
6. ⏳ Add automated sync checks to CI/CD

---

## Test Impact

### Currently Passing Tests (25/28)
All tests use SQLite by default, which has the 3 seeded users but missing user_details.

### Tests That May Fail on PostgreSQL
- Any test expecting `infysightadmin` or `infysightuser` 
- Tests requiring multiple tenants
- RBAC tests that check cross-tenant access

### Photo Upload Tests
- ✅ 2/3 passing on SQLite (with file storage working)
- ❌ User details not being persisted to SQLite after background processing
- ✅ Should work on PostgreSQL (has user_details table properly configured)

---

## Files to Update

1. `scripts/seed_infysight.py` - Add admin and regular user creation
2. `tests/conftest.py` - Ensure seeded_database fixture creates user_details
3. `src/adapters/api/routers/profile.py` - Fix background task session handling
4. `.github/workflows/*.yml` - Add database sync checks to CI

---

## Schema Verification

Both databases have identical schemas ✅:

**user_details table**:
- user_id (UUID, PK, FK to users)
- full_name (VARCHAR(100))
- phone (VARCHAR(20))
- address (TEXT)
- photo_display_url (VARCHAR(512))
- photo_thumbnail_url (VARCHAR(512))
- photo_avatar_url (VARCHAR(512))
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- created_by (UUID, FK to users)
- updated_by (UUID, FK to users)

**Indexes**: created_at, updated_at ✅  
**Foreign Keys**: user_id, created_by, updated_by ✅
