# Feature Specification: Modern Enterprise-Grade Multi-Tenant FastAPI Backend

**Feature Branch**: `001-modern-enterprise-grade`  
**Created**: 2025-10-02  
**Status**: Draft  
**Input**: User description: "modern enterprise-grade multi-tenant FastAPI backend with interchangeable data & infrastructure layers, rigorous RBAC, and test-first delivery"

## Execution Flow (main)

```text  


1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines

- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation

When creating this spec from a user prompt:

1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make

2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies  
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a platform superadmin, I can provision a new tenant, configure its base roles and policies, and immediately allow tenant administrators to invite users who then authenticate and perform authorized domain actions, all while the system enforces strict tenant isolation and produces auditable security events.

### Acceptance Scenarios

1. **Given** no tenant exists, **When** superadmin creates tenant A with default role set, **Then** tenant A is persisted, emits an audit event, and is returned with generated tenant_id.
2. **Given** tenant A exists, **When** tenant_admin invites a user via email, **Then** an invitation token is created, email dispatch event recorded, and pending user is visible only within tenant A.
3. **Given** a pending invitation, **When** invited user accepts and sets credentials (or federated identity), **Then** user status transitions to active, RBAC roles applied, audit logged.
4. **Given** user with role analyst in tenant A, **When** they request resources belonging to tenant B, **Then** access is denied with standardized error envelope and denial audit event.
5. **Given** superadmin, **When** they perform a cross-tenant diagnostic query (explicit cross_tenant=true), **Then** request succeeds, results contain multiple tenant_ids, and cross-tenant access is logged.
6. **Given** performance baseline defined, **When** 1000 concurrent auth token validations occur, **Then** p95 latency < 50ms and no tenant leakage.
7. **Given** key rotation event, **When** new tokens issued, **Then** old tokens remain valid until grace window ends, rotation audit exists.
8. **Given** API v1 endpoints, **When** a backward incompatible change is proposed, **Then** a deprecation notice appears in responses before change activation.
9. **Given** DEPLOY_MODE=monorepo, **When** the system starts, **Then** backend serves built frontend assets and only FRONTEND_/SHARED_ scoped variables are exposed to the client.
10. **Given** DEPLOY_MODE=backend-only, **When** the system starts, **Then** static asset serving is disabled and no frontend-only variables appear in diagnostics.
11. **Given** a newly added required config variable missing from runtime, **When** startup runs, **Then** process exits non-zero with aggregated config error report.
12. **Given** a variable outside descriptor, **When** drift detection runs, **Then** an anomaly audit event is persisted.
13. **Given** password hashing parameters are strengthened (e.g., higher memory cost), **When** an existing user logs in with a valid password hashed under old parameters, **Then** authentication succeeds and the stored hash is transparently upgraded and audited.
14. **Given** an approved embed origin, **When** an embedded client initiates session establishment, **Then** a short-lived embed token is exchanged and a secure session cookie (SameSite=None; Secure; HttpOnly) is set and audit logged with origin.
15. **Given** a disallowed embed origin, **When** it attempts to load embedded content, **Then** the request is rejected with an explicit policy denial and no session cookie issued.
16. **Given** a fresh developer environment with only required language runtime installed, **When** the bootstrap command is executed, **Then** a minimal stack launches using mocks for optional services (e.g., cache, email) and reports readiness.
17. **Given** a user without MFA enabled, **When** they request a password reset and submit a valid reset token with new password, **Then** password is updated, token invalidated, active sessions revoked, and event audited.
18. **Given** a user with MFA enabled, **When** they perform password reset using valid reset token and correct MFA challenge, **Then** password is updated, token invalidated, sessions revoked, and both reset + MFA success are audited.
19. **Given** a tenant_admin in tenant A, **When** they perform a standard tenant-scoped action (e.g., update tenant A display name) without an explicit granular RBAC grant, **Then** the action succeeds and is audited as implicit_tenant_admin_allow.
20. **Given** a tenant_admin in tenant A, **When** they attempt to create a superadmin user, **Then** the action is denied with error code role_forbidden and audited.
21. **Given** initial system bootstrap, **When** the seed script runs on an empty database, **Then** TestTenant plus one superadmin, one tenant_admin, and one standard user are created idempotently.
22. **Given** logging configured with LOG_LEVEL=INFO and JSON format, **When** a standard API request completes, **Then** a single structured log line contains timestamp, level, correlation_id, request_id, tenant_id (nullable), user_id (nullable), path, method, status, latency_ms, and no secret fields.
23. **Given** an audit user requests a log export for tenant A between two timestamps with category=security, **When** export executes, **Then** only matching events are returned, sensitive fields are redacted, and an export audit event is recorded.
24. **Given** performance test results show p95 latency exceeding 200ms threshold for a CRUD endpoint, **When** results are ingested, **Then** a performance.regression event is emitted and visible in metrics/logs.
25. **Given** a release cycle boundary, **When** the OWASP dynamic security test suite runs, **Then** results (pass/fail counts and high severity findings) are recorded and failing high severity findings block release until remediated or explicitly waived.
26. **Given** a merge attempt into main, **When** code quality metrics show duplication >= 8% overall or any file duplication >= 15% or any function complexity > 10 without a justification marker, **Then** the merge is blocked and a metrics_violation report is generated.

### Edge Cases

- Tenant soft deleted: active sessions referencing tenant must be invalidated gracefully.
- Invitation reuse: second attempt with same token after acceptance returns idempotent success (no duplicate account).
- Superadmin misuse: repeated cross-tenant access > threshold triggers alert event.
- Stale policy cache: policy changes propagate atomically; stale evaluator rejects with retryable error if version mismatch.
- Large tenant (10k users) pagination must remain performant (< 200ms p95 list users).
- Simultaneous tenant creation name collision (race) resolves with constraint violation mapped to user-friendly error.
- Token replay attempt detected via nonce store results in immediate token revocation and security audit escalation.
- Mis-scoped variable: FRONTEND_ variable present but not in descriptor triggers a warning and recommendation.
- Unauthorized scope: BACKEND_ variable requested by frontend build is stripped and build fails clearly.
- Drift detection: Extra or missing descriptor key logs anomaly event.
- Deploy mode mismatch: DEPLOY_MODE=frontend-only while backend process invoked causes startup abort.
- Password hash parameter upgrade: login after parameter change triggers transparent rehash using new parameters without forcing password reset.
- Unapproved embed origin: iframe load attempt from non-allowlisted domain is blocked and audited as security_denied_origin.
- Password reset token reuse: second attempt after successful reset returns invalid_token without leaking whether reset succeeded.
- MFA state change mid-reset: if user enables MFA after token issuance but before completion, completion requires MFA challenge.
- Tenant admin implicit scope: removing an explicit grant does not remove access to baseline tenant operations.
- Tenant admin escalation attempt: tenant_admin attempting to assign superadmin role is denied and audited.
- Seed idempotency: rerunning seed script does not duplicate TestTenant or baseline users.
- Log export size bound: request exceeding max window or size limit returns partial export with explicit boundary indicator.
- Redaction violation: detection of raw secret in log triggers redaction_violation audit and metric increment.
- Performance regression false positive: budget breach due to configuration anomaly flagged and linked to configuration hash for triage.
- Security test waiver: waiver requires explicit justification reference; missing justification blocks release.

## Clarifications

All previously implicit or ambiguous parameters are now explicitly defined to remove planning uncertainty. Each clarification ID (C-###) can be referenced by functional requirements, implementation tasks, and tests. No open clarification items remain at this time.

### Session 1 – Resolved (Defaults Applied)

- **C-001 Password Policy (FR-009)**: Minimum length 12; must include at least 1 letter and 1 digit. Optional advanced complexity (require 3 of 4 classes: upper, lower, digit, symbol) may be enabled via configuration flag `PASSWORD_COMPLEXITY_STRICT=false` (default false for developer friendliness). Maximum accepted length 128 to prevent abuse.
- **C-002 Rate Limits (FR-023, FR-058)**: Auth endpoints default limits: per-tenant 500 req/min, per-IP 50 req/min; burst smoothing via leaky bucket. Embedded context has independent bucket with same defaults unless `EMBED_RATE_LIMIT_SCALE` applied. Lockout escalation for repeated 429s is deferred (future feature) to keep initial developer experience simple.
- **C-003 Performance Load Profile (FR-027, FR-074)**: Reference dataset ≥10k users, ≥50k audit events, representative policies (≥25), invitations (≥1k). Concurrency tiers: light 25, reference 100 (budget enforced), stress 300 (informational). CRUD budgets: p95 < 200ms, p99 < 400ms. Heavy operations (exports, bulk policy load) informational targets p95 < 400ms, p99 < 800ms (regression triggers per FR-074 thresholds).
- **C-004 Key Rotation Grace (FR-022)**: Default overlap 15 minutes (shortened from earlier informal 24h concept for simpler ops) – adjustable via `KEY_ROTATION_GRACE_MINUTES`. Dual verification path active during overlap only.
- **C-005 Logging Configuration (FR-071)**: Allowed formats: json, text. Allowed sinks: stdout (default), file, otlp. Required base fields: timestamp, level, message, correlation_id, request_id, tenant_id (nullable), user_id (nullable), path (when HTTP), method (when HTTP), status (when HTTP), latency_ms (when HTTP). Additional opt-in fields via `LOG_FIELDS_EXTRA` (comma list) validated against allowlist (e.g. ip, user_agent).
- **C-006 Log Export Bounds (FR-072)**: Time window ≤ 24h, maximum uncompressed size 100MB. If size exceeded mid-stream, export truncates at record boundary and includes `truncated=true` plus `reason=size_limit` metadata.
- **C-007 Redaction Set (FR-073)**: Case-insensitive key match for: password, password_hash, passwd, token, access_token, refresh_token, secret, api_key, authorization, set-cookie, mfa_secret, email (hashed variant stored), pii_hint. Values replaced with `REDACTED`. Redaction violations emit `redaction_violation` audit event.
- **C-008 Password Reset Token (FR-060–FR-065)**: Expiry default 30 minutes; single-use; stored as SHA-256 hash; attempts after consumption or expiry return uniform `invalid_token` response without enumeration of success state.
- **C-009 Seed Baseline (FR-069, FR-052)**: Deterministic TestTenant slug `test-tenant` with UUIDv5 derived from a fixed namespace + slug; baseline users (superadmin, tenant_admin, standard) also use deterministic UUIDv5 (namespace + normalized email). Reruns are idempotent (upsert by deterministic identifiers). Hash parameters may upgrade on seed rerun.
- **C-010 Role Hierarchy (FR-066–FR-068)**: Predefined roles: superadmin, tenant_admin, analyst, standard. Only superadmin may grant/revoke superadmin or tenant_admin. Implicit tenant_admin allowances exclude destructive purge and cross-tenant actions.
- **C-011 Code Quality Thresholds (FR-070, FR-076)**: Duplication overall < 8%; any single file duplication < 15%; cyclomatic complexity ≤ 10 per function. Justification marker pattern: `JUSTIFY:<ID>` inline comment adjacent to function or block. CI fails if metrics exceed thresholds without matching justification ID recorded in a justification registry artifact (to be defined in planning phase) – keeps developer friction low while enabling exceptions.
- **C-012 Embed Mode (FR-053–FR-059)**: Default origin allowlist empty in non-dev; in dev mode (`DEV_MODE=true`) wildcard `http://localhost:*` allowed. Embed token TTL default 5 minutes; non-refreshable; exchange invalidates token. Separate rate limit bucket label `embed`.
- **C-013 Performance Regression Events (FR-074)**: Trigger conditions: CRUD p95 ≥ 200ms OR p99 ≥ 500ms; heavy ops p95 ≥ 400ms OR p99 ≥ 800ms; only if outside declared maintenance window (`MAINT_WINDOW_ACTIVE=false`). Event payload includes configuration hash to disambiguate environment anomalies.
- **C-014 Configuration Descriptor Mutation (FR-044, FR-048)**: Attempted mutation raises error with code `config_immutable`. Direct `os.environ` access in app layer is flagged by static rule; single exception allowed inside configuration bootstrap module.
- **C-015 Minimal Hardware Assumption (General)**: Developer baseline: 4 CPU cores, 8GB RAM, SSD storage. All bootstrap and reference performance requirements scoped to this minimum to remain accessible.
- **C-016 Security Testing Cadence (FR-075)**: OWASP dynamic suite executes per release cycle boundary (tag or main merge). Waiver requires `WAIVER:<ID>` reference plus risk justification artifact.
- **C-017 Rate Limit Configuration Source (FR-023, FR-058)**: All rate limit parameters reside in centralized configuration (no inline constants) supporting environment overrides without code changes.
- **C-018 Justification Registry (FR-070, FR-076)**: Stored as machine-readable YAML (`quality_justifications.yml`) mapping JUSTIFY IDs to rationale, owner, expiry date to avoid permanent degradation.
- **C-019 Audit Metadata Fields (FR-077)**: Mutable entities (Tenant, User, Policy, FeatureFlag) require created_at, created_by, updated_at, updated_by; append-only entities (AuditEvent, KeyRotationRecord, PolicyEvaluationLog) record created_at & actor context only. Any exception must be explicitly justified in data-model.md.
- **C-020 Replay Detection Strategy (FR-028, FR-033)**: JWT `jti` (UUIDv4) stored as SHA-256 hash in revocation/replay store with TTL = token_expiry + 10% buffer. Replay = second validation attempt with same jti after revocation or previously seen jti; triggers security.audit token_replay_detected + immediate revocation. Eviction: TTL pruning + approximate LRU under memory pressure; expired entries removed only after TTL to reduce false negatives.
- **C-021 OIDC Stub Scope (FR-007)**: Initial OIDC provider stub limits to discovery (fetch & cache metadata) + ID token signature/claim validation for already obtained tokens; no full authorization code exchange implemented in Phase 2 (explicit backlog). Downstream principal normalization limited to subject + email claims.
- **C-022 Regression Evaluation Window (FR-074)**: Performance regression detector evaluates rolling window of last 5 minutes (or ≥100 samples, whichever larger) before emitting performance.regression to reduce false positives from transient spikes. Window size configurable via `PERF_REGRESSION_WINDOW_MINUTES`.
- **C-023 Hashing Algorithm Exclusivity (FR-049, FR-051)**: Argon2id is the ONLY supported password hashing algorithm; bcrypt (passlib) dependency removed to reduce attack surface and ambiguity. Any future alternative hash introduction requires new clarification ID and migration plan.
**C-024 Pluggable Auth Provider Deferral (FR-007, FR-061, FR-062)**: Authentication provider architecture ships in Phase 2 with ONLY the password provider enabled. OIDC / external SSO and advanced MFA provider implementations are explicitly deferred (DEFER-AUTH-15/16, DEFER-MFA-ENROLL). The interface & registry MUST NOT assume password semantics; adding a new provider later MUST require no changes to existing password provider logic or downstream authorization code. Tests cover registry integrity & MFA conditional branching only (no external IdP flows).
**C-025 Tenant Non-Destructive Update Scope (FR-001)**: "Update (non-destructive)" allows modifying: display name, metadata fields, feature flag defaults, and soft deletion state. Prohibited (new FR required): hard delete, tenant_id reassignment, cross-tenant resource reassociation, irreversible purges. Out-of-scope attempts emit error code `tenant_update_forbidden` and audit denial.
**C-026 Admin Defense-in-Depth Layers (FR-036)**: Protected admin endpoints MUST enforce gates: (1) Authentication (principal) (2) Role check (superadmin OR tenant_admin in-scope) (3) Policy evaluation (DENY overrides) (4) Explicit admin scope indicator (header `X-Admin-Action: true` or endpoint-specific flag) (5) Audit emission with scope_reason. Missing any layer → 403 `admin_scope_missing_layer`.
**C-027 Token Revocation / Validation Log Fields (FR-028)**: Each revocation or failed validation log/audit event MUST include: correlation_id, hashed_jti, tenant_id (nullable), user_id (nullable), reason (`user_logout|rotation|replay_detected|expired|invalid_signature|unknown_jti`), key_version (if applicable). `hashed_jti = hex(SHA256(jti))`. Adding a new reason requires a new clarification ID + test. Sensitive claim data excluded or redacted.
**C-028 Key Rotation Dual Validation Strategy (FR-022)**: During grace both old & new signing keys (KID-distinguished) are accepted; validator attempts verification using active keys newest-first. After grace expiry retired key removed. Audit event fields: previous_active_kid, new_active_kid, grace_minutes, initiated_by, expires_at.
**C-029 Tenant Configuration Export Format (FR-035)**: Export bundle = deterministic gzip tar `tenant-config-{tenant_id}-{version}.tar.gz` containing: `roles.json`, `policies.json` (versioned entries), `feature_flags.json`, `metadata.json` (export_version, generated_at, sha256 hash of concatenated sorted file contents). Integrity = SHA256(lowercase hex). Adding new files requires including them in hash computation.
**C-030 Per-Tenant Metrics Enumeration (FR-016)**: Minimum required metrics exposed (per tenant and global aggregation where applicable) via `/metrics` (Prometheus) and internal snapshot: `active_users`, `auth_failures_total`, `policy_denials_total`, `rate_limit_hits_total`, `config_drift_events_total`, `performance_regressions_total`. Each counter/histogram name MUST include tenant label `tenant_id` when not global. Adding a new metric requires documentation update & test assertion.
**C-031 Error Envelope Schema (FR-017)**: Standard error response body: `{ "trace_id": str, "correlation_id": str, "code": str, "message": str, "details": object|null, "docs_url": str|null }`. `trace_id` aligns with tracing system; `correlation_id` echoes request header; no stack traces or internal exception strings included. Tests MUST assert absence of extraneous keys and presence of required fields.
**C-032 Role Downgrade Invalidation Mechanism (FR-021)**: Each session token embeds `session_version`. User record maintains current `session_version`. Role downgrade increments version and persists change; validator rejects tokens whose embedded version < current within ≤60s. A transient allow window (max 60s) is implemented by immediate version bump + optional async revocation for long-lived refresh tokens.
**C-033 Password Hash Upgrade Audit (FR-051)**: On successful login where `needs_rehash` is True, system MUST rehash and emit audit event `auth.password.hash_upgraded` with fields: `user_id`, `old_time_cost`, `new_time_cost`, `old_memory_cost`, `new_memory_cost`, `algorithm="argon2id"`.
**C-034 Bootstrap Duration Measurement (FR-052)**: Bootstrap command logs structured line category `infra.bootstrap` with `duration_ms`, `success=true|false`, `service_count`, and `config_hash`. Acceptance: `duration_ms < 120000` on baseline hardware (C-015). Test reads log output and asserts threshold.
**C-035 Embed vs Primary Rate Limit Response (FR-058)**: Distinct response headers: `RateLimit-Context: embed|primary`. When exceeded, embed context returns error code `embed_rate_limited`; primary returns `rate_limited`. Shared headers: `RateLimit-Limit`, `RateLimit-Remaining`, `Retry-After` (optional). Logging differentiates via context label.
**C-036 OIDC Deferral Assertion (FR-007)**: Until OIDC tasks exit DEFERRED state, auth provider registry MUST contain only `password`. Introduction of any additional provider name MUST be coupled with enabling tasks and new tests citing this clarification.
**C-037 Config Hash Secret Omission Rule (FR-043, FR-071)**: Hash input only includes descriptor entries with `secret=false`. Additionally, env vars with prefix `SECRET_` are forcibly excluded even if descriptor misconfigured. Secrets are never hashed nor logged. Prevents accidental disclosure via configuration hash.
**C-038 Deterministic Namespace UUID (FR-069)**: Fixed namespace UUID constant `9b4f53c4-2e74-5e5b-9e33-3d4c0fd84c11`. Deterministic entity IDs use `UUIDv5(namespace, normalized_identifier)`; normalization = lowercase + trim. C-009 references this constant for tenant & seed user IDs.
**C-039 Policy Extension Registry Shape (FR-038)**: Registry entry: `resource_type` (str), `predicate_ref` (import path), `version` (semver), `created_at` (timestamp). Unique constraint (resource_type, version). Duplicate registration raises `extension_conflict` and is audited. Removal requires future clarification.

