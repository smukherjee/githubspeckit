# Primary Key and Foreign Key Analysis

**Date**: 2025-10-21  
**Database**: infysight_users (current state at revision 3da4ba72b3b5)  
**Purpose**: Identify inconsistencies before consolidating migrations

---

## Summary of Issues Found

### 🔴 CRITICAL ISSUES

1. **Missing `roles` table** - Database is missing the `roles` table entirely (migration 0c34fb45b7a8 not applied)
2. **user_roles.role_id type mismatch** - Current: `VARCHAR(50)`, Expected: `UUID` (FK to roles.id)
3. **user_roles missing audit fields** - No `assigned_at`, `assigned_by` columns

### 🟡 INCONSISTENCIES

4. **Inconsistent PK naming** - Mix of `{table}_pkey` and `pk_{table}` patterns
5. **Inconsistent FK naming** - Mix of `{table}_{column}_fkey` and `fk_{table}_{column}` patterns

---

## Detailed Analysis

### 1. Primary Keys

| Table | PK Column(s) | Constraint Name | Type | Status |
|-------|-------------|-----------------|------|--------|
| tenants | tenant_id | tenants_pkey | UUID | ✅ Consistent |
| users | user_id | users_pkey | UUID | ✅ Consistent |
| **user_roles** | user_id, role_id | user_roles_pkey | UUID, VARCHAR(50) | 🔴 **role_id should be UUID** |
| user_details | user_id | pk_user_details | UUID | 🟡 Different naming pattern |
| user_mfa | user_id, factor_type | user_mfa_pkey | UUID, ENUM | ✅ Consistent |
| invitations | invitation_id | invitations_pkey | UUID | ✅ Consistent |
| password_reset_requests | reset_id | password_reset_requests_pkey | UUID | ✅ Consistent |
| policies | policy_id | policies_pkey | UUID | ✅ Consistent |
| policy_evaluation_logs | eval_id | policy_evaluation_logs_pkey | UUID | ✅ Consistent |
| feature_flags | flag_id | feature_flags_pkey | UUID | ✅ Consistent |
| audit_events | event_id | audit_events_pkey | UUID | ✅ Consistent |
| key_rotation_records | key_version | key_rotation_records_pkey | INTEGER | ✅ Consistent (auto-increment) |
| token_replay_records | jti | token_replay_records_pkey | VARCHAR(255) | ✅ Consistent (JWT ID) |
| schema_version | version | schema_version_pkey | VARCHAR(20) | ✅ Consistent |
| **roles** | id | N/A | UUID | 🔴 **TABLE MISSING** |

**PK Naming Inconsistency**:
- Pattern 1: `{table}_pkey` (13 tables) ← **Standard**
- Pattern 2: `pk_{table}` (1 table: user_details) ← **Non-standard**

---

### 2. Foreign Keys

#### 2.1 Tenant Isolation FKs (All point to tenants.tenant_id)

| From Table | Column | Constraint Name | ON DELETE | Status |
|------------|--------|-----------------|-----------|--------|
| users | tenant_id | users_tenant_id_fkey | CASCADE | ✅ |
| invitations | tenant_id | invitations_tenant_id_fkey | CASCADE | ✅ |
| policies | tenant_id | policies_tenant_id_fkey | CASCADE | ✅ |
| feature_flags | tenant_id | feature_flags_tenant_id_fkey | CASCADE | ✅ |

**Pattern**: `{table}_tenant_id_fkey` ← Consistent ✅

---

#### 2.2 User-Related FKs (Point to users.user_id)

| From Table | Column | Constraint Name | ON DELETE | Status |
|------------|--------|-----------------|-----------|--------|
| user_roles | user_id | user_roles_user_id_fkey | CASCADE | ✅ |
| user_mfa | user_id | user_mfa_user_id_fkey | CASCADE | ✅ |
| password_reset_requests | user_id | password_reset_requests_user_id_fkey | CASCADE | ✅ |
| user_details | user_id | fk_user_details_user_id | CASCADE | 🟡 Different pattern |
| user_details | created_by | fk_user_details_created_by | NO ACTION | 🟡 Different pattern |
| user_details | updated_by | fk_user_details_updated_by | NO ACTION | 🟡 Different pattern |

**Patterns**:
- Standard: `{table}_user_id_fkey` (3 tables)
- Non-standard: `fk_{table}_{column}` (user_details only)

---

#### 2.3 Policy FKs

| From Table | Column | Constraint Name | ON DELETE | Status |
|------------|--------|-----------------|-----------|--------|
| policy_evaluation_logs | policy_id | policy_evaluation_logs_policy_id_fkey | CASCADE | ✅ |

**Pattern**: `{table}_policy_id_fkey` ← Consistent ✅

---

#### 2.4 Role FKs (🔴 BROKEN)

| From Table | Column | Constraint Name | Referenced Table | Status |
|------------|--------|-----------------|------------------|--------|
| **user_roles** | role_id | **NONE** | **roles.id (MISSING TABLE)** | 🔴 **No FK constraint** |

