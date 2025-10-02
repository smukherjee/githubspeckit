# Data Model (Phase 1)

Source Spec: `/specs/001-modern-enterprise-grade/spec.md`
Date: 2025-10-02
Status: Draft (Design Complete Pending Constitution Re-check)

## Entities Overview

| Entity | Purpose | Key Fields | Relationships | Notes |
|--------|---------|------------|---------------|-------|
| Tenant | Logical isolation boundary | tenant_id (UUID), name, status, config_version, created_at | 1..\* Users, 1..\* Policies, 1..\* Invitations, 1..\* FeatureFlags | Soft delete supported |
| User | Authenticated principal within a tenant | user_id (UUID), tenant_id, email, status, roles[], last_login_at | *..* Roles, 1..* PasswordResetRequest, belongs to Tenant | Roles resolved via assignment table |
| Invitation | Pending user onboarding | invitation_id, tenant_id, email, token_hash, expires_at, accepted_at | Belongs to Tenant | Token hashed SHA-256 |
| PasswordResetRequest | Password reset flow state | reset_id, user_id, token_hash, issued_at, expires_at, consumed_at | Belongs to User | Single-use; hash stored |
| Role | Role definition (enumerated) | role_id, description | *..* Users | Hierarchy: superadmin > tenant_admin > others |
| Policy | Fine-grained authorization rule | policy_id, version, resource_type, condition_expression, effect, created_by, created_at | Many evaluations (PolicyEvaluationLog) | Evaluation returns ALLOW/DENY/ABSTAIN |
| AuditEvent | Compliance & security log | event_id, tenant_id?, actor_user_id?, action_type, target_ref, metadata (JSON), created_at | Belongs to Tenant (nullable) | Partition/index by created_at + tenant_id |
| Token (conceptual) | Issued auth credential | jti, subject, tenant_id, issued_at, expires_at, scopes[], key_version | N/A | Stateless JWT; revoked tracked separately |
| FeatureFlag | Toggle behavior | flag_key, tenant_id?, status, rollout_rules | Belongs to Tenant (nullable global) | Future advanced targeting |
| KeyRotationRecord | Signing key lifecycle | key_version, activated_at, retired_at?, algorithm, notes | N/A | Overlap window controls acceptance |
| PolicyEvaluationLog | Evaluated authorization decision | eval_id, policy_id, decision, latency_ms, tenant_id, user_id, correlation_id | Belongs to Policy | Used for performance & denial metrics |
| UserMFA | MFA enrollment | user_id, factor_type, enrolled_at, last_used_at, secret_hash/public_key | Belongs to User | Optional table when MFA enabled |

## Field Specifications

### Tenant

- tenant_id: UUIDv5 (primary key) derived from namespace + slug (deterministic idempotent seed)
- name: String (unique, indexed)
- status: Enum(active, soft_deleted)
- config_version: Integer (increments on config-impacting change)
- created_at / updated_at: Timestamps (UTC)
- created_by: user_id FK nullable (system bootstrap)
- updated_by: user_id FK nullable

Indexes:

- (name)
- (status, created_at)

### User

- user_id: UUID PK
- tenant_id: UUID FK -> Tenant.tenant_id (indexed composite (tenant_id, email))
- email: Lowercased string, unique within tenant
- status: Enum(invited, active, disabled)
- password_hash: String (Argon2id) nullable until activation for invited user
- roles: association table user_roles(user_id, role_id)
- last_login_at: Timestamp nullable
- created_at / updated_at: Timestamps
- created_by: user_id FK nullable (seed/system)
- updated_by: user_id FK nullable

Indexes:

- (tenant_id, email) unique
- (tenant_id, status)

### Invitation

- invitation_id: UUID PK
- tenant_id: FK -> Tenant
- email: Lowercase string (not yet a user) – optional uniqueness enforcement per tenant while pending
- token_hash: SHA-256 hex
- expires_at: Timestamp
- accepted_at: Timestamp nullable

Indexes:

- (tenant_id, email)
- (expires_at)

### PasswordResetRequest

- reset_id: UUID PK
- user_id: FK -> User
- token_hash: SHA-256 hex
- issued_at: Timestamp
- expires_at: Timestamp
- consumed_at: Timestamp nullable

Indexes:

- (user_id, expires_at)
- (token_hash) unique (fast lookup)

### Role

- role_id: Enum(superadmin, tenant_admin, analyst, standard, service_account, support_readonly, future domain roles)
- description: Text

### Policy

- policy_id: UUID PK
- version: Integer
- resource_type: String (enum-like or namespaced identifier)
- condition_expression: Serialized logic (DSL or JSON predicate) – initial simple expression structure
- effect: Enum(ALLOW, DENY)
- created_by: user_id FK
- created_at: Timestamp
- updated_at: Timestamp
- updated_by: user_id FK nullable

Indexes:

- (resource_type, effect)
- (created_at)

### AuditEvent