**C-040 Superadmin Cross-Tenant Misuse Threshold (FR-002 Edge Case)**: An alert/audit event `security.superadmin_cross_tenant_suspect` MUST be emitted if a single superadmin performs >5 cross-tenant data access operations (reads or writes) within any rolling 10 minute window outside maintenance mode. A Prometheus counter `superadmin_cross_tenant_suspect_total{superadmin_id}` increments once per breach per window; subsequent breaches require the count to drop below threshold then exceed again. Threshold & window configurable via `SUPERACTION_ALERT_THRESHOLD` (default 5) and `SUPERACTION_ALERT_WINDOW_MINUTES` (default 10). Reset logic evaluated every request. Optional future adaptive heuristics require new clarification.

**C-041 Policy Dry-Run Response & Rationale Codes (FR-012, FR-020)**: Dry-run endpoint response schema:

```json
{
   "decision": "ALLOW|DENY|ABSTAIN",
   "rationale_code": "policy_not_found|explicit_deny|implicit_allow|condition_mismatch|no_applicable_policy",
   "matched_policies": [ {"policy_id": "string", "version": 1, "effect": "ALLOW"} ],
   "evaluation_trace": [ {"policy_id": "string", "step": "predicate_eval", "result": "match"} ],
   "latency_ms": 3.42
}
```

