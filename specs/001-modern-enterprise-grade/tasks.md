# Phase 2 Task Breakdown: Modern Enterprise-Grade Multi-Tenant FastAPI Backend

Status Legend: PENDING | WIP | DONE | DEFERRED

Principle: Contract & Test First.

Naming: `TEST-*` precedes corresponding `IMPL-*`.

Parallelization: Lanes (A–H) can advance after prerequisites.

## High-Level Lanes

- Lane A: Domain & Repository Foundations
- Lane B: Configuration Layer & Bootstrap
- Lane C: Auth Core
- Lane D: Policy Engine & RBAC
- Lane E: User Lifecycle, Feature Flags, Embed
- Lane F: Observability & Performance
- Lane G: Security & Quality Gates
- Lane H: API Adapters & Seed

## A. Domain & Repository Foundations

- TEST-DOM-01 Audit metadata persistence (entity fields present) (FR-077). [PENDING]
- TEST-DOM-05 Tenant isolation & superadmin cross_tenant bypass (FR-002, FR-011). [PENDING]
- TEST-DOM-07 User & Tenant soft delete/restore domain invariants (FR-018). [PENDING]
- IMPL-DOM-02 Tenant domain model + repository interface. [PENDING]
- IMPL-DOM-03 User domain model + repository interface. [PENDING]
- IMPL-DOM-04 Policy domain model + repository interface (versioning). [PENDING]
- IMPL-DOM-05 FeatureFlag domain model + repository interface. [PENDING]
- IMPL-DOM-06 AuditEvent domain appender abstraction. [PENDING]
- IMPL-DOM-07 Invitation domain model + repository interface. [PENDING]

## Dependency Overview

- B before components needing config.
- A before C/D/E/H.
- C & D after minimal A+B; E after A+C+D.
- F after A+B.
- G after B (plus C/F partials).
- H integrates progressively.

- IMPL-POL-06 Role enforcement guards. [PENDING]
- TEST-POL-07 Tenant admin implicit allow. [PENDING]
- IMPL-POL-08 Implicit allowance logic. [PENDING]
- TEST-POL-09 Admin defense-in-depth. [PENDING]
- IMPL-POL-10 Admin scope validator. [PENDING]
- IMPL-POL-11 Extension registry skeleton. [PENDING]
- TEST-POL-12 Extension registry registration. [PENDING]

## C. Auth Core

- TEST-AUTH-00 Provider registry exposes only password provider (FR-007). [PENDING]
- IMPL-AUTH-00 AuthProviderRegistry + password provider registration (FR-007). [PENDING]
- TEST-AUTH-01 Argon2id hash/upgrade. [PENDING]
- IMPL-AUTH-02 Hashing module. [PENDING]
- TEST-AUTH-03 Token issuance. [PENDING]
- IMPL-AUTH-04 JWT service. [PENDING]
- TEST-AUTH-05 Key rotation grace. [PENDING]
- IMPL-AUTH-06 Rotation orchestrator. [PENDING]
- TEST-AUTH-07 Revocation & replay. [PENDING]
- IMPL-AUTH-08 Revocation service. [PENDING]
- TEST-AUTH-09 Login + MFA branch (no enrollment flows). [PENDING]
- IMPL-AUTH-10 AuthenticationService. [PENDING]
- TEST-AUTH-11 Password reset lifecycle. [PENDING]
- IMPL-AUTH-12 Password reset service. [PENDING]
- TEST-AUTH-13 Role downgrade invalidation. [PENDING]
- IMPL-AUTH-14 Session invalidation hook. [PENDING]
- DEFER-AUTH-15 OIDC provider stub (discovery + claim validation) (Deferred per C-024). [DEFERRED]
- DEFER-AUTH-16 OIDC provider full authorization code flow. [DEFERRED]
- TEST-AUTH-17 MFA verify_code (Hybrid-A factors absent = pass-through). [PENDING]
- IMPL-AUTH-18 MFARepository (placeholder) + integration. [PENDING]

## D. Policy Engine & RBAC

