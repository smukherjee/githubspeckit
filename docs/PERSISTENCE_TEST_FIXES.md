# Persistence Test Fixes Summary

**Date:** October 5, 2025  
**Status:** 85/108 tests passing (78.7%)

## ✅ Successfully Fixed

### 1. Test Infrastructure (Critical Foundation)
- **conftest.py**: Implemented proper async session management with `pytest_asyncio`
- **Transaction Isolation**: Function-scoped engine with automatic rollback
- **Fixtures**: All repository fixtures working correctly

### 2. Repository Implementation Bugs Fixed
- **TenantRepository.list()**: Now excludes soft-deleted tenants (FR-018)
- **UserRepository.list_by_tenant()**: Now excludes soft-deleted users (FR-018)
- **DatabaseReplayStore**: JTI is now globally unique (FR-SEC-020 security fix)

### 3. Security Fix: JWT Replay Protection
**Issue:** Original test expected same JTI to work for different tenants  
**Security Risk:** Superadmin tokens could be replayed across tenants  
**Fix:** 
- JTI must be globally unique regardless of tenant
- Prevents replay attacks on privileged tokens
- Updated test to validate correct behavior

**Rationale:**
```
Superadmin tokens have access to all tenants.
If JTI is scoped per-tenant:
  - Token with JTI "abc123" used in tenant A
  - Same token could be replayed in tenant B
  - Violates replay protection for privileged users

Solution: JTI is globally unique, protecting all users including superadmin
```

### 4. Test Files - 100% Passing

#### test_tenant_isolation.py (6/6 tests) ✅
- Fixed all field naming: `id` → `tenant_id`, `user_id`, `policy_id`, `flag_id`
- Removed non-existent `slug` field from Tenant
- Fixed enum access: `ACTIVE` → `active`, `ENABLED` → `enabled`
- Fixed `hashed_password` → `password_hash`
- Fixed Policy model structure (uses `rules` list with `PolicyRule` objects)

#### test_replay_store.py (15/15 tests) ✅
- Fixed test_multi_tenant_isolation to validate correct security behavior
- All replay detection tests passing
- Cleanup and edge case tests passing

#### test_repository_parity.py (24/24 tests) ✅
- All parity tests passing

#### test_query_metrics.py (18/18 tests) ✅
- All query metric tests passing

#### test_fk_cascade_behavior.py (12/15 tests) ✅
- Most FK tests passing
- 3 failures need investigation (CASCADE and SET NULL behavior)

---

## ❌ Remaining Issues

### 1. test_policy_evaluation_logs.py (0/4 tests, all failing)
**Issue:** Model/Test Mismatch

**Tests Expect:**
```python
PolicyEvaluationLogModel(
    log_id=...,           # ❌ Model has: eval_id
    resource="users",     # ❌ Not in model
    action="read",        # ❌ Not in model
    rationale_code="...", # ❌ Not in model
    context={...},        # ❌ Not in model
    evaluated_at=...      # ❌ Model has: created_at
)
```

**Model Actually Has:**
```python
PolicyEvaluationLogModel(
    eval_id: UUID,        # Primary key
    policy_id: UUID,
    decision: DecisionEnum,
    latency_ms: int,
    tenant_id: UUID,
    user_id: UUID,
    correlation_id: str,
    created_at: datetime
)
```

**Action Required:** 
- Either update model to match test expectations (add resource, action, rationale_code, context)
- Or update tests to match current model structure
- Recommend: Expand model to support full audit trail

### 2. test_migration_smoke.py (0/7 tests, all failing)
**Issue:** Non-async tests requesting async fixtures

```python
# Current (fails):
def test_expected_tables_exist(self, db_engine, clean_db):
    ...

# Should be:
async def test_expected_tables_exist(self, db_engine, clean_db):
    ...
```

**Action Required:** Add `async` keyword to all test methods

### 3. test_fk_cascade_behavior.py (3/15 failures)
**Failing Tests:**
- `test_delete_policy_cascades_to_evaluation_logs`
- `test_delete_tenant_preserves_audit_events_with_set_null`
- `test_delete_user_preserves_audit_events_with_set_null`

**Likely Issues:**
- FK CASCADE not working correctly
- FK SET NULL not preserving records
- Need to verify foreign key constraints in schema

### 4. test_migration_check.py (1 failure)
- `test_get_current_revision_queries_database` - Mock/async issue

### 5. test_seed_idempotency.py (8 errors)
**Issue:** Import or setup errors preventing test collection

**Action Required:** Check test file for import errors

---

## 📊 Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **Passing** | 85 | 78.7% |
| **Failing** | 15 | 13.9% |
| **Errors** | 8 | 7.4% |
| **Total** | 108 | 100% |

### By Test File