`evaluation_trace` only present when query param `verbose=1`. `rationale_code` enumeration above MUST be asserted by contract tests; adding a new code requires a new clarification ID.

**C-042 Performance Endpoint Classification (FR-027)**: “Standard CRUD endpoints” = tenant/user create, update (non-destructive), soft delete/restore, list/list-with-pagination for Users, Tenants, FeatureFlags, Policies (excluding export, bulk import, configuration bundle, audit/export operations). “Heavy operations” = configuration export, log export, audit query (spanning > 1000 events), policy bulk registration, performance regression scan, seed/bootstrap. Classification table MUST appear in developer docs; tests tag endpoints for latency grouping to ensure correct budget evaluation.

**C-043 Seed Script Error Modes (FR-025)**: Exit codes: 0 success (idempotent or initial), 2 partial seed (recoverable—e.g., one baseline user missing then created), 3 fatal (irrecoverable constraint mismatch requiring manual intervention). On conflict (existing deterministic UUID with divergent immutable attributes) the script logs `seed.conflict` audit event and skips mutation (non-fatal). A summary JSON line `infra.seed.summary` includes counts: created, skipped, upgraded (password hash), conflicts, duration_ms. Re-running MUST not increase `created` count after first successful seed.

**C-044 Policy Evaluation Latency Histogram (FR-034)**: Metric: `policy_evaluation_latency_seconds{tenant_id}` (histogram) with buckets (seconds): 0.001,0.005,0.01,0.02,0.05,0.1,0.25,0.5,1,2. Companion counter: `policy_evaluations_total{tenant_id,decision}`. 95th & 99th percentiles derived via Prometheus queries documented. Tests assert bucket presence and at least one observation after simulated evaluations.