- TEST-POL-01 Policy evaluation ALLOW/DENY/ABSTAIN semantics basic (FR-012). [PENDING]
- TEST-POL-03 Policy version rollback scenario (FR-030). [PENDING]
- TEST-POL-05 Role enforcement & undefined role rejection (FR-019, FR-031, FR-067, FR-068). [PENDING]
- IMPL-POL-02 Basic policy evaluator (FR-012). [PENDING]
- IMPL-POL-04 Policy versioning + registration (FR-029, FR-030). [PENDING]
- IMPL-POL-06 Role enforcement guards (FR-019, FR-031). [PENDING]
- TEST-POL-07 Tenant admin implicit allow (FR-066). [PENDING]
- IMPL-POL-08 Implicit allowance logic (FR-066). [PENDING]
- TEST-POL-09 Admin defense-in-depth (FR-036, C-026). [PENDING]
- IMPL-POL-10 Admin scope validator (FR-036, C-026). [PENDING]
- IMPL-POL-11 Extension registry skeleton (FR-038). [PENDING]
- TEST-POL-12 Extension registry registration (FR-038). [PENDING]

## E. User Lifecycle, Feature Flags, Embed

- TEST-ULF-01 Invitation accept idempotent. [PENDING]
- IMPL-ULF-02 Invitation service + hashing. [PENDING]
- TEST-ULF-03 User soft delete/restore. [PENDING]
- IMPL-ULF-04 Disable/restore logic. [PENDING]
- TEST-ULF-05 Feature flag evaluate (global/tenant). [PENDING]
- IMPL-ULF-06 FeatureFlagService. [PENDING]
- TEST-ULF-07 Embed token lifecycle. [PENDING]
- IMPL-ULF-08 EmbedService + origin validation. [PENDING]
- TEST-ULF-09 Disallowed origin. [PENDING]
- IMPL-ULF-10 Embed docs generator. [PENDING]

## F. Observability & Performance

- TEST-OBS-01 Log field presence. [PENDING]
- IMPL-OBS-02 Logging + redaction. [PENDING]
- TEST-OBS-03 Redaction enforcement. [PENDING]
- IMPL-OBS-04 Audit service. [PENDING]
- TEST-OBS-05 Log export bounds. [PENDING]
- IMPL-OBS-06 Export orchestrator. [PENDING]
- TEST-OBS-07 Metrics snapshot & Prometheus. [PENDING]
- IMPL-OBS-08 Metrics instrumentation. [PENDING]
- TEST-OBS-09 Regression trigger. [PENDING]
- IMPL-OBS-10 Regression detector. [PENDING]
- TEST-OBS-11 Revocation audit log. [PENDING]
- TEST-OBS-12 Audit event emission security-sensitive (FR-005). [PENDING]
- TEST-OBS-09A Regression false positive filtering (config hash differentiation). [PENDING]

## G. Security & Quality Gates

- TEST-SEC-01 Rate limit config. [PENDING]
- IMPL-SEC-02 Rate limiter abstraction. [PENDING]
- TEST-SEC-03 Error envelope. [PENDING]
- IMPL-SEC-04 Error middleware. [PENDING]
- TEST-SEC-05 Quality metrics fail example. [PENDING]
- IMPL-SEC-06 Quality metrics integration. [PENDING]
- TEST-SEC-07 Justification registry parser. [PENDING]
- IMPL-SEC-08 Justifications file + validator. [PENDING]
- TEST-SEC-09 OWASP scan ingestion mock. [PENDING]
- IMPL-SEC-10 Security scan integration. [PENDING]
- TEST-SEC-11 Failed token validation logging fields (FR-028 C-027). [PENDING]
- TEST-SEC-12 Error envelope schema compliance (FR-017 C-031). [PENDING]

## H. API Layer & Integration

