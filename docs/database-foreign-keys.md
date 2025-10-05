# Foreign Key Cascade Policies

**Document**: IMPL-DB-FK-02  
**Phase**: 3 (Persistence Layer)  
**Related**: FR-002 (tenant isolation), FR-018 (soft delete), FR-077 (audit metadata)

## Overview

This document describes all foreign key constraints and their `ON DELETE` policies in the database schema. The design follows these principles:

1. **CASCADE for ephemeral/association tables**: Short-lived records (tokens, invitations) or association tables (user_roles) CASCADE delete with their parent.
2. **CASCADE for tenant-scoped entities**: Users, policies, feature flags CASCADE when tenant deleted (physical deletion only).
3. **SET NULL for audit trails**: Audit events preserve history even after referenced entities are deleted.
4. **Soft delete does NOT trigger cascades**: Soft delete is a status field change; physical FK constraints remain inactive.

## Foreign Key Constraints by Table

### 1. `users` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `tenant_id` | `tenants.tenant_id` | `CASCADE` | Users are tenant-scoped; orphaned users not allowed. Physical tenant deletion cascades to users. Soft delete (status='soft_deleted') does NOT trigger cascade. |

**Dependent Tables (CASCADE to `users`)**:
- `user_roles`: Association table; roles orphaned when user deleted
- `password_reset_requests`: Ephemeral tokens; no value after user deletion
- `user_mfa`: MFA credentials are user-specific secrets; must not persist

### 2. `user_roles` Table (Association)

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `user_id` | `users.user_id` | `CASCADE` | Association table; no orphaned role assignments allowed |

**Notes**:
- This is a many-to-many association table.
- `role_id` is a string enum (not FK to a roles table); represents logical role identifiers.

### 3. `invitations` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `tenant_id` | `tenants.tenant_id` | `CASCADE` | Invitations are ephemeral; no value if tenant deleted. Physical deletion cascades invitations. |

**Notes**:
- Invitations expire after 7 days (configurable).
- Physical tenant deletion removes all pending invitations.

### 4. `password_reset_requests` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `user_id` | `users.user_id` | `CASCADE` | Password reset tokens are ephemeral; tied to user lifecycle. Must be deleted when user deleted. |

**Notes**:
- Tokens expire after 1 hour (configurable via `PASSWORD_RESET_TTL_MINUTES`).
- Physical user deletion cascades all password reset requests.

### 5. `policies` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `tenant_id` | `tenants.tenant_id` | `CASCADE` | Policies are tenant-scoped authorization rules; no orphaned policies allowed. |

**Dependent Tables (CASCADE to `policies`)**:
- `policy_evaluation_logs`: Diagnostic logs; policy deletion purges evaluation history.

### 6. `policy_evaluation_logs` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `policy_id` | `policies.policy_id` | `CASCADE` | Evaluation logs are diagnostic/observability data; policy deletion can purge history. If retention required, implement archival before policy deletion. |

**Notes**:
- High-volume table (Phase 4: partitioning ADR planned).
- Retention policy (Phase 4): configurable TTL, automatic cleanup.
- CASCADE allows clean policy deletion without manual log cleanup.

### 7. `audit_events` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `tenant_id` | `tenants.tenant_id` | `SET NULL` | **Audit trail preservation** (FR-018): Even if tenant deleted, audit events persist for compliance/forensics. `tenant_id` becomes NULL but event remains. |
| `actor_user_id` | `users.user_id` | `SET NULL` | **Actor history preservation**: Even if actor user deleted, audit trail persists. `actor_user_id` becomes NULL but event remains. |

**Notes**:
- **Critical constraint**: `audit_events` MUST NOT use `CASCADE` for tenant_id or actor_user_id.
- Audit events are append-only; no updates except for data purging (compliance-driven, manual).
- Query pattern: `WHERE tenant_id IS NOT NULL AND tenant_id = ?` for active tenant events.
- Query pattern: `WHERE tenant_id IS NULL` for orphaned events (post-tenant-deletion forensics).

### 8. `feature_flags` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `tenant_id` | `tenants.tenant_id` | `CASCADE` | Feature flags are tenant-scoped configuration; orphaned flags have no meaning. |

**Notes**:
- Global flags (future): `tenant_id` nullable, no FK; survives tenant deletions.
- Tenant-specific flags: `tenant_id` NOT NULL, FK CASCADE.