**C-045 Aggregated Configuration Error Report Format (FR-041)**: On startup failure due to config validation, STDERR (and structured log) emits single JSON object:

```json
{
   "error": "configuration_validation_failed",
   "config_hash": "<non_secret_hash_or_null>",
   "issues": [
      {"name": "BACKEND_DB_URL", "error": "missing", "expected_type": "str"},
      {"name": "FRONTEND_PUBLIC_ORIGIN", "error": "invalid_format", "expected_type": "url"}
   ]
}
```

`issues` sorted lexicographically by `name`. Process exit code = 1.

**C-046 Embedded vs Primary Rate Limit Precedence (FR-058)**: Two evaluations performed: (1) context bucket (embed or primary) (2) global per-tenant bucket. If either exceeds limit the request is rejected. Preference of error code: if context=embed AND its bucket exceeded → `embed_rate_limited`; else `rate_limited`. Headers returned:
`RateLimit-Limit`, `RateLimit-Remaining`, and context-specific `RateLimit-Context-Limit`, `RateLimit-Context-Remaining`. Both reflect post-decrement state. When both exceeded simultaneously in embed context, a single rejection with embed code is emitted; metrics increment for both buckets.

**C-047 Embed Documentation Artifact (FR-059)**: Generated file `docs/embed/guide.md` produced by embed docs generator task; includes sections: Overview, Origin Allowlist, Token Exchange, Cookie Attributes, CSP & frame-ancestors examples, Rate Limit Headers, Error Codes. CI check ensures file updated if embed-related clarifications change (hash compare of relevant clarifications text). Missing or stale file blocks merge.

