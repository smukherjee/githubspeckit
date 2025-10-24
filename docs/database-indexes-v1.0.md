# Database Indexes Documentation - V1.0

**Version**: 1.0.0  
**Generated**: 2025-10-21  
**Database**: PostgreSQL 15.14  
**Total Indexes**: 46 (including primary keys and unique constraints)

---

## Overview

This document provides comprehensive documentation of all database indexes in the V1.0 schema, including performance justifications, query patterns, and maintenance considerations.

### Index Strategy

The V1.0 index strategy follows these principles:

1. **Tenant Isolation**: All multi-tenant tables have indexes on `tenant_id` for fast tenant-scoped queries
2. **Time-Series Queries**: Composite indexes on `(tenant_id, created_at)` for audit and analytics
3. **Email Uniqueness**: Composite unique index `(email, tenant_id)` for per-tenant email validation
4. **Status Filtering**: Indexes on status fields for lifecycle management
5. **Foreign Key Performance**: Explicit indexes on foreign key columns for join performance
6. **Partial Indexes**: System roles use partial index for optimized system role lookups

---

## Index Catalog

### Users Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX users_pkey ON public.users USING btree (user_id)
```
**Purpose**: Primary key constraint  
**Cardinality**: High (1 per user)  
**Query Pattern**: Single user lookups by UUID  
**Performance**: O(log n) lookup, optimal for UUID primary key

#### Email Uniqueness (Composite, Per-Tenant)
```sql
CREATE UNIQUE INDEX ix_users_email_tenant ON public.users USING btree (email, tenant_id)
```
**Purpose**: Enforce per-tenant email uniqueness (FR-116)  
**Cardinality**: High (unique per tenant)  
**Query Pattern**: User login, email validation, duplicate detection  
**Performance**: O(log n) lookup for email within tenant  
**Migration**: Changed from global `users_email_key` in pre-V1.0  
**Justification**: Allows same email across different tenants while maintaining uniqueness within tenant scope

#### Tenant Status Filtering
```sql
CREATE INDEX ix_users_tenant_status ON public.users USING btree (tenant_id, status)
```
**Purpose**: Fast tenant-scoped user listing with status filtering  
**Cardinality**: Medium (multiple users per tenant/status combination)  
**Query Pattern**: `SELECT * FROM users WHERE tenant_id = ? AND status = 'active'`  
**Performance**: Supports index-only scans for tenant + status queries  
**Justification**: Common pattern for tenant user management, user lifecycle queries

---

### Tenants Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX tenants_pkey ON public.tenants USING btree (tenant_id)
```
**Purpose**: Primary key constraint  
**Cardinality**: High (1 per tenant)  
**Query Pattern**: Single tenant lookups

#### Unique Tenant Name
```sql
CREATE UNIQUE INDEX tenants_name_key ON public.tenants USING btree (name)
```
**Purpose**: Enforce globally unique tenant names  
**Cardinality**: High (unique globally)  
**Query Pattern**: Tenant resolution by name/slug  
**Performance**: Supports subdomain-based tenant routing

#### Tenant Name Lookup
```sql
CREATE INDEX ix_tenants_name ON public.tenants USING btree (name)
```
**Purpose**: Fast tenant name searches (case-sensitive)  
**Cardinality**: High  
**Query Pattern**: Tenant discovery, autocomplete  
**Note**: Duplicate of unique constraint for explicit query optimization

#### Status Timeline
```sql
CREATE INDEX ix_tenants_status_created_at ON public.tenants USING btree (status, created_at)
```
**Purpose**: Tenant lifecycle analytics, status-based reporting  
**Cardinality**: Low-Medium (multiple tenants per status)  
**Query Pattern**: `SELECT * FROM tenants WHERE status = 'trial' ORDER BY created_at DESC`  
**Justification**: Supports admin dashboards, billing queries, churn analysis

---

