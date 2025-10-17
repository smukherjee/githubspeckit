# Database Migration Consolidation - v1.0.0 Release

**Date**: October 17, 2025  
**Status**: ✅ COMPLETE

## Summary

All Alembic migrations have been consolidated into a single base migration for the v1.0.0 release. Both SQLite and PostgreSQL databases have been dropped, recreated, and seeded with identical data.

## Consolidated Migrations

### Previous Migrations (Removed)
1. **9f85fdd0f4d0**: Initial schema baseline
   - Created all core tables (tenants, users, policies, audit_events, etc.)
   - Established indexes and foreign keys
   
2. **8c01924a527d**: Add token_replay_records table
   - JWT replay protection (FR-SEC-020, IMPL-DB-11)
   - Globally unique JTI tracking
   
3. **94da136ac201**: Remove audit_events FK constraints
   - Audit integrity principle (no FK constraints block audit logging)
   - Database-agnostic implementation (PostgreSQL + SQLite)

### New Base Migration
- **v1_0_0_base** (20251017_1020_v1_0_0_base_schema.py)
  - Combines all three migrations into single base schema
  - Creates 13 tables total
  - Clean migration history for v1.0 release

## Database Tables (13)

| Table | Purpose | FK Constraints |
|-------|---------|----------------|
| tenants | Multi-tenant root entity | None |
| users | Tenant-scoped user accounts | → tenants |
| user_roles | User-to-role associations | → users |
| invitations | Pending user invitations | → tenants |
| password_reset_requests | Password reset tokens | → users |
| policies | Authorization policies | → tenants |
| policy_evaluation_logs | Policy evaluation audit | → policies |
| **audit_events** | Compliance audit log | **NO FK** |
| feature_flags | Feature toggles | → tenants |
| key_rotation_records | Signing key lifecycle | None |
| user_mfa | MFA enrollment (deferred) | → users |
| token_replay_records | JWT replay detection | None |
| alembic_version | Schema version tracking | None |

**Note**: `audit_events` has NO foreign key constraints to ensure audit integrity (never block operations).

## Database Recreations

### SQLite (dev.db)
```bash
# Removed old database
rm -f *.db

# Created new database
DATABASE_URL="sqlite+aiosqlite:///./dev.db" alembic upgrade head
```

**Result**: ✅ Migration v1_0_0_base applied successfully

### PostgreSQL (infysight_users)
```bash
# Terminated connections
psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'infysight_users';"

# Dropped and recreated database
psql -d postgres -c "DROP DATABASE infysight_users;"
psql -d postgres -c "CREATE DATABASE infysight_users OWNER infysight_dbadmin;"

# Applied migration
DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users" alembic upgrade head
```

**Result**: ✅ Migration v1_0_0_base applied successfully

## Seed Data (Identical in Both Databases)

Both databases seeded using `scripts/seed_infysight.py` with deterministic UUIDs:

### Tenant
- **ID**: `c79911ec-beb1-5c45-833d-4a9847b88024`
- **Name**: `infysight`
- **Status**: `active`

### User
- **ID**: `a5053ec7-a656-53ef-98c4-8713a68b2b9b`
- **Tenant ID**: `c79911ec-beb1-5c45-833d-4a9847b88024`
- **Email**: `infysightsa@infysight.com`
- **Status**: `active`
- **Role**: `superadmin`
- **Password**: `infysightsa123`

### Verification Queries

**PostgreSQL**:
```sql
SELECT tenant_id, name, status FROM tenants;
-- c79911ec-beb1-5c45-833d-4a9847b88024 | infysight | active

SELECT user_id, email, status FROM users;
-- a5053ec7-a656-53ef-98c4-8713a68b2b9b | infysightsa@infysight.com | active

SELECT user_id, role_id FROM user_roles;
-- a5053ec7-a656-53ef-98c4-8713a68b2b9b | superadmin

SELECT version_num FROM alembic_version;
-- v1_0_0_base
```

**SQLite**:
```sql
-- Identical results (same UUIDs, same data)
SELECT version_num FROM alembic_version;
-- v1_0_0_base
```

## Verification Results

✅ **Schema Consistency**: Both databases have identical table structures  
✅ **Data Consistency**: Both databases have identical seed data (same UUIDs)  
✅ **Migration Version**: Both databases at `v1_0_0_base`  
✅ **Table Count**: Both have 13 tables (+ alembic_version)  

## Git Commit

**Commit**: `bbc3001`  
**Message**: `feat: consolidate migrations into v1.0.0 base schema`

**Changes**:
- ✅ Deleted 2 old migration files
- ✅ Renamed/rewrote initial migration as v1.0.0 base
- ✅ Net reduction: 34 lines (100 insertions, 134 deletions)

## Benefits of Consolidation

1. **Clean History**: Single base migration easier to understand and maintain
2. **Faster Deployment**: One migration file to apply instead of three
3. **Reduced Complexity**: No migration dependencies to track
4. **Better Documentation**: Consolidated migration documents full schema
5. **Easier Rollback**: Single downgrade() function for full schema removal

## Next Steps

- ✅ Both databases ready for development
- ✅ Superadmin credentials available for testing
- ✅ Clean migration history for v1.0 release
- ✅ Production-ready schema baseline

## Login Credentials

**Superadmin Account**:
- Email: `infysightsa@infysight.com`
- Password: `infysightsa123`
- Role: `superadmin`
- Tenant: `infysight`

Use these credentials to log in to the API or frontend application.