- event_id: UUID PK
- tenant_id: Nullable FK (system/global events)
- actor_user_id: Nullable FK -> User
- action_type: String (categorical e.g., tenant.create, auth.login.failure)
- target_ref: String (resource reference pattern: `tenant:{uuid}` | `user:{uuid}` | `policy:{uuid}`)
- metadata: JSONB (structured; redaction ensures secrets not stored)
- created_at: Timestamp (append-only; no updated_at/updated_by by design)

Indexes:

- (tenant_id, created_at)
- (action_type, created_at)
- (correlation_id) via metadata extraction or separate column if needed

### FeatureFlag

- flag_key: String PK (composite with tenant_id when tenant scoped)
- tenant_id: Nullable FK
- status: Enum(enabled, disabled)
- rollout_rules: JSONB (array of targeting rules, initial minimal)
- created_at / updated_at: Timestamps
- created_by: user_id FK nullable
- updated_by: user_id FK nullable

Indexes:

- (tenant_id, flag_key)
- (status)

### KeyRotationRecord

- key_version: Integer PK
- activated_at: Timestamp
- retired_at: Timestamp nullable
- algorithm: String
- notes: Text nullable
- created_at: Timestamp (activation time)
- created_by: user_id FK nullable (system automation)

### PolicyEvaluationLog

- eval_id: UUID PK
- policy_id: FK -> Policy
- decision: Enum(ALLOW, DENY, ABSTAIN)
- latency_ms: Integer
- tenant_id: UUID FK
- user_id: UUID FK
- correlation_id: String
- created_at: Timestamp (index ordering)
- (Actor captured via user_id; separate created_by not required – rationale: evaluation rows are system outputs tied to invoking user.)

Indexes:

- (policy_id, created_at)
- (tenant_id, created_at)
- (decision, created_at)

### UserMFA

- user_id: FK PK (one row per factor type or composite with factor_type)
- factor_type: Enum(totp, webauthn)
- enrolled_at: Timestamp
- last_used_at: Timestamp nullable
- secret_hash / credential_public_key: String / binary
- created_at: Timestamp
- created_by: user_id FK nullable

## Association Tables

- user_roles(user_id UUID FK, role_id Enum, PRIMARY KEY(user_id, role_id))
- role_permissions(role_id Enum, permission_code String) (optional initial mapping if permissions enumerated)
- policy_tenants (if a policy can apply to multiple tenants in future; not initial scope)

## State Transition Summaries

- User: invited -> active (on invitation acceptance), active -> disabled (admin action), disabled -> active (re-enable).
- Tenant: active -> soft_deleted (admin), soft_deleted -> active (restore).
- PasswordResetRequest: issued -> consumed (completion) or expired (time).
- Invitation: pending -> accepted or expired.
- KeyRotationRecord: new version added; old version becomes retired_at when grace ends.

## Validation & Domain Rules

- Emails normalized (lowercase, trimmed). Duplicate within same tenant blocked.
- Password hashes always Argon2id; rehash if parameters outdated.
- Policy condition_expression validated (no arbitrary code execution; whitelist limited operators).
- AuditEvent metadata must pass redaction pre-save (enforced in adapter layer).

## Redaction Notes

Sensitive metadata keys replaced with `REDACTED` prior to persistence if accidentally present (defense-in-depth).

## Performance Considerations

- High-write tables: AuditEvent, PolicyEvaluationLog – require partitioning/index strategy (future ADR).
- Latency tracking: store latency_ms integer for evaluation optimization.
- Avoid cascade deletes; use soft delete & background cleanup tasks (future).
  - Exception Rationale (Phase 3 Planning Alignment): Limited ON DELETE CASCADE may be applied ONLY to:
    - Ephemeral token state tables (e.g., password_resets) where rows lose meaning immediately when parent (User) is physically purged in explicit maintenance scenarios.
    - Pure association/bridge tables (e.g., user_roles) to prevent orphan join rows and reduce maintenance complexity.
  - All high-volume or auditable domain tables (tenants, users, policies, policy_eval_logs, audit_events, feature_flags) continue to use RESTRICT + logical (soft) delete semantics to avoid accidental large fan-out deletions and to preserve performance predictability under heavy write load.
  - This clarification ensures the Phase 3 FK & Cascade Matrix does not contradict the overarching performance guidance; cascades are constrained to low-cardinality, low-write, operationally trivial relations.

## Open Questions (Deferred)

None for initial scope (covered by clarifications). Future: partitioning strategy, policy DSL extensibility.

---

## Phase 3 Addendum: Persistence Foreign Keys, Cascades & Key Management

This addendum aligns the domain data model with the Phase 3 persistence plan (see `plan.md` Physical Mapping & FK policy tables). It introduces explicit foreign key semantics, logical vs physical cascade strategy, and clarifies which relationships are enforced at the DB vs domain layer.

### Foreign Key & Cascade Matrix