**C-048 Redaction Violation Metric (FR-073)**: Metric name `redaction_violations_total{tenant_id, key}` (counter). Emitted once per request containing at least one unredacted sensitive key; multiple keys produce multiple increments (distinct label cardinality). Audit event `security.redaction_violation` includes offending keys list (capped length 10, else truncated=true flag). Tests assert metric increment & audit emission on synthetic violation.

**C-049 Rationale Code Enumeration Reference (FR-012)**: Policy evaluation (non-dry-run) responses embedding denial rationale use `rationale_code` values from C-041 enumeration. Implementation MUST NOT leak raw condition expressions. Adding rationale requires new clarification.

**C-050 API Implementation Ordering vs DB & Seed (FR-024, FR-025, FR-052, FR-069)**: Phase 2 API endpoints (health, auth, tenant/user CRUD, policy, feature flags, embed, metrics, audit query) MUST be implemented and validated against in-memory repositories BEFORE introducing a real database layer. Rationale: preserves test speed and enables contract tests early. The persistent database integration (and migration layer) is deferred to Phase 3; the seed script (FR-025 / FR-069) producing durable baseline data executes only after the real persistence adapter is added. Until then, any test data “seeding” occurs via test fixtures/factories in memory—no bootstrap seed required for Phase 2 runtime. Bootstrap command (FR-052) in Phase 2 operates without a DB by wiring in-memory stores; its responsibility is environment/config readiness, not durable data population. Introducing DB earlier than specified requires a new clarification ID documenting impact on test strategy and performance budgets.