- TEST-API-01 OpenAPI bundle validation. [PENDING]
- IMPL-API-02 FastAPI app factory. [DONE]
- TEST-API-03 Health/status. [DONE]
- IMPL-API-04 Health controller. [DONE]
- TEST-API-05 Config export. [PENDING]
- IMPL-API-06 Config export route. [PENDING]
- TEST-API-07 Tenant CRUD + idempotency. [PENDING]
- IMPL-API-08 Tenant routes. [PENDING]
- TEST-API-09 User list & restore. [PENDING]
- IMPL-API-10 User routes. [PENDING]
- TEST-API-11 Invitation accept. [PENDING]
- IMPL-API-12 Invitation route. [PENDING]
- TEST-API-13 Auth login/refresh/revoke. [PENDING]
- IMPL-API-14 Auth endpoints. [PENDING]
- TEST-API-15 Policy dry-run. [PENDING]
- IMPL-API-16 Dry-run route. [PENDING]
- TEST-API-17 Feature flags CRUD. [PENDING]
- IMPL-API-18 Feature flags routes. [PENDING]
- TEST-API-19 Embed exchange. [PENDING]
- IMPL-API-20 Embed routes. [PENDING]
- TEST-API-21 Metrics endpoints. [PENDING]
- IMPL-API-22 Metrics routes. [PENDING]
- TEST-API-23 Audit events page. [PENDING]
- IMPL-API-24 Audit routes. [PENDING]
- TEST-API-25 Bootstrap command integration. [PENDING]
- IMPL-API-26 Bootstrap CLI. [PENDING]
- TEST-API-27 Policy registration endpoint (admin-only) (FR-029). [PENDING]
- IMPL-API-27 Policy registration route wiring. [PENDING]
- TEST-API-23A Audit query multi-filter & pagination edge cases (FR-032). [PENDING]

## Cross-Cutting / Finalization

- TEST-XCUT-01 Correlation propagation. [PENDING]
- IMPL-XCUT-02 Correlation middleware. [PENDING]
- TEST-XCUT-03 Audit metadata persistence. [PENDING]
- IMPL-XCUT-04 Populate created_by/updated_by. [PENDING]
- TEST-XCUT-05 Deprecation header. [PENDING]
- IMPL-XCUT-06 Deprecation utility. [PENDING]
- TEST-XCUT-07 Seed idempotency deterministic UUIDv5 (FR-069). [PENDING]
- TEST-XCUT-08 Hash upgrade audit emission (FR-051 C-033). [PENDING]
- TEST-XCUT-09 Role downgrade session version invalidation timing (FR-021 C-032). [PENDING]

## Deferred / Backlog

- DEFER-MFA-ENROLL MFA enrollment & WebAuthn. [DEFERRED]
- DEFER-POL-DSL Advanced policy DSL & caching. [DEFERRED]
- DEFER-CACHE Distributed cache layer. [DEFERRED]
- DEFER-EMBED-WS Embed real-time channel. [DEFERRED]

## FR → Task Mapping (All FRs Covered)