| Relationship | Physical FK | ON DELETE (DB) | Logical (Domain) Behavior | Notes |
|--------------|-------------|----------------|---------------------------|-------|
| users.tenant_id → tenants.tenant_id | Yes | RESTRICT | Tenant soft delete hides users; hard delete not routine | Protects cross-table integrity; no orphan users. |
| invitations.tenant_id → tenants.tenant_id | Yes | RESTRICT | Cleanup job removes stale invites if tenant soft_deleted | Avoids accidental loss; invites ephemeral. |
| password_resets.user_id → users.user_id | Yes | CASCADE | User soft delete invalidates outstanding resets | Physical cascade acceptable (tokens meaningless post-delete). |
| user_roles.user_id → users.user_id | Yes | CASCADE | Role entries removed if user physically purged (rare) | Normal flows use soft delete only. |
| user_roles.tenant_id → tenants.tenant_id | Yes | RESTRICT | Tenant soft delete preserves assignments for audit | Historical role evidence retained. |
| policies.tenant_id → tenants.tenant_id | Yes | RESTRICT | Policies retained; may be archived if tenant archived | Required for compliance rollback references. |
| policy_eval_logs.tenant_id → tenants.tenant_id | Yes | RESTRICT | Logs retained unless regulated purge required | Append-only; high volume. |
| feature_flags.tenant_id → tenants.tenant_id | Yes | RESTRICT | Tenant soft delete disables evaluation path | Prevents silent toggle removal. |
| audit_events.tenant_id → tenants.tenant_id | Yes | RESTRICT | Immutable audit persists | No cascade ever. |
| password_resets.user_id → users.user_id | Yes | CASCADE | Redundant entry (see above) | Consolidated for clarity. |
| token_replays (hashed_jti) | No | N/A | TTL cleanup independent of FK constraints | Performance / simplicity. |
| key_rotations.key_version (sequence) | Unique key only | N/A | Retired versions pruned after grace | Not tenant-scoped. |

"Logical cascade" means the application enforces soft delete semantics (status flags) and background cleanup rather than DB-level ON DELETE CASCADE to avoid silent large-scale data removal.

### Soft Delete Strategy

| Entity | Soft Delete Field | Physical Delete Trigger | Justification |
|--------|-------------------|-------------------------|--------------|
| Tenant | status=soft_deleted | Manual migration / admin tool | Ensures reversible isolation before irreversible purge. |
| User | status=disabled (not a full delete) | (Future) explicit purge task | Keeps audit references & evaluation logs valid. |
| FeatureFlag | status=disabled | Rare manual removal | Historical feature state for debugging retained. |

Other entities (invitations, password_resets) are inherently ephemeral—expiration or consumption drives deletion via maintenance job.

### Index Naming Conventions (Persistence Alignment)

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `pk_<table>` | pk_users |
| Foreign Key | `fk_<from>_<to>` | fk_users_tenant_id_tenants |
| Unique | `uq_<table>_<cols>` | uq_users_tenant_id_email |
| Standard Index | `ix_<table>_<col>` | ix_users_tenant_id_status |
| Composite Index | `ix_<table>_<col1>_<col2>` | ix_policies_tenant_id_resource_type |

Deterministic naming ensures migration diffs are reviewable, aligning with migration safety gate.

### Encryption & Key Management Alignment

| Asset | Scope | Persistence | Rotation / Change Path | References |
|-------|-------|------------|-------------------------|------------|
| JWT Signing Keys | Auth boundary | External secret / file ref | Dual-key overlap, grace removal | FR-022, C-028 |
| Password Hash Parameters | Auth core | Config descriptor | Rehash on login when outdated | FR-051, C-033 |
| Deterministic Namespace UUID | Global constant | Code constant | Immutable | C-038 |
| Seed Deterministic IDs | Global | Derived (UUIDv5) | Immutable | C-009, C-038 |
| Future DEKs (data encryption keys) | Deferred | N/A | Requires ADR (not Phase 3) | (Future) |

### Migration Safety Notes

- All destructive operations (DROP COLUMN / TABLE) require explicit approval comment and ADR reference.
- Initial revision introduces only additive, non-destructive objects; subsequent destructive changes must be accompanied by rollback plan.
- Migration head reported via health endpoint enabling drift detection (FR-015).

### Additional Governance Hooks

- Critical path coverage list will include `adapters/persistence/*` & `alembic/versions/*` once IMPL-DB-13 complete.
- Slow query threshold (`DB_SLOW_QUERY_THRESHOLD_MS`) documented in config descriptor and enforced in metrics logging path.

### Open Questions (Phase 3 Forward-Looking)

| Topic | Description | Planned Resolution Mechanism |
|-------|-------------|------------------------------|
| Partitioning | When to partition high-volume logs | Future ADR after volume telemetry baseline |
| Policy Eval Log Retention | How long to retain evaluation logs | Configurable retention + archival ADR |
| Encrypted Columns | Selective encryption for PII fields | Encryption ADR (deferred) |