### Traceability Mapping (Selected)

| Clarification | Related FRs |
|---------------|-------------|
| C-001 | FR-009 |
| C-002 | FR-023, FR-058 |
| C-003 | FR-027, FR-074 |
| C-004 | FR-022 |
| C-005 | FR-071, FR-072, FR-073 |
| C-006 | FR-072 |
| C-007 | FR-073 |
| C-008 | FR-060–FR-065 |
| C-009 | FR-069, FR-052 |
| C-010 | FR-066–FR-068 |
| C-011 | FR-070, FR-076 |
| C-012 | FR-053–FR-059 |
| C-013 | FR-074, FR-027 |
| C-014 | FR-044, FR-048 |
| C-015 | FR-052, FR-027 |
| C-016 | FR-075 |
| C-017 | FR-023, FR-058 |
| C-018 | FR-070, FR-076 |
| C-019 | FR-077 |
| C-020 | FR-028, FR-033 |
| C-021 | FR-007 |
| C-022 | FR-074 |
| C-023 | FR-049, FR-051 |
| C-024 | FR-007, FR-061, FR-062 |
| C-025 | FR-001 |
| C-026 | FR-036 |
| C-027 | FR-028 |
| C-028 | FR-022 |
| C-029 | FR-035 |
| C-030 | FR-016 |
| C-031 | FR-017 |
| C-032 | FR-021 |
| C-033 | FR-051 |
| C-034 | FR-052 |
| C-035 | FR-058 |
| C-036 | FR-007 |
| C-037 | FR-043, FR-071 |
| C-038 | FR-069 |
| C-039 | FR-038 |
| C-040 | FR-002 |
| C-041 | FR-012, FR-020 |
| C-042 | FR-027 |
| C-043 | FR-025 |
| C-044 | FR-034 |
| C-045 | FR-041 |
| C-046 | FR-058 |
| C-047 | FR-059 |
| C-048 | FR-073 |
| C-049 | FR-012 |
| C-050 | FR-024, FR-025, FR-052, FR-069 |

### Open Items

None at this time. Future ambiguities will be appended with next available ID (C-050+).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow superadmin to create, update (non-destructive), and soft delete tenants.
- **FR-002**: System MUST enforce tenant isolation on all data queries (implicit tenant filter) except explicit superadmin cross-tenant actions.
- **FR-003**: System MUST provide reusable auth module supporting JWT-based auth with extension points for OIDC and opaque tokens.
- **FR-004**: System MUST implement role-based access control with policy registration API for domain modules.
- **FR-005**: System MUST audit all security-sensitive events (tenant create, role assignment, cross-tenant access, key rotation, failed privilege escalation, policy change).
- **FR-006**: System MUST support user invitation lifecycle: invite → accept → activate.
- **FR-007**: System MUST allow password-based login and provide a pluggable authentication provider architecture (only password provider shipped in Phase 2; OIDC / other SSO providers added later without core rewrite) (see C-024, C-036).
- **FR-008**: System MUST provide token issuance, validation, refresh, and revocation endpoints.
- **FR-009**: System MUST allow configurable password policy (length, complexity, disallowed substrings). DEFAULT: minimum length 12, at least 1 letter and 1 digit; complexity rules adjustable via configuration layer.
- **FR-010**: System MUST expose endpoint to list tenant users with pagination, filtering, and role-based column restrictions.
- **FR-011**: System MUST implement superadmin cross_tenant access gating with explicit query parameter and audit reason.
- **FR-012**: System MUST enforce policy evaluation returning ALLOW/DENY with rationale code for denial responses.
      - (See C-041, C-049 for rationale enumeration & dry-run response schema.)