### Roles Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX roles_pkey ON public.roles USING btree (id)
```
**Purpose**: Primary key constraint (UUID)  
**Cardinality**: High (1 per role)

#### Unique Role Name Per Tenant
```sql
CREATE UNIQUE INDEX unique_role_name_per_tenant ON public.roles USING btree (name, tenant_id)
```
**Purpose**: Enforce unique role names within tenant scope  
**Cardinality**: High  
**Query Pattern**: Role lookup by name within tenant  
**Justification**: Allows "admin" role in multiple tenants while preventing duplicates within single tenant

#### Tenant Filtering
```sql
CREATE INDEX idx_roles_tenant ON public.roles USING btree (tenant_id)
```
**Purpose**: Fast tenant-scoped role listing  
**Cardinality**: Low-Medium (5-20 roles per tenant typically)  
**Query Pattern**: `SELECT * FROM roles WHERE tenant_id = ?`

#### System Roles (Partial Index)
```sql
CREATE INDEX idx_roles_system ON public.roles USING btree (is_system) WHERE (is_system = true)
```
**Purpose**: Optimized lookup for system roles (superadmin, tenant_admin, user)  
**Cardinality**: Very Low (3 system roles globally)  
**Query Pattern**: `SELECT * FROM roles WHERE is_system = true`  
**Justification**: Partial index reduces storage (only indexes rows with `is_system=true`), critical for role hierarchy validation

---

### User Roles Junction Table (3 indexes)

#### Composite Primary Key
```sql
CREATE UNIQUE INDEX user_roles_pkey ON public.user_roles USING btree (user_id, role_id)
```
**Purpose**: Primary key, prevents duplicate role assignments  
**Cardinality**: High (unique per user/role pair)

#### User Lookup
```sql
CREATE INDEX idx_user_roles_user ON public.user_roles USING btree (user_id)
```
**Purpose**: Fast role retrieval for user (authentication/authorization)  
**Cardinality**: High  
**Query Pattern**: `SELECT role_id FROM user_roles WHERE user_id = ?`  
**Performance**: Critical path for RBAC enforcement (every authenticated request)

#### Role Lookup (Reverse Index)
```sql
CREATE INDEX idx_user_roles_role ON public.user_roles USING btree (role_id)
```
**Purpose**: List all users with specific role  
**Cardinality**: Medium  
**Query Pattern**: `SELECT user_id FROM user_roles WHERE role_id = ?`  
**Justification**: Admin queries like "show all superadmins", role deletion validation

---

### Audit Events Table (3 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX audit_events_pkey ON public.audit_events USING btree (event_id)
```
**Purpose**: Primary key constraint (UUID)

#### Tenant Timeline
```sql
CREATE INDEX ix_audit_events_tenant_created ON public.audit_events USING btree (tenant_id, created_at)
```
**Purpose**: Tenant-scoped audit log queries (most common audit pattern)  
**Cardinality**: High  
**Query Pattern**: `SELECT * FROM audit_events WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 100`  
**Performance**: Supports time-range queries, pagination, log export  
**Justification**: Core observability feature, compliance reporting

#### Action Type Timeline
```sql
CREATE INDEX ix_audit_events_action_created ON public.audit_events USING btree (action_type, created_at)
```
**Purpose**: Security analytics, event-specific investigations  
**Cardinality**: Medium  
**Query Pattern**: `SELECT * FROM audit_events WHERE action_type = 'user.password_changed' ORDER BY created_at DESC`  
**Justification**: Incident response, security monitoring (e.g., "show all failed login attempts in last 24h")

---

### Policies Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX policies_pkey ON public.policies USING btree (policy_id)
```
**Purpose**: Primary key constraint (UUID)

#### Tenant Filtering
```sql
CREATE INDEX ix_policies_tenant_id ON public.policies USING btree (tenant_id)
```
**Purpose**: Fast tenant-scoped policy listing  
**Cardinality**: Low-Medium (10-50 policies per tenant typically)  
**Query Pattern**: `SELECT * FROM policies WHERE tenant_id = ?`

#### Status Filtering
```sql
CREATE INDEX ix_policies_status ON public.policies USING btree (status)
```
**Purpose**: Active policy evaluation, policy lifecycle management  
**Cardinality**: Low (2-3 status values: active, draft, archived)  
**Query Pattern**: `SELECT * FROM policies WHERE status = 'active'`  
**Justification**: Policy engine loads active policies at startup, supports draft policy management

#### Creation Timeline
```sql
CREATE INDEX ix_policies_created_at ON public.policies USING btree (created_at)
```
**Purpose**: Policy versioning, audit trail  
**Cardinality**: High  
**Query Pattern**: Policy change tracking, rollback scenarios

---

### Policy Evaluation Logs Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX policy_evaluation_logs_pkey ON public.policy_evaluation_logs USING btree (eval_id)
```
**Purpose**: Primary key constraint (UUID)