### 9. `user_mfa` Table

| Column | References | ON DELETE | Rationale |
|--------|-----------|-----------|-----------|
| `user_id` | `users.user_id` | `CASCADE` | MFA credentials (TOTP secrets, WebAuthn keys) are user-specific; must be purged when user deleted for security. |

**Notes**:
- Composite PK: `(user_id, factor_type)` allows multiple MFA factors per user.
- Physical user deletion cascades all MFA enrollments.

### 10. `key_rotation_records` Table

**No Foreign Keys**

| Column | Type | Notes |
|--------|------|-------|
| `created_by` | UUID | Nullable; represents admin/system actor who initiated rotation. No FK constraint; value is informational/audit only. |

**Rationale**: Key rotation records are system-level; not scoped to tenant. `created_by` is a UUID for audit trail but no FK enforcement (admin users may be deleted).

## Cascade Chain Summary

### Physical Tenant Deletion → Cascade Effects

```
DELETE FROM tenants WHERE tenant_id = ?
  ↓ CASCADE
  ├─ users (all users in tenant)
  │   ↓ CASCADE
  │   ├─ user_roles (all role assignments)
  │   ├─ password_reset_requests (all password resets)
  │   └─ user_mfa (all MFA enrollments)
  │
  ├─ invitations (all pending invitations)
  ├─ policies (all tenant policies)
  │   ↓ CASCADE
  │   └─ policy_evaluation_logs (all evaluation history)
  │
  └─ feature_flags (all tenant-specific flags)

SET NULL (preserved):
  └─ audit_events.tenant_id → NULL (history preserved)
```

### Physical User Deletion → Cascade Effects

```
DELETE FROM users WHERE user_id = ?
  ↓ CASCADE
  ├─ user_roles (role assignments)
  ├─ password_reset_requests (password reset tokens)
  └─ user_mfa (MFA enrollments)

SET NULL (preserved):
  └─ audit_events.actor_user_id → NULL (actor history preserved)
```

### Physical Policy Deletion → Cascade Effects

```
DELETE FROM policies WHERE policy_id = ?
  ↓ CASCADE
  └─ policy_evaluation_logs (evaluation history purged)
```

## Soft Delete Behavior

**Critical**: Soft delete is implemented as a **status field change**, NOT a physical `DELETE` operation. Therefore, **no FK cascades are triggered by soft delete**.

### Soft Delete Implementation

```python
# Soft delete tenant (no CASCADE)
tenant.status = TenantStatusEnum.SOFT_DELETED
await session.commit()

# All FK-related records remain in database:
# - users, policies, invitations, feature_flags still exist
# - Application-level queries MUST filter out soft-deleted tenants:
#   WHERE tenant_id = ? AND status != 'soft_deleted'
```

### Soft Delete vs Physical Delete

| Operation | FK Cascades? | Audit Events? | Restoration? |
|-----------|--------------|---------------|--------------|
| Soft delete (status='soft_deleted') | ❌ No | ✅ Yes (audit.tenant_soft_deleted) | ✅ Possible (status='active') |
| Physical delete (DELETE FROM) | ✅ Yes (per ON DELETE policy) | ✅ Yes (audit.tenant_deleted), then SET NULL | ❌ Not possible |

### Application-Level Cascade for Soft Delete

If soft delete should "cascade" to related entities, implement **application-level soft delete**:

```python
# Application-level soft delete cascade (Phase 4+)
async def soft_delete_tenant(tenant_id: uuid.UUID, session: AsyncSession):
    # 1. Soft delete tenant
    tenant.status = TenantStatusEnum.SOFT_DELETED
    
    # 2. Soft delete all users (application-level)
    users = await session.execute(
        select(UserModel).where(UserModel.tenant_id == tenant_id)
    )
    for user in users.scalars():
        user.status = UserStatusEnum.DISABLED  # or soft_deleted if enum supports
    
    # 3. Disable feature flags (application-level)
    flags = await session.execute(
        select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == tenant_id)
    )
    for flag in flags.scalars():
        flag.state = FlagStateEnum.DISABLED
    
    await session.commit()
```

## Testing Strategy

Comprehensive FK cascade tests implemented in `tests/persistence/test_fk_cascade_behavior.py`:

### Test Coverage