- **FR-013**: System MUST maintain idempotency for tenant creation retry (same name within retry window returns original tenant_id).
- **FR-014**: System MUST provide API versioning through URI prefix /v1 and embed deprecation headers when needed.
- **FR-015**: System MUST expose health/status endpoint including migration state and key rotation version.
- **FR-016**: System MUST store and expose per-tenant metrics (active users, auth failures, policy denials) (see C-030) .
- **FR-017**: System MUST implement structured error envelope for all non-2xx responses (see C-031).
- **FR-018**: System MUST support soft delete and restore for users and tenants.
- **FR-019**: System MUST prevent assignment of undefined roles and reject ambiguous role expansion.
- **FR-020**: System MUST support policy dry-run mode (simulate decision) for debugging (response schema & rationale codes per C-041).
- **FR-021**: System MUST invalidate sessions upon role downgrade within max 60 seconds (see C-032).
- **FR-022**: System MUST allow rotating signing keys without downtime (grace overlap window) (DEFAULT grace 15m).
- **FR-023**: System MUST enforce configurable rate limiting on auth endpoints. DEFAULT: 500 requests/minute per tenant + 50 requests/minute per IP (burst tokens allowed via leaky bucket); limits adjustable via configuration.
- **FR-024**: System MUST export OpenAPI documentation with security schemes defined for all protected endpoints.
- **FR-025**: System MUST provide seed script / initialization pathway for first superadmin creation (error modes & idempotency per C-043).
- **FR-026**: System MUST support feature flag evaluation per tenant for future domain modules.
- **FR-027**: System MUST ensure p95 latency < 200ms and p99 < 400ms for standard CRUD endpoints (classification per C-042) under reference load: 100 concurrent users, representative dataset (≥10k users, ≥50k audit events) on production-like hardware.
- **FR-028**: System MUST log all token revocations and failed token validations.
- **FR-029**: System MUST provide a policy registration endpoint (admin-only) for dynamic policy deployment.
- **FR-030**: System MUST ensure policy changes are versioned and can be rolled back.
- **FR-031**: System MUST ensure only superadmin can assign or revoke tenant_admin role.
- **FR-032**: System MUST expose audit query endpoint filtered by tenant and event type with pagination.
- **FR-033**: System MUST detect and reject token replay attempts.
- **FR-034**: System MUST provide instrumentation endpoints/metrics (Prometheus format) including policy evaluation latency distribution (histogram spec per C-044).
- **FR-035**: System MUST allow exporting tenant configuration (roles, policies) as versioned bundle (see C-029).
- **FR-036**: System MUST secure all admin endpoints via defense-in-depth (role + policy + explicit admin scope claim).
- **FR-037**: System MUST provide standardized correlation_id header passthrough.
- **FR-038**: System MUST provide domain extension registry enabling future modules to register resource types.
- **FR-039**: System MUST centralize configuration in a single descriptor enumerating all environment variables (name, scope, type, required, description) and generate an example file.
- **FR-040**: System MUST support DEPLOY_MODE values: monorepo, backend-only, frontend-only, dual.
- **FR-041**: System MUST fail fast with aggregated configuration errors if required variables are missing/invalid (report format per C-045).
- **FR-042**: System MUST enforce scoping so frontend code can only access `FRONTEND_` or `SHARED_` variables.
- **FR-043**: System MUST log a hashed summary (excluding secrets) of effective configuration at startup.
- **FR-044**: System MUST provide immutable configuration objects (attempted mutation raises error).
- **FR-045**: System MUST abort startup if mode behavior contradicts DEPLOY_MODE (e.g., static serve in backend-only).
- **FR-046**: System MUST offer a redacted configuration export command or endpoint.
- **FR-047**: System MUST log and categorize configuration drift (extra/missing keys) with severity.
- **FR-048**: System MUST prohibit direct environment access outside configuration layer (enforced via static scan/CI rule).
- **FR-049**: System MUST hash user passwords using Argon2id with configurable memory, time, and parallelism parameters with secure defaults (upgrade path without forced reset).
- **FR-050**: System MUST hash sensitive tokens (invitation, reset, API keys) using SHA-256 (or stronger) before storage; only the hash is persisted.
- **FR-051**: System MUST support transparent password hash rehash on login when stored hash parameters fall below current policy (see C-033).
- **FR-052**: System MUST provide a single bootstrap command that installs dependencies, applies migrations, seeds superadmin, and starts services (with mocks for optional infrastructure) in < 2 minutes on a standard laptop (see C-034).
- **FR-053**: System MUST support embed mode with origin allowlist controlling which domains may initiate embedded sessions.
- **FR-054**: System MUST issue short-lived (configurable, default 5m) one-time embed tokens exchanged for standard session credentials; unused tokens expire automatically.
- **FR-055**: System MUST set cookies for embedded sessions with attributes: Secure, HttpOnly, SameSite=None.
- **FR-056**: System MUST log embed session establishment including origin, tenant_id, and correlation_id.
- **FR-057**: System MUST deny and audit attempts from non-allowlisted origins with a distinct error code (origin_not_allowed).
- **FR-058**: System MUST provide configuration to isolate rate limits for embedded vs primary application contexts (see C-035, precedence per C-046).
- **FR-059**: System MUST document (generated artifact) the steps for embedding including CSP examples and required headers (artifact per C-047).
- **FR-060**: System MUST provide password reset initiation endpoint issuing a single-use reset token (hashed at rest) with configurable expiry (default 30m).
- **FR-061**: System MUST allow password reset completion without MFA when user has no MFA factors enrolled.
- **FR-062**: System MUST require successful MFA challenge during password reset completion when MFA is enabled for the user.
- **FR-063**: System MUST revoke all active sessions and refresh tokens upon successful password reset.
- **FR-064**: System MUST audit password reset initiation (without revealing if email exists) and completion (success/failure) with correlation_id.
- **FR-065**: System MUST prevent reuse of consumed or expired password reset tokens and respond with uniform invalid_token error.
- **FR-066**: System MUST grant tenant_admin implicit ALLOW for all non-high-risk tenant-scoped actions without needing explicit policy grants (excluding restricted actions like superadmin creation, cross-tenant operations, destructive purges requiring explicit policies).
- **FR-067**: System MUST deny and audit any attempt by tenant_admin (or lower roles) to create, assign, or revoke superadmin roles/users.
- **FR-068**: System MUST enforce role hierarchy: superadmin > tenant_admin > other roles; evaluation MUST reject policies that would grant cross-tenant capabilities to non-superadmin roles.
- **FR-069**: System MUST provide an idempotent seed operation that creates TestTenant (deterministic UUIDv5 from slug), one superadmin, one tenant_admin for TestTenant, and at least one standard user (deterministic UUIDv5 from normalized emails); reruns skip existing records using deterministic IDs.
- **FR-070**: System MUST expose code quality metrics (duplication %, cyclomatic complexity hotspots) per build and fail merges if thresholds (duplication >= 8% overall OR file duplication >= 15% OR function complexity > 10) are exceeded without inline justification.
- **FR-071**: System MUST provide centralized logging configuration controlling LOG_LEVEL, LOG_FORMAT (json|text), LOG_SINK (stdout|otlp|file), and LOG_FIELDS_EXTRA (comma-separated) exclusively via the configuration layer (no runtime code overrides).
- **FR-072**: System MUST support filtered log export (time window ≤ 24h, tenant_id, category, correlation_id) with maximum uncompressed size 100MB; partial exports MUST indicate boundary metadata and produce an export audit event.
- **FR-073**: System MUST redact configured sensitive keys (password, passwd, token, access_token, refresh_token, secret, api_key, authorization, set-cookie) from all logs; any detection of unredacted sensitive data MUST emit a redaction_violation audit event and metric (metric naming per C-048).
- **FR-074**: System MUST emit a performance.regression event when measured p95 or p99 latency exceeds budget (CRUD p95 ≥ 200ms OR p99 ≥ 500ms; heavy ops p95 ≥ 400ms OR p99 ≥ 800ms) outside an approved maintenance window.
- **FR-075**: System MUST run an OWASP Top 10 dynamic security test suite each release cycle and block release on unwaived high severity findings.
- **FR-076**: System MUST fail CI if code quality thresholds (duplication %, file duplication %, function complexity) are exceeded without an inline justification marker referencing a tracking ID.
- **FR-077**: System MUST ensure mutable domain entities (Tenant, User, Policy, FeatureFlag) include created_at, created_by, updated_at, updated_by fields; append-only entities (AuditEvent, KeyRotationRecord, PolicyEvaluationLog) MUST record created_at and actor context where applicable without update fields. Exceptions MUST be justified in data-model.md.