- FR-001: TEST-API-07, IMPL-API-08, TEST-DOM-07
- FR-002: TEST-DOM-05
- FR-003: IMPL-AUTH-10, IMPL-AUTH-16
- FR-004: IMPL-POL-02, IMPL-POL-04
- FR-005: IMPL-OBS-04
- FR-006: TEST-ULF-01, IMPL-ULF-02, TEST-API-11, IMPL-API-12
- FR-007: TEST-AUTH-00, IMPL-AUTH-00, TEST-AUTH-09, IMPL-AUTH-10 (OIDC deferred: DEFER-AUTH-15/16)
- FR-008: TEST-AUTH-03, IMPL-AUTH-04, TEST-API-13, IMPL-API-14
- FR-009: TEST-AUTH-01, IMPL-CONF-07
- FR-010: TEST-API-09, IMPL-API-10
- FR-011: TEST-DOM-05
- FR-012: TEST-POL-01, IMPL-POL-02
- FR-013: TEST-API-07, IMPL-API-08
- FR-014: IMPL-API-02, TEST-XCUT-05, IMPL-XCUT-06
- FR-015: TEST-API-03, IMPL-API-04
- FR-016: IMPL-OBS-08, TEST-OBS-07
- FR-016: IMPL-OBS-08, TEST-OBS-07, C-030 metrics enumeration enforced
- FR-017: TEST-SEC-03, IMPL-SEC-04
- FR-017: TEST-SEC-03, TEST-SEC-12, IMPL-SEC-04
- FR-018: TEST-API-09, IMPL-API-10, TEST-DOM-07
- FR-019: TEST-POL-05, IMPL-POL-06
- FR-020: TEST-API-15, IMPL-API-16, IMPL-POL-04
- FR-021: TEST-AUTH-13, IMPL-AUTH-14
- FR-021: TEST-AUTH-13, TEST-XCUT-09, IMPL-AUTH-14
- FR-022: TEST-AUTH-05, IMPL-AUTH-06, IMPL-API-04
- FR-023: TEST-SEC-01, IMPL-SEC-02
- FR-024: TEST-API-01
- FR-025: IMPL-API-26, TEST-API-25
- FR-026: TEST-ULF-05, IMPL-ULF-06, TEST-API-17, IMPL-API-18
- FR-027: TEST-OBS-09, IMPL-OBS-10
- FR-028: TEST-AUTH-07, IMPL-AUTH-08, TEST-OBS-11
- FR-028: TEST-AUTH-07, IMPL-AUTH-08, TEST-OBS-11, TEST-SEC-11
- FR-029: TEST-API-27, IMPL-POL-04, IMPL-API-27
- FR-030: TEST-POL-03, IMPL-POL-04
- FR-031: TEST-POL-05, IMPL-POL-06
- FR-032: IMPL-OBS-04, TEST-API-23
- FR-032: IMPL-OBS-04, TEST-API-23, TEST-API-23A
- FR-033: TEST-AUTH-07, IMPL-AUTH-08
- FR-034: TEST-OBS-07, IMPL-OBS-08, TEST-API-21, IMPL-API-22
- FR-035: TEST-ULF-05, IMPL-ULF-06
- FR-036: TEST-POL-09, IMPL-POL-10
- FR-037: TEST-XCUT-01, IMPL-XCUT-02, IMPL-SEC-04
- FR-038: IMPL-POL-11, TEST-POL-12
- FR-039: TEST-CONF-01, IMPL-CONF-02
- FR-040: TEST-CONF-03, IMPL-CONF-02
- FR-041: TEST-CONF-01
- FR-042: TEST-CONF-05, IMPL-CONF-02
- FR-043: TEST-CONF-06, IMPL-CONF-04
- FR-044: TEST-CONF-07, IMPL-CONF-02
- FR-045: TEST-CONF-03
- FR-046: IMPL-CONF-06, TEST-API-05, IMPL-API-06
- FR-047: TEST-CONF-08, IMPL-CONF-04
- FR-048: TEST-CONF-05, IMPL-CONF-02
- FR-049: TEST-AUTH-01, IMPL-AUTH-02
- FR-050: IMPL-ULF-02, IMPL-AUTH-12
- FR-051: TEST-AUTH-01, IMPL-AUTH-02
- FR-051: TEST-AUTH-01, TEST-XCUT-08, IMPL-AUTH-02
- FR-052: IMPL-API-26, TEST-API-25
- FR-053: TEST-ULF-07, IMPL-ULF-08
- FR-054: TEST-ULF-07, IMPL-ULF-08
- FR-055: TEST-ULF-07, IMPL-ULF-08
- FR-056: IMPL-ULF-08, TEST-ULF-07
- FR-057: TEST-ULF-09, IMPL-ULF-08
- FR-058: TEST-SEC-01, IMPL-ULF-08
- FR-059: IMPL-ULF-10
- FR-060: TEST-AUTH-11, IMPL-AUTH-12
- FR-061: TEST-AUTH-09, TEST-AUTH-11, TEST-AUTH-17, IMPL-AUTH-10, IMPL-AUTH-12, IMPL-AUTH-18
- FR-062: TEST-AUTH-09, TEST-AUTH-11, TEST-AUTH-17, IMPL-AUTH-10, IMPL-AUTH-12, IMPL-AUTH-18
- FR-063: TEST-AUTH-11, IMPL-AUTH-12
- FR-064: TEST-AUTH-11, IMPL-AUTH-12
- FR-065: TEST-AUTH-11, IMPL-AUTH-12
- FR-066: TEST-POL-07, IMPL-POL-08
- FR-067: TEST-POL-05, IMPL-POL-06
- FR-068: TEST-POL-05, IMPL-POL-06
- FR-069: IMPL-API-26, TEST-API-25
- FR-069: IMPL-API-26, TEST-API-25, TEST-XCUT-07
- FR-070: TEST-SEC-05, IMPL-SEC-06
- FR-071: TEST-OBS-01, IMPL-OBS-02
- FR-072: TEST-OBS-05, IMPL-OBS-06
- FR-073: TEST-OBS-03, IMPL-OBS-02
- FR-074: TEST-OBS-09, IMPL-OBS-10
- FR-075: TEST-SEC-09, IMPL-SEC-10
- FR-076: TEST-SEC-05, IMPL-SEC-06, TEST-SEC-07, IMPL-SEC-08
- FR-077: TEST-DOM-01, TEST-XCUT-03, IMPL-XCUT-04