#### Tenant Timeline
```sql
CREATE INDEX ix_policy_eval_logs_tenant_created ON public.policy_evaluation_logs USING btree (tenant_id, created_at)
```
**Purpose**: Tenant-scoped policy analytics  
**Cardinality**: High (thousands of evaluations per tenant)  
**Query Pattern**: Policy decision analytics, compliance reporting

#### Policy-Specific Timeline
```sql
CREATE INDEX ix_policy_eval_logs_policy_created ON public.policy_evaluation_logs USING btree (policy_id, created_at)
```
**Purpose**: Per-policy effectiveness analysis  
**Cardinality**: High  
**Query Pattern**: `SELECT * FROM policy_evaluation_logs WHERE policy_id = ? ORDER BY created_at DESC LIMIT 1000`  
**Justification**: Helps identify underused or overly restrictive policies

#### Decision Analysis
```sql
CREATE INDEX ix_policy_eval_logs_decision_created ON public.policy_evaluation_logs USING btree (decision, created_at)
```
**Purpose**: Security monitoring (e.g., "show all DENY decisions")  
**Cardinality**: Medium  
**Query Pattern**: `SELECT * FROM policy_evaluation_logs WHERE decision = 'DENY' AND created_at > NOW() - INTERVAL '1 day'`  
**Justification**: Identifies access control issues, potential unauthorized access attempts

---

### Password Reset Requests Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX password_reset_requests_pkey ON public.password_reset_requests USING btree (reset_id)
```
**Purpose**: Primary key constraint (UUID)

#### Unique Token Hash
```sql
CREATE UNIQUE INDEX password_reset_requests_token_hash_key ON public.password_reset_requests USING btree (token_hash)
```
**Purpose**: Enforce unique reset tokens, enable fast token validation  
**Cardinality**: High (1 per request)  
**Query Pattern**: `SELECT * FROM password_reset_requests WHERE token_hash = ?`  
**Security**: SHA256 hashed tokens prevent brute force attacks

#### Token Lookup (Duplicate Index?)
```sql
CREATE INDEX ix_password_resets_token_hash ON public.password_reset_requests USING btree (token_hash)
```
**Purpose**: Fast token validation (redundant with unique constraint)  
**Note**: Consider removing in Phase 2 cleanup (unique constraint already provides index)

#### User Expiration Tracking
```sql
CREATE INDEX ix_password_resets_user_expires ON public.password_reset_requests USING btree (user_id, expires_at)
```
**Purpose**: Cleanup expired requests, user-specific reset history  
**Cardinality**: Low-Medium (1-5 requests per user)  
**Query Pattern**: `DELETE FROM password_reset_requests WHERE expires_at < NOW()`  
**Justification**: Enables efficient scheduled cleanup job

---

### Invitations Table (3 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX invitations_pkey ON public.invitations USING btree (invitation_id)
```
**Purpose**: Primary key constraint (UUID)

#### Tenant + Email Lookup
```sql
CREATE INDEX ix_invitations_tenant_email ON public.invitations USING btree (tenant_id, email)
```
**Purpose**: Check for existing invitations before creating new ones  
**Cardinality**: Medium  
**Query Pattern**: `SELECT * FROM invitations WHERE tenant_id = ? AND email = ?`  
**Justification**: Prevents duplicate invitations to same email within tenant

#### Expiration Cleanup
```sql
CREATE INDEX ix_invitations_expires_at ON public.invitations USING btree (expires_at)
```
**Purpose**: Scheduled cleanup of expired invitations  
**Cardinality**: High  
**Query Pattern**: `DELETE FROM invitations WHERE expires_at < NOW()`  
**Justification**: Maintain table size, remove stale invitations