1. **CASCADE Tests**:
   - ✅ `test_delete_user_cascades_to_password_resets`
   - ✅ `test_delete_user_cascades_to_user_roles`
   - ✅ `test_delete_user_cascades_to_user_mfa`
   - ✅ `test_delete_tenant_cascades_to_users`
   - ✅ `test_delete_tenant_cascades_to_invitations`
   - ✅ `test_delete_tenant_cascades_to_policies`
   - ✅ `test_delete_tenant_cascades_to_feature_flags`
   - ✅ `test_delete_policy_cascades_to_evaluation_logs`

2. **SET NULL Tests**:
   - ✅ `test_delete_tenant_preserves_audit_events_with_set_null`
   - ✅ `test_delete_user_preserves_audit_events_with_set_null`

3. **Soft Delete Tests**:
   - ✅ `test_soft_delete_tenant_preserves_users`
   - ✅ `test_soft_delete_tenant_preserves_policies`

4. **Constraint Violation Tests**:
   - ✅ `test_cannot_create_user_with_nonexistent_tenant`
   - ✅ `test_cannot_create_policy_with_nonexistent_tenant`
   - ✅ `test_cannot_create_password_reset_with_nonexistent_user`

### Running FK Tests

```bash
# Run all FK cascade tests
pytest tests/persistence/test_fk_cascade_behavior.py -v

# Run specific test class
pytest tests/persistence/test_fk_cascade_behavior.py::TestForeignKeyCascadeBehavior -v

# Run with database markers only
pytest -m db tests/persistence/test_fk_cascade_behavior.py
```

## Migration Safety

### Adding New FKs

When adding new foreign keys in future migrations:

1. **Decide ON DELETE policy**:
   - Ephemeral/association tables → `CASCADE`
   - Audit/history tables → `SET NULL`
   - Parent entities → Consider soft delete patterns

2. **Document in migration comment**:
   ```python
   # Migration: add_new_fk_xyz
   op.create_foreign_key(
       'fk_table_column_ref',
       'table_name', 'referenced_table',
       ['column'], ['referenced_column'],
       ondelete='CASCADE'  # Rationale: <explain why CASCADE appropriate>
   )
   ```

3. **Add test in `test_fk_cascade_behavior.py`**:
   - Test CASCADE behavior if applicable
   - Test SET NULL behavior if applicable
   - Test constraint violation (orphaned record rejection)

### Breaking Changes

**Changing ON DELETE policy is a breaking change**:

- Existing data may violate new constraints.
- Application logic may depend on current cascade behavior.

**Process**:
1. Document rationale in migration comments.
2. Add data migration if needed (e.g., SET NULL → CASCADE requires orphan cleanup).
3. Update `test_fk_cascade_behavior.py` tests.
4. Update this documentation.

## Phase 4+ Considerations

### Partitioning (High-Write Tables)

**Phase 4**: `policy_evaluation_logs` may be partitioned by time (monthly/quarterly).

**FK Impact**:
- Partitioned tables may have limited FK support in PostgreSQL.
- **Decision**: Keep `policy_id` FK for now; monitor performance.
- **Alternative**: Remove FK, enforce referential integrity at application layer.

**ADR Required**: Evaluate FK vs application-level enforcement for partitioned tables.

### Retention Policies

**Phase 4**: Automatic cleanup of evaluation logs older than retention window.

**FK Impact**:
- Retention cleanup = `DELETE FROM policy_evaluation_logs WHERE created_at < ?`
- No FK cascade issues (deleting child records).

**Configuration**: `POLICY_EVAL_LOG_RETENTION_DAYS` (default 90 days).

### Archival Strategy

If audit compliance requires long-term policy evaluation log storage:

1. **Option A**: Archive to separate table/schema before policy deletion.
2. **Option B**: Remove FK constraint, rely on application-level cleanup.
3. **Option C**: Change ON DELETE to `SET NULL` for `policy_id` (evaluation log orphaned).

**Recommended**: **Option A** (archive before deletion) maintains referential integrity during active lifecycle.

## References

- **Migration**: `alembic/versions/20251005_0356_9f85fdd0f4d0_initial_schema_baseline.py`
- **Tests**: `tests/persistence/test_fk_cascade_behavior.py`
- **FRs**: FR-002 (tenant isolation), FR-018 (soft delete), FR-077 (audit metadata)
- **Phase 3 Plan**: `specs/001-modern-enterprise-grade/plan.md` (soft delete semantics, RESTRICT FKs)