- FR-003: IMPL-AUTH-10, IMPL-AUTH-16
- FR-004: IMPL-POL-02, IMPL-POL-04
- FR-005: IMPL-OBS-04
- FR-006: TEST-ULF-01, IMPL-ULF-02, TEST-API-11, IMPL-API-12
- FR-007: TEST-AUTH-00, IMPL-AUTH-00, TEST-AUTH-09, IMPL-AUTH-10 (OIDC deferred: DEFER-AUTH-15/16)
- FR-008: TEST-AUTH-03, IMPL-AUTH-04, TEST-API-13, IMPL-API-14
- FR-009: TEST-AUTH-01 (password policy config via config tasks), IMPL-CONF-07
- FR-010: TEST-API-09, IMPL-API-10
- FR-011: (Implicit in multi-tenancy + superadmin bypass) TEST-DOM-05
- FR-012: TEST-POL-01, IMPL-POL-02
- FR-013: TEST-API-07, IMPL-API-08
- FR-014: IMPL-API-02, TEST-XCUT-05, IMPL-XCUT-06
- FR-015: TEST-API-03, IMPL-API-04
- FR-016: (Per-tenant metrics) IMPL-OBS-08, TEST-OBS-07
- FR-017: TEST-SEC-03, IMPL-SEC-04
- FR-018: TEST-API-09, IMPL-API-10, TEST-DOM-07
- FR-019: TEST-POL-05, IMPL-POL-06
- FR-020: TEST-API-15, IMPL-API-16, IMPL-POL-04
- FR-021: TEST-AUTH-13, IMPL-AUTH-14
- FR-022: TEST-AUTH-05, IMPL-AUTH-06, IMPL-API-04 (exposes key rotation version)
- FR-023: TEST-SEC-01, IMPL-SEC-02
- FR-024: TEST-API-01
- FR-025: IMPL-API-26, TEST-API-25
- FR-026: TEST-ULF-05, IMPL-ULF-06, TEST-API-17, IMPL-API-18
- FR-027: TEST-OBS-09 (performance regression), IMPL-OBS-10
- FR-028: TEST-AUTH-07, IMPL-AUTH-08, TEST-OBS-11
- FR-029: TEST-API-27, IMPL-POL-04, IMPL-API-27
- FR-030: TEST-POL-03, IMPL-POL-04
- FR-031: TEST-POL-05, IMPL-POL-06
- FR-032: IMPL-OBS-04, TEST-API-23
- FR-033: TEST-AUTH-07, IMPL-AUTH-08
- FR-034: TEST-OBS-07, IMPL-OBS-08, TEST-API-21, IMPL-API-22
- FR-035: TEST-ULF-05, IMPL-ULF-06
- FR-036: TEST-POL-09, IMPL-POL-10
- FR-037: TEST-XCUT-01, IMPL-XCUT-02, IMPL-SEC-04
- FR-038: IMPL-POL-11, TEST-POL-12
- FR-039: TEST-CONF-01, IMPL-CONF-02
- FR-040: TEST-CONF-03, IMPL-CONF-02
- FR-041: TEST-CONF-01
- FR-042: TEST-CONF-05, IMPL-CONF-02
- FR-043: TEST-CONF-06, IMPL-CONF-04
- FR-044: TEST-CONF-07, IMPL-CONF-02
- FR-045: TEST-CONF-03
- FR-046: IMPL-CONF-06, TEST-API-05, IMPL-API-06
- FR-047: IMPL-CONF-04
- FR-048: TEST-CONF-05, IMPL-CONF-02
- FR-049: TEST-AUTH-01, IMPL-AUTH-02
- FR-050: IMPL-ULF-02, IMPL-AUTH-12 (reset tokens)
- FR-051: TEST-AUTH-01, IMPL-AUTH-02
- FR-052: IMPL-API-26, TEST-API-25
- FR-053: TEST-ULF-07, IMPL-ULF-08
- FR-054: TEST-ULF-07, IMPL-ULF-08
- FR-055: TEST-ULF-07, IMPL-ULF-08
- FR-056: IMPL-ULF-08 (audit hook), TEST-ULF-07
- FR-057: TEST-ULF-09, IMPL-ULF-08
- FR-058: TEST-SEC-01, IMPL-ULF-08 (embed rate limits)
- FR-059: IMPL-ULF-10
- FR-060: TEST-AUTH-11, IMPL-AUTH-12
- FR-061: TEST-AUTH-09, TEST-AUTH-11, TEST-AUTH-17, IMPL-AUTH-10, IMPL-AUTH-12, IMPL-AUTH-18
- FR-062: TEST-AUTH-09, TEST-AUTH-11, TEST-AUTH-17, IMPL-AUTH-10, IMPL-AUTH-12, IMPL-AUTH-18
- FR-063: TEST-AUTH-11, IMPL-AUTH-12
- FR-064: TEST-AUTH-11, IMPL-AUTH-12
- FR-065: TEST-AUTH-11, IMPL-AUTH-12
- FR-066: TEST-POL-07, IMPL-POL-08
- FR-067: TEST-POL-05, IMPL-POL-06
- FR-068: TEST-POL-05, IMPL-POL-06
- FR-069: IMPL-API-26, TEST-API-25
- FR-070: TEST-SEC-05, IMPL-SEC-06
- FR-071: TEST-OBS-01, IMPL-OBS-02
- FR-072: TEST-OBS-05, IMPL-OBS-06
- FR-073: TEST-OBS-03, IMPL-OBS-02
- FR-074: TEST-OBS-09, IMPL-OBS-10
- FR-075: TEST-SEC-09, IMPL-SEC-10
- FR-076: TEST-SEC-05, IMPL-SEC-06, TEST-SEC-07, IMPL-SEC-08
- FR-077: TEST-DOM-01, TEST-XCUT-03, IMPL-XCUT-04