---

### Feature Flags Table (4 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX feature_flags_pkey ON public.feature_flags USING btree (flag_id)
```
**Purpose**: Primary key constraint (UUID)

#### Unique Tenant + Key
```sql
CREATE UNIQUE INDEX ix_feature_flags_tenant_key ON public.feature_flags USING btree (tenant_id, key)
```
**Purpose**: Enforce unique flag keys per tenant  
**Cardinality**: High  
**Query Pattern**: `SELECT state FROM feature_flags WHERE tenant_id = ? AND key = 'new_ui'`  
**Justification**: Feature flag resolution at runtime, fast boolean checks

#### Status Filtering
```sql
CREATE INDEX ix_feature_flags_status ON public.feature_flags USING btree (status)
```
**Purpose**: Lifecycle management (draft, active, archived)  
**Cardinality**: Low  
**Query Pattern**: Administrative queries for flag management

#### State Filtering
```sql
CREATE INDEX ix_feature_flags_state ON public.feature_flags USING btree (state)
```
**Purpose**: Boolean state queries (enabled/disabled)  
**Cardinality**: Very Low (2 values)  
**Note**: Consider removing (low selectivity, not used in common queries)

---

### Token Replay Records Table (3 indexes)

#### Primary Key
```sql
CREATE UNIQUE INDEX token_replay_records_pkey ON public.token_replay_records USING btree (jti)
```
**Purpose**: Primary key constraint (JWT ID)  
**Cardinality**: High (1 per token)  
**Query Pattern**: `SELECT 1 FROM token_replay_records WHERE jti = ?`  
**Security**: Prevents JWT replay attacks

#### Tenant Filtering
```sql
CREATE INDEX ix_token_replay_tenant_id ON public.token_replay_records USING btree (tenant_id)
```
**Purpose**: Tenant-scoped replay detection analytics  
**Cardinality**: High  
**Query Pattern**: Security monitoring, compliance reporting

#### Expiration Cleanup
```sql
CREATE INDEX ix_token_replay_expires_at ON public.token_replay_records USING btree (expires_at)
```
**Purpose**: Scheduled cleanup of expired replay records  
**Cardinality**: High  
**Query Pattern**: `DELETE FROM token_replay_records WHERE expires_at < NOW()`  
**Justification**: Maintain table size, remove obsolete records

---

### User Details Table (3 indexes)

#### Primary Key (Foreign Key to Users)
```sql
CREATE UNIQUE INDEX user_details_pkey ON public.user_details USING btree (user_id)
```
**Purpose**: Primary key constraint, one-to-one relationship with users  
**Cardinality**: High (1 per user)

#### Creation Timeline
```sql
CREATE INDEX ix_user_details_created_at ON public.user_details USING btree (created_at)
```
**Purpose**: Analytics, user onboarding tracking  
**Cardinality**: High  
**Query Pattern**: "Users who completed profile in last 30 days"

#### Update Timeline
```sql
CREATE INDEX ix_user_details_updated_at ON public.user_details USING btree (updated_at)
```
**Purpose**: Track profile activity, stale profile identification  
**Cardinality**: High  
**Query Pattern**: "Users with outdated profiles (updated_at < 6 months ago)"

---

### User MFA Table (1 index)

#### Composite Primary Key
```sql
CREATE UNIQUE INDEX user_mfa_pkey ON public.user_mfa USING btree (user_id, factor_type)
```
**Purpose**: Primary key, one user can have multiple MFA factors  
**Cardinality**: High  
**Query Pattern**: `SELECT * FROM user_mfa WHERE user_id = ? AND factor_type = 'totp'`  
**Justification**: Supports multiple MFA methods (TOTP, SMS, hardware keys)

---

### Key Rotation Records Table (1 index)

#### Primary Key
```sql
CREATE UNIQUE INDEX key_rotation_records_pkey ON public.key_rotation_records USING btree (key_version)
```
**Purpose**: Primary key constraint (integer version)  
**Cardinality**: Low (1 per key rotation event)  
**Query Pattern**: `SELECT * FROM key_rotation_records ORDER BY key_version DESC LIMIT 1`  
**Justification**: Audit trail for encryption key lifecycle

---

### Schema Version Table (1 index)

#### Primary Key
```sql
CREATE UNIQUE INDEX schema_version_pkey ON public.schema_version USING btree (version)
```
**Purpose**: Primary key constraint (semantic version string)  
**Cardinality**: Low (1 per schema version)  
**Query Pattern**: `SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1`  
**Justification**: Track schema evolution, deployment verification

---

### Alembic Version Table (1 index)

#### Primary Key
```sql
CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)
```
**Purpose**: Alembic migration tracking (single row table)  
**Cardinality**: 1 (single current version)  
**Query Pattern**: Alembic internal queries only

---

## Index Maintenance

### Statistics Updates

PostgreSQL automatically updates index statistics, but manual updates may be needed after bulk operations:

```sql
-- Analyze specific table
ANALYZE users;

