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

## Open Questions (Deferred)

None for initial scope (covered by clarifications). Future: partitioning strategy, policy DSL extensibility.
