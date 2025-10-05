# Infysight Database Seed Summary

**Date**: October 5, 2025  
**Database**: infysight_users  
**Connection**: postgresql://infysight_dbadmin@localhost/infysight_users

## ✅ Database Setup Complete

### 1. Database Configuration

**Alembic Connection String** (updated in `alembic.ini`):
```ini
sqlalchemy.url = postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users
```

### 2. Migrations Applied

Successfully applied 2 migrations:
- ✅ `9f85fdd0f4d0` - initial_schema_baseline (13 tables + 5 enum types)
- ✅ `8c01924a527d` - add_token_replay_records_table

**Tables Created** (13 total):
1. `tenants` - Multi-tenant root entity
2. `users` - User accounts (tenant-scoped)
3. `user_roles` - User role assignments
4. `invitations` - Pending user invitations
5. `password_reset_requests` - Password reset tokens
6. `policies` - Authorization policies
7. `policy_evaluation_logs` - Policy evaluation history
8. `audit_events` - Audit trail
9. `feature_flags` - Feature toggles
10. `key_rotation_records` - Key rotation history
11. `user_mfa` - MFA enrollments
12. `token_replay_records` - Token replay detection
13. `alembic_version` - Migration tracking

**Enum Types Created** (5 total):
- `tenant_status`: 'active', 'soft_deleted'
- `user_status`: 'invited', 'active', 'disabled'
- `flag_state`: 'enabled', 'disabled'
- `decision`: 'ALLOW', 'DENY', 'ABSTAIN'
- `mfa_factor_type`: 'totp', 'webauthn'

### 3. Seed Data Created

**Script**: `scripts/seed_infysight.py`

**Tenant**:
- **ID**: `c79911ec-beb1-5c45-833d-4a9847b88024` (deterministic UUIDv5)
- **Name**: `infysight`
- **Status**: `active`
- **Config Version**: 1

**Superadmin User**:
- **ID**: `a5053ec7-a656-53ef-98c4-8713a68b2b9b` (deterministic UUIDv5)
- **Email**: `infysightsa@infysight.com`
- **Username**: `infysightsa`
- **Password**: `infysightsa123` (Argon2id hashed)
- **Role**: `superadmin`
- **Status**: `active`
- **Tenant**: `infysight`

## 🔐 Login Credentials

```
Username: infysightsa
Email: infysightsa@infysight.com
Password: infysightsa123
Role: superadmin
Tenant: infysight
```

## 📝 Usage Instructions

### Running Migrations

```bash
# Set environment variable for database URL
export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"

# Apply all pending migrations
source .venv/bin/activate
alembic upgrade head

# Check current migration version
alembic current

# Generate new migration
alembic revision --autogenerate -m "description"
```

### Re-running Seed Script (Idempotent)

```bash
source .venv/bin/activate
python scripts/seed_infysight.py
```

**Note**: The seed script is idempotent. Running it multiple times will:
- Skip tenant creation if "infysight" already exists
- Skip or update the user if "infysightsa" already exists
- Update the password if the user exists

### Connecting to Database

**psql**:
```bash
PGPASSWORD=infysight_dbadmin123 psql -U infysight_dbadmin -h localhost -d infysight_users
```

**Python (async)**:
```python
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
engine = create_async_engine(DATABASE_URL)
```

## 🔧 Troubleshooting

### Issue: "greenlet module not found"
**Solution**: Install greenlet dependency
```bash
source .venv/bin/activate
pip install greenlet
```

### Issue: "password authentication failed"
**Solution**: Ensure DATABASE_URL environment variable is set correctly
```bash
export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
```

### Issue: "type already exists" error
**Solution**: SQLAlchemy auto-creates enum types. Don't create them manually in migrations.

## 📊 Database Schema Overview

### Key Relationships

```
tenants (1) ─┬─ (N) users
             ├─ (N) invitations  
             ├─ (N) policies
             └─ (N) feature_flags

users (1) ─┬─ (N) user_roles
           ├─ (N) password_reset_requests
           └─ (N) user_mfa

policies (1) ── (N) policy_evaluation_logs

audit_events (nullable FKs to tenants, users for history preservation)
```

### Foreign Key Cascade Policies

- **CASCADE**: `users`, `invitations`, `policies`, `feature_flags`, `user_roles`, `password_resets`, `user_mfa`, `policy_evaluation_logs`
- **SET NULL**: `audit_events.tenant_id`, `audit_events.actor_user_id` (history preservation)
- **No FK**: `key_rotation_records`, `token_replay_records` (system-level)

See `docs/database-foreign-keys.md` for complete documentation.

## 🚀 Next Steps

1. **Start FastAPI Server** (when implemented):
   ```bash
   uvicorn src.main:app --reload
   ```

2. **Test Authentication** (when API implemented):
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "infysightsa@infysight.com", "password": "infysightsa123"}'
   ```

3. **Add More Users**:
   - Use the seed script pattern to create additional users
   - Or use the API user registration endpoint (when implemented)

4. **Configure Feature Flags**:
   - Insert records into `feature_flags` table
   - Assign tenant-specific or global flags

5. **Set Up Policies**:
   - Create authorization policies in `policies` table
   - Test policy evaluation against superadmin user

## 📚 Reference Documentation

- **Migration Documentation**: `docs/database-testing.md`
- **Foreign Key Documentation**: `docs/database-foreign-keys.md`
- **Phase 3 Completion**: `specs/001-modern-enterprise-grade/PHASE_3_COMPLETE.md`
- **Seed Script**: `scripts/seed_infysight.py`
- **Original Bootstrap**: `src/cli/db_bootstrap.py`

## ✅ Verification Checklist

- [x] Database `infysight_users` exists
- [x] All 13 tables created successfully
- [x] All 5 enum types created successfully
- [x] Alembic migrations applied (2 revisions)
- [x] Tenant "infysight" created
- [x] User "infysightsa" created with superadmin role
- [x] Password hashed with Argon2id
- [x] Deterministic UUIDs generated (UUIDv5)
- [x] Seed script is idempotent
- [x] Connection string configured in alembic.ini

---

**Status**: ✅ **READY FOR USE**

The infysight tenant and superadmin user are ready for authentication and testing!