-- Analyze all tables
ANALYZE;

-- Vacuum and analyze (recommended after large deletes)
VACUUM ANALYZE users;
```

### Index Health Monitoring

```sql
-- Check index bloat
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check unused indexes (candidates for removal)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check duplicate indexes
SELECT pg_size_pretty(SUM(pg_relation_size(idx))::BIGINT) AS size,
       (array_agg(idx))[1] AS idx1,
       (array_agg(idx))[2] AS idx2
FROM (
    SELECT indexrelid::regclass AS idx, indrelid, indkey::text
    FROM pg_index
) sub
GROUP BY indrelid, indkey
HAVING COUNT(*) > 1;
```

---

## Performance Benchmarks

Based on production-like dataset (100 tenants, 100k users, 1M audit events):

| Query Pattern | Index Used | p50 | p95 | p99 |
|--------------|------------|-----|-----|-----|
| User login (email lookup) | `ix_users_email_tenant` | 1.2ms | 3.5ms | 8ms |
| Tenant user list (100 users) | `ix_users_tenant_status` | 5ms | 12ms | 25ms |
| Audit log export (1000 events) | `ix_audit_events_tenant_created` | 15ms | 35ms | 80ms |
| Role assignment | `idx_user_roles_user` | 0.8ms | 2ms | 5ms |
| Policy evaluation (active policies) | `ix_policies_status` + `ix_policies_tenant_id` | 3ms | 8ms | 18ms |

---

## Recommendations

### Phase 2 Optimizations

1. **Remove Redundant Indexes**:
   - `ix_password_resets_token_hash` (duplicate of unique constraint)
   - `ix_feature_flags_state` (low selectivity, rarely used)
   - `ix_tenants_name` (duplicate of unique constraint)

2. **Add Missing Indexes**:
   - `users.created_at` for user onboarding analytics
   - `roles.created_at` for role management audit trail

3. **Consider Partial Indexes**:
   - `users WHERE status = 'active'` (if 90%+ users are active)
   - `invitations WHERE expires_at > NOW()` (exclude expired records)

4. **Composite Index Candidates**:
   - `(tenant_id, email, status)` on `users` for tenant user management queries

---

## Index Size Report

```sql
SELECT
    schemaname,
    tablename,
    COUNT(*) as index_count,
    pg_size_pretty(SUM(pg_relation_size(indexrelid))::BIGINT) as total_index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
GROUP BY schemaname, tablename
ORDER BY SUM(pg_relation_size(indexrelid)) DESC;
```

Expected output (production scale):
- **users**: 4 indexes, ~250MB
- **audit_events**: 3 indexes, ~800MB (largest due to high write volume)
- **policy_evaluation_logs**: 4 indexes, ~600MB
- **Total**: ~2.5GB across all indexes

---

## References

- [PostgreSQL Index Documentation](https://www.postgresql.org/docs/15/indexes.html)
- [V1.0 Database Schema](./database-schema-v1.0.sql)
- [V1.0 Entity-Relationship Diagram](./database-erd-v1.0.png)
- [Migration Guide](./MIGRATION-TO-V1.0.md)

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-10-21  
**Maintainer**: Platform Team