**Critical Issue**: 
- `user_roles.role_id` is `VARCHAR(50)` with NO foreign key constraint
- Expected: FK to `roles.id` (UUID) with ON DELETE CASCADE
- Root cause: `roles` table migration (0c34fb45b7a8) not applied yet

---

### 3. Data Type Consistency

#### 3.1 UUID Columns (Primary/Foreign Keys)

All UUID columns use `uuid` PostgreSQL type ✅

**Exception**: 
- 🔴 `user_roles.role_id` is `VARCHAR(50)` (should be UUID)

#### 3.2 Audit Metadata Columns

| Table | created_at | updated_at | created_by | updated_by |
|-------|------------|------------|------------|------------|
| tenants | timestamptz | timestamptz | uuid (nullable) | uuid (nullable) |
| users | timestamptz | timestamptz | uuid (nullable) | uuid (nullable) |
| user_details | timestamptz | timestamptz | uuid (NOT NULL) | uuid (NOT NULL) |
| policies | timestamptz | timestamptz | uuid (nullable) | uuid (nullable) |
| feature_flags | timestamptz | timestamptz | uuid (nullable) | uuid (nullable) |
| key_rotation_records | timestamptz | - | uuid (nullable) | - |

**Inconsistency**: 
- 🟡 user_details.created_by and updated_by are NOT NULL (all others nullable)
- This may cause issues during bootstrap (no user exists yet)

---

### 4. Missing Tables

| Table | Migration File | Revision | Status |
|-------|----------------|----------|--------|
| roles | 20251020_1747_0c34fb45b7a8_create_roles_table.py | 0c34fb45b7a8 | 🔴 NOT APPLIED |

**Current DB revision**: `3da4ba72b3b5` (add_schema_version_metadata_table)  
**Missing revisions**: 0c34fb45b7a8, 6972634478c6, 31a51a6816b1 (all role-related)

---

### 5. Missing Columns in Existing Tables

#### user_roles table
**Current columns**:
- user_id (uuid)
- role_id (varchar(50)) 🔴

**Expected columns** (from RoleModel/UserRoleModel):
- user_id (uuid) ✅
- role_id (uuid) 🔴 TYPE MISMATCH
- assigned_at (timestamptz) 🔴 MISSING
- assigned_by (uuid, nullable) 🔴 MISSING

---

## Recommendations for Consolidated Migration

### 1. Drop and Recreate user_roles Table
The existing `user_roles` table is incompatible:
```sql
-- Drop old user_roles (no data loss concern - table is empty or has invalid data)
DROP TABLE IF EXISTS user_roles CASCADE;

-- Recreate with correct schema
CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID,
    CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id),
    CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) 
        REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT user_roles_assigned_by_fkey FOREIGN KEY (assigned_by) 
        REFERENCES users(user_id) ON DELETE SET NULL
);
```

### 2. Standardize Constraint Naming

**Adopt pattern**: `{table}_{column}_fkey` for all FKs

**Fix user_details FKs**:
- Rename `fk_user_details_user_id` → `user_details_user_id_fkey`
- Rename `fk_user_details_created_by` → `user_details_created_by_fkey`
- Rename `fk_user_details_updated_by` → `user_details_updated_by_fkey`

**Fix user_details PK**:
- Rename `pk_user_details` → `user_details_pkey`

### 3. Fix user_details Audit Field Nullability

Change `created_by` and `updated_by` to nullable:
```sql
ALTER TABLE user_details 
    ALTER COLUMN created_by DROP NOT NULL,
    ALTER COLUMN updated_by DROP NOT NULL;
```

### 4. Add Missing Indexes for user_roles

Per FR-122 spec:
```sql
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

---

## Migration Order for Consolidated Schema

1. ✅ All existing tables (tenants, users, etc.)
2. ✅ Fix user_details audit field nullability
3. ✅ Fix user_details constraint naming
4. 🆕 **Create roles table BEFORE user_roles**
5. 🆕 **Drop old user_roles table**
6. 🆕 **Recreate user_roles with correct schema**
7. 🆕 **Seed 3 system roles** (superadmin, tenant_admin, user)

---

## Testing Checklist

- [ ] All 15 tables exist (including roles)
- [ ] user_roles.role_id is UUID type
- [ ] FK: user_roles.role_id → roles.id exists
- [ ] FK: user_roles.user_id → users.user_id exists
- [ ] All constraint names follow `{table}_{column}_fkey` pattern
- [ ] user_details.created_by is nullable
- [ ] 3 system roles seeded with fixed UUIDs
- [ ] All tests pass (especially test_migration_smoke.py)

---

## Fixed UUID Values for System Roles

Per migration `31a51a6816b1_seed_system_roles.py`:

```python
SUPERADMIN_ROLE_ID = '00000000-0000-0000-0000-000000000001'
TENANT_ADMIN_ROLE_ID = '00000000-0000-0000-0000-000000000002'  
USER_ROLE_ID = '00000000-0000-0000-0000-000000000003'
```

These UUIDs **MUST** be used in the consolidated migration to match test expectations.