| File | Status | Tests |
|------|--------|-------|
| test_tenant_isolation.py | ✅ | 6/6 (100%) |
| test_replay_store.py | ✅ | 15/15 (100%) |
| test_repository_parity.py | ✅ | 24/24 (100%) |
| test_query_metrics.py | ✅ | 18/18 (100%) |
| test_fk_cascade_behavior.py | ⚠️ | 12/15 (80%) |
| test_migration_check.py | ⚠️ | 9/10 (90%) |
| test_migration_smoke.py | ❌ | 0/7 (0%) |
| test_policy_evaluation_logs.py | ❌ | 0/4 (0%) |
| test_seed_idempotency.py | 🚫 | 0/8 (errors) |

---

## 🔧 Key Fixes Applied

### Dependencies
```toml
# Added to pyproject.toml
"tomli>=2.2,<3"  # TOML parsing for config descriptor

# Already present but verified
"pytest-asyncio>=1.2.0"
"greenlet>=3.2.4"  # SQLAlchemy async support
```

### Database Schema
```sql
-- token_replay_records: Kept jti as sole PRIMARY KEY
-- This ensures JTI is globally unique (required for superadmin security)
CREATE TABLE token_replay_records (
    jti VARCHAR(255) PRIMARY KEY,  -- Globally unique
    expires_at FLOAT NOT NULL,
    registered_at FLOAT NOT NULL,
    tenant_id UUID  -- Nullable, for tracking only
);
```

### Test Fixture Pattern
```python
# conftest.py
@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            async with connection.begin() as transaction:
                async_session_maker = async_sessionmaker(
                    bind=connection,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint"
                )
                async with async_session_maker() as session:
                    yield session
                    await transaction.rollback()  # Test isolation
    finally:
        await engine.dispose()
```

---

## 🎯 Next Steps

### Priority 1: Quick Wins
1. Fix test_migration_smoke.py - Add `async` to test methods
2. Fix test_seed_idempotency.py - Resolve import errors

### Priority 2: Schema/Model Updates
1. Expand PolicyEvaluationLogModel with audit fields
2. Verify FK CASCADE/SET NULL constraints
3. Update test_policy_evaluation_logs.py tests

### Priority 3: Edge Cases
1. Investigate remaining FK cascade failures
2. Fix test_migration_check.py mock issues

---

## 📝 Design Decisions

### Why JTI Must Be Globally Unique

**Context:** Multi-tenant system with superadmin role

**Decision:** JTI (JWT ID) is globally unique, not scoped per tenant

**Reasoning:**
1. **Superadmin Security:** Superadmin users have access to all tenants
2. **Replay Attack Prevention:** A token used in one context cannot be reused elsewhere
3. **JWT Standard:** JTI is meant to be a globally unique identifier per RFC 7519
4. **Defense in Depth:** Even if tenant scoping had merit, global uniqueness is safer

**Alternative Considered:** Composite key (jti, tenant_id)
- ❌ Breaks superadmin security
- ❌ Violates JWT standard
- ❌ Complex to implement correctly
- ❌ No real benefit

**Conclusion:** Single PRIMARY KEY on jti, tenant_id as nullable tracking field only

---

## 🔍 Field Naming Conventions (Established)

| Model | Primary Key | Other Fields |
|-------|-------------|--------------|
| TenantModel | tenant_id | name, status, config_version |
| UserModel | user_id | tenant_id, email, password_hash, status, roles |
| PolicyModel | policy_id | tenant_id, name, rules |
| FeatureFlagModel | flag_id | tenant_id, key, state, variant |
| PolicyEvaluationLogModel | eval_id | policy_id, decision, latency_ms |

**Pattern:** Each model uses `{entity}_id` for primary key, never just `id`

---

---

## 🔧 DATABASE_URL Consolidation (October 5, 2025)

### Problem
- Multiple test files defined their own `DATABASE_URL` with different credentials
- `test_migration_smoke.py` was setting environment variables that persisted across tests
- This caused test failures when tests ran in different orders
- VS Code test UI showed tests as failed due to missing schema

### Solution
**Single Source of Truth:** `tests/persistence/conftest.py`

```python
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
)
```

All test files now import from conftest:
```python
from conftest import DATABASE_URL as TEST_DATABASE_URL
```

### Files Updated
1. `tests/persistence/conftest.py` - Main configuration
2. `tests/persistence/test_migration_smoke.py` - Imports from conftest, uses wrapper function
3. `tests/persistence/test_seed_idempotency.py` - Imports from conftest  
4. `alembic/env.py` - Updated default to match test database

### Key Changes in test_migration_smoke.py
- Created `run_alembic_command()` wrapper to temporarily set DATABASE_URL env var
- Environment variable only set during Alembic command execution
- Automatically restores original value after command completes
- Prevents environment pollution affecting other tests

### Test Setup Requirements
⚠️ **Before running tests, ensure:**
1. Migrations applied: `alembic upgrade head`
2. Database seeded: `python scripts/seed_infysight.py`
3. See `tests/persistence/README_TEST_SETUP.md` for details

---

**Last Updated:** October 5, 2025 - Phase 3 Test Fixing + DATABASE_URL Consolidation
