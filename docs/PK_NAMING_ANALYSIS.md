# Primary Key Naming Pattern Analysis

**Date**: 2025-10-21  
**Analysis**: Checking consistency between `id` vs `<tablename>_id` patterns

---

## Current State (Database Schema)

| Table | PK Column | Pattern | Model Class | Model PK Field |
|-------|-----------|---------|-------------|----------------|
| tenants | tenant_id | ✅ `{table}_id` | TenantModel | tenant_id ✅ |
| users | user_id | ✅ `{table}_id` | UserModel | user_id ✅ |
| **roles** | **MISSING** | N/A | RoleModel | **id** 🔴 |
| user_roles | (user_id, role_id) | Composite PK | UserRoleModel | (user_id, role_id) ⚠️ |
| user_details | user_id | ✅ `{table}_id` (FK) | UserDetailsModel | user_id ✅ |
| user_mfa | (user_id, factor_type) | Composite PK | UserMFAModel | (user_id, factor_type) ✅ |
| invitations | invitation_id | ✅ `{table}_id` | InvitationModel | invitation_id ✅ |
| password_reset_requests | reset_id | ⚠️ Abbreviated | PasswordResetRequestModel | reset_id ⚠️ |
| policies | policy_id | ✅ `{table}_id` | PolicyModel | policy_id ✅ |
| policy_evaluation_logs | eval_id | ⚠️ Abbreviated | PolicyEvaluationLogModel | eval_id ⚠️ |
| audit_events | event_id | ✅ `{table}_id` | AuditEventModel | event_id ✅ |
| feature_flags | flag_id | ⚠️ Abbreviated | FeatureFlagModel | flag_id ⚠️ |
| key_rotation_records | key_version | ⚠️ Special case | KeyRotationRecordModel | key_version ⚠️ |
| token_replay_records | jti | ⚠️ JWT ID | (No model in models.py) | N/A |
| schema_version | version | ⚠️ Metadata table | (No model) | N/A |

---

## Pattern Analysis

### ✅ **Full Pattern**: `{table_name}_id` (8 tables)
- tenants → **tenant_id**
- users → **user_id**
- invitations → **invitation_id**
- policies → **policy_id**
- audit_events → **event_id**

**Consistency**: Models match database schema ✅

---

### ⚠️ **Abbreviated Pattern**: Short name + `_id` (3 tables)
- password_reset_requests → **reset_id** (not password_reset_request_id)
- policy_evaluation_logs → **eval_id** (not policy_evaluation_log_id)
- feature_flags → **flag_id** (not feature_flag_id)

**Rationale**: Avoid excessively long column names  
**Consistency**: Models match database schema ✅

---

### ⚠️ **Special Cases** (3 tables)
- key_rotation_records → **key_version** (sequential integer, not UUID)
- token_replay_records → **jti** (JWT ID standard, string not UUID)
- schema_version → **version** (semantic version string)

**Rationale**: Domain-specific identifiers  
**Consistency**: Appropriate for use case ✅

---

### 🔴 **INCONSISTENCY**: roles table

**Current model (RoleModel)**:
```python
class RoleModel(Base):
    __tablename__ = "roles"
    id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
```

**Expected pattern**: `role_id` (to match project convention)

**Issue**: 
- Using generic `id` breaks naming consistency
- Creates confusion with `roles.id` vs `users.user_id`, `tenants.tenant_id`
- Foreign keys reference `roles.id` instead of `roles.role_id`

---

## Impact Analysis

### 1. Foreign Key References to roles.id

| From Table | Column | References |
|------------|--------|------------|
| user_roles | role_id | **roles.id** 🔴 |
| roles | created_by | users.user_id ✅ |
| roles | updated_by | users.user_id ✅ |
| roles | tenant_id | tenants.tenant_id ✅ |

**Inconsistency**: `user_roles.role_id` references `roles.id`, not `roles.role_id`

### 2. Code References

**UserRoleModel** (models.py line 226):
```python
role_id: Mapped[UUID] = mapped_column(
    PortableUUID(),
    ForeignKey("roles.id", ondelete="CASCADE"),  # 🔴 References roles.id
    primary_key=True
)
```

**Test expectations** (test_role_api.py line 18):
```python
SYSTEM_ROLE_IDS = {
    "superadmin": UUID("00000000-0000-0000-0000-000000000001"),
    "tenant_admin": UUID("00000000-0000-0000-0000-000000000002"),
    "user": UUID("00000000-0000-0000-0000-000000000003")
}
```

Tests use `.json()["id"]` to extract role ID, expecting field name `id`.

---

## Recommendations