### Key Entities *(include if feature involves data)*

- **Tenant**: tenant_id, name, status (active, disabled), created_at, updated_at, config_version.
- **User**: user_id, tenant_id, email, status (invited, active, disabled), roles[], last_login_at.
- **Invitation**: invitation_id, tenant_id, email, token_hash, expires_at, accepted_at.
- **PasswordResetRequest**: reset_id, user_id, token_hash, issued_at, expires_at, consumed_at (nullable).
- **Role**: role_id (enumerated), description, permissions[] (logical capability identifiers).
- **Policy**: policy_id, version, resource_type, condition_expression, effect (ALLOW/DENY), created_by, created_at.
- **AuditEvent**: event_id, tenant_id (nullable for system), actor_user_id, action_type, target_ref, metadata, created_at.
- **Token** (conceptual): jti, subject (user_id/service_id), tenant_id, issued_at, expires_at, scopes[], key_version.
- **FeatureFlag**: flag_key, tenant_id (nullable=global), status (enabled/disabled), rollout_rules.
- **KeyRotationRecord**: key_version, activated_at, retired_at (nullable), algorithm, notes.
- **PolicyEvaluationLog**: eval_id, policy_id, decision, latency_ms, tenant_id, user_id, correlation_id.
- **UserMFA** (optional if enabled): user_id, factor_type (totp, webauthn), enrolled_at, last_used_at, secret_hash / credential_public_key.

Entity relationships (high-level):

- Tenant 1..* Users
- Tenant 1..* Invitations
- Tenant 1..* Policies
- Tenant 1..* FeatureFlags
- User *..* Roles (via assignment table)
- PolicyEvaluationLog many-to-one Policy

---

## Review & Acceptance Checklist

GATE: Automated checks run during main() execution.

### Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous  
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status

Updated by main() during processing.

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---