## Additional Low-Severity Test Tasks

- TEST-AUTH-07B Replay detection near expiry boundary (FR-028, C-020) [PENDING]
- TEST-OBS-01A Metrics key set compliance (FR-016, C-030) [PENDING]
- TEST-AUTH-00A OIDC absence assertion (FR-007, C-036) [PENDING]

## Parallelization Plan (Initial Sprint Ordering)

1. Start B (Configuration) & A (Domain Interfaces) concurrently.
2. Kick off C (Auth hashing, token skeleton) once A+B partial complete.
3. Begin D (basic policy evaluator) after A.
4. Start F (logging skeleton + audit) after B for config references.
5. Integrate H endpoints incrementally as services mature (login, health first).
6. Launch G quality gates after minimal code present (post initial commits) to avoid noise.
7. E (invitations, feature flags, embed) after core auth & policy foundations ready.
8. Performance regression instrumentation (F) after first end-to-end user flow implemented.

## Exit Criteria for Phase 2

- All TEST-* tasks created & implemented (failing initially until IMPL counterparts land).
- Every FR mapped in FR → Task section (no omissions) ✔
- OpenAPI bundle regenerates & passes validation in CI.
- Justification registry scaffold added (empty or sample entry) + validator.
- Bootstrap command test passes (minimal environment start).

## Notes

- MFA enrollment & WebAuthn explicitly deferred (DEFER-* tasks) to prevent scope creep.
- Policy expression DSL intentionally minimal; complexity expansions require new ADR.
- In-memory repositories empower fast unit tests; DB integration postponed until Phase 3 start.
- Error codes (mfa_required, mfa_invalid, origin_not_allowed, invalid_token, config_immutable) centralized in one enum early (add small follow-up task when creating that file).

## Next Immediate Actions

1. Proceed with A & B lane test scaffolds before any substantial implementation.
2. Commit updated tasks.md and establish CI baseline (ensure no phantom task references remain).
3. Begin C (hashing) after configuration loader & domain models tests exist.

End of tasks.md