### Option 1: Keep `roles.id` (Minimal Changes) ✅ **RECOMMENDED**

**Rationale**:
- Tests already expect `id` field name
- Migration 0c34fb45b7a8 already uses `id`
- Changing to `role_id` requires updating:
  - 3 migration files
  - RoleModel class
  - UserRoleModel FK reference
  - All role-related tests (20+ files)
  - API response schemas
  - OpenAPI contracts

**Consistency trade-off**: Accept one exception for `roles.id` to avoid massive refactoring

**Document the exception**:
```python
class RoleModel(Base):
    """
    Role entity (FR-122: Role Management & Hierarchy).
    
    NOTE: Uses 'id' instead of 'role_id' to avoid excessively long
    composite FK names (e.g., user_roles.role_id -> roles.role_id).
    This is consistent with common practice for junction tables.
    """
    __tablename__ = "roles"
    id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
```

---

### Option 2: Rename to `role_id` (Full Consistency)

**Changes required**:
1. Update RoleModel: `id` → `role_id`
2. Update UserRoleModel FK: `ForeignKey("roles.id")` → `ForeignKey("roles.role_id")`
3. Update migration 0c34fb45b7a8: Column name `id` → `role_id`
4. Update migration 6972634478c6: FK reference
5. Update all tests expecting `.json()["id"]` → `.json()["role_id"]`
6. Update API schemas (20+ files)
7. Update OpenAPI contracts

**Estimated effort**: 2-3 hours of changes + full regression testing

**Risk**: High chance of breaking tests and contracts

---

## Decision

### ✅ **KEEP `roles.id`** (Option 1)

**Final Pattern Summary**:
- **Standard tables**: `{table}_id` (tenants, users, invitations, policies, audit_events)
- **Abbreviated tables**: `{short_name}_id` (reset_id, eval_id, flag_id)
- **Special case - roles**: `id` (junction table optimization)
- **Special identifiers**: key_version, jti, version

**Accepted trade-off**: One exception (`roles.id`) is acceptable given:
1. Matches existing migrations and tests
2. Common pattern for junction table PKs
3. Avoids `user_roles.role_id -> roles.role_id` redundancy
4. Minimal cognitive overhead

---

## Updated PK/FK Analysis Corrections

### user_details Audit Fields

**Current analysis stated**: "user_details.created_by and updated_by are NOT NULL"

**CORRECTION - Models.py shows**:
```python
created_by: Mapped[Optional[UUID]] = mapped_column(
    PortableUUID(),
    ForeignKey("users.user_id", ondelete="SET NULL"),
    nullable=True  # ✅ NULLABLE in model
)
```

**Database schema shows**: NOT NULL constraint

**Root cause**: Migration `20251017_0645_5b0206f95039_add_user_details_table.py` incorrectly set NOT NULL:
```python
sa.Column('created_by', sa.UUID(), nullable=False, comment='User who created the record'),
sa.Column('updated_by', sa.UUID(), nullable=False, comment='User who last updated the record'),
```

**Fix required**: Consolidated migration must use `nullable=True` for audit fields (matches current model)

---

## Consolidated Migration Adjustments

### 1. roles table
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY,  -- ✅ Keep 'id' not 'role_id'
    name VARCHAR(100) NOT NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT unique_role_name_per_tenant UNIQUE (name, tenant_id)
);
```

### 2. user_details audit fields
```sql
CREATE TABLE user_details (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    photo_display_url VARCHAR(512),
    photo_thumbnail_url VARCHAR(512),
    photo_avatar_url VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,  -- ✅ NULLABLE
    updated_by UUID REFERENCES users(user_id) ON DELETE SET NULL   -- ✅ NULLABLE
);
```

### 3. Constraint naming (standardize user_details)
```sql
-- Primary key
CONSTRAINT user_details_pkey PRIMARY KEY (user_id)  -- Not pk_user_details

-- Foreign keys
CONSTRAINT user_details_user_id_fkey FOREIGN KEY (user_id) ...  -- Not fk_user_details_user_id
CONSTRAINT user_details_created_by_fkey FOREIGN KEY (created_by) ...
CONSTRAINT user_details_updated_by_fkey FOREIGN KEY (updated_by) ...
```

---

## Testing Validation

After consolidated migration, verify:

- [ ] `SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'roles' AND column_name = 'id'` → Returns `id`, `NO`
- [ ] `SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'user_details' AND column_name = 'created_by'` → Returns `created_by`, `YES`
- [ ] Tests reference `role["id"]` not `role["role_id"]`
- [ ] FK: `user_roles.role_id → roles.id` exists
- [ ] All constraint names follow pattern (no `pk_*` or `fk_*` prefixes)
