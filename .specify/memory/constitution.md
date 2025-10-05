<!--
Sync Impact Report
Version: 1.5.0 -> 1.5.1 (PATCH)
Modified Principles: II (expanded explicit coverage enforcement mechanics: 90% domain, 85% overall, 100% critical paths; added coverage manifest governance and justification rules)
Added Sections: None
Removed Sections: None
Templates Updated:
	- .specify/templates/plan-template.md ✅ (added coverage gating to Constitution Check item 2 + version ref)
	- .specify/templates/spec-template.md ✅ (compatible; no change needed)
	- .specify/templates/tasks-template.md ✅ (implicit support; no wording change required)
Templates Pending: None
Deferred TODOs: None
Rationale for Version Bump: Clarification and procedural detail only (no semantic governance change) qualifies as PATCH.
-->

# githubspeckit Backend Constitution
<!-- Historical Sync Impact Reports omitted for brevity in active version; prior version deltas retained in VCS history. -->

## I. Modular, Hexagonal & Tenant-Aware Architecture

The system uses a ports & adapters (hexagonal) architecture: domain layer (pure Python) is framework‑agnostic; adapters implement FastAPI transport, persistence, caching, external services. Multi‑tenancy is explicit: all domain operations include tenant context (tenant_id) passed from request boundary. No business logic in adapters. Side effects isolated. Infrastructure changes require adapter/config swaps only. Idempotent service methods where appropriate.

## II. Contract & Test First (NON‑NEGOTIABLE)

Every change starts with: (1) contract (OpenAPI fragment / Pydantic model / domain interface) (2) failing tests (unit + contract + RBAC + negative). Red‑Green‑Refactor strictly enforced. No implementation without an asserting test. Mutation of public contracts requires version impact analysis + backward compatibility plan.

Required Coverage Matrix (enforced in CI):

* Domain layer: >= 90% line coverage (hard fail below).
* Overall repository: >= 85% line coverage (hard fail below).
* Critical auth & multi‑tenancy enforcement paths: 100% statement coverage (no unexecuted branches) — failing lines block merge.
* New/changed files: MUST NOT reduce aggregate coverage; any overall drop >0.5% requires justification (JUSTIFY ID) and >1.0% blocks until addressed.

Enforcement Mechanics:

1. CI `coverage-gate` parses coverage XML → structured JSON summary consumed by quality gate.
2. If any threshold violated: pipeline fails; merge blocked.
3. Coverage decreases within thresholds but >0.5% overall produce a non-blocking warning requiring reviewer acknowledgment; >1.0% becomes blocking.
4. Critical path manifest (`coverage_critical_paths.yml`) governs which files require 100%; manifest edits require security reviewer approval.
5. Performance tests for high‑throughput endpoints MUST exist (tag `@smoke_performance`) before feature completion; absence becomes blocking after first stable release of that feature.

Performance Gate Ordering: Coverage gate runs before performance regression detection to prevent masking untested slow paths.

## III. Secure Multi-Tenancy, Role Hierarchy & Least Privilege

All data access is tenant‑scoped by default.

Role Hierarchy (strict):

* superadmin (global) → may perform cross-tenant operations & platform-wide functions.
* tenant_admin (per-tenant) → full authority over resources within its tenant (implicit ALLOW for all tenant-scoped actions) except: cannot assign or create superadmin users/roles, cannot perform cross-tenant reads/writes, cannot modify global platform configuration.
* other tenant roles (developer, analyst, user, service_account, support_readonly, future domain roles) → explicitly permissioned via policies; NEVER exceed tenant_admin scope by default.

Tenant Admin Implicit Scope:

* Does NOT require individual RBAC grants for standard tenant CRUD and configuration inside the tenant.
* Still subject to policy engine for explicitly high-risk actions flagged as elevated (e.g., bulk export, destructive purge) — policies may DENY.
* Cross-tenant query attempts are rejected unless elevated to superadmin.

Seed & Bootstrapping:

* Initial seed MUST create: TestTenant (id deterministic), one global superadmin user, one tenant_admin user for TestTenant, and at least one standard user role.
* Seed operation is idempotent; rerun updates missing records only.

RBAC Enforcement Flow: (1) Authentication (principal + tenant resolution) (2) Role resolution (role graph/hierarchy) (3) Implicit tenant_admin widening inside tenant (4) Policy evaluation (attribute checks: tenant_id, ownership, feature flags) (5) Deny > allow precedence.

No implicit wildcard roles beyond tenant_admin’s defined tenant scope. Privilege escalation requires explicit role change + audit. Security tests include: tenant boundary breaches, role downgrade session invalidation, tenant_admin forbidden operations (superadmin creation, cross-tenant reads). Secrets never logged. PII classification applied to fields; encryption at rest mandated if sensitive.

## IV. Switchable Data & Infrastructure Abstraction Layer

Repositories expose async interfaces returning domain models (no ORM leakage). Swappable implementations: SQLAlchemy (PostgreSQL primary), optional in‑memory (tests), SQLite (local dev), and future cloud variants. Migrations: alembic with per‑tenant strategy configurable: (a) single database, tenant_id column (default) (b) schema-per-tenant (pluggable strategy) (c) database-per-tenant (not default—requires governance approval). Caching, messaging, search, and file storage each behind their own provider interface. Feature toggles control rollout; toggles are testable and documented. No direct ORM usage outside data adapters.

## V. Observability, Performance & Evolution (Versioned APIs & Central Logging)

Logging (Central & Configurable):

* Central Control: A single configuration block (e.g., LOG_LEVEL, LOG_FORMAT=json|text, LOG_SINK=stdout|otlp|file, LOG_FIELDS_EXTRA=csv) governs all logger instances; code MUST NOT set ad‑hoc levels.
* Structured Fields: Every request log line includes: timestamp (ISO8601), level, correlation_id, request_id, tenant_id (nullable), user_id (nullable), roles, path, method, status, latency_ms, bytes_in/out.
* Event Categories: security.*, audit.*, policy.*, perf.*, infra.* for filterable streams. Security events MUST never be downgraded below INFO.
* Redaction: PII / secrets detection middleware ensures configured sensitive keys (e.g., password, token, secret, api_key) are hashed or removed; violation triggers security.redaction_violation metric + audit.
* Log Export: System MUST support on-demand export of a bounded, queryable slice (filters: time window, tenant_id, category, correlation_id) producing line-delimited JSON or compressed archive for forensic review.
* Sampling: High-volume categories (trace-level adapter diagnostics) may be sampled; security/audit logs MUST be unsampled.
* Retention & Rotation: Default rotation policy documented; local dev rotates by size/time, production defers to platform or log processor; configuration enumerated.

Metrics & Tracing:

* Metrics Minimum Set: request_latency (histogram), request_errors (counter by code), policy_denials, db_query_latency, cache_hits, cache_misses, auth_failures, rate_limit_hits, config_drift_events.
* Per-Tenant Counters: opt-out only for privacy reasons approved via governance.
* Tracing: OpenTelemetry spans at boundaries (API handler, service, repository, external call). Trace IDs correlate with correlation_id header.

Performance Budgets & Profiling:

* Budgets: p95 < 200ms CRUD, p99 < 500ms heavy ops; breach triggers performance.regression event.
* Query SLAs: Single-query p95 < 50ms unless explicitly labeled bulk; slow query logger emission > threshold.
* Continuous Profiling (Future ADR): Placeholder for optional sampling profiler integration.

API Versioning & Evolution:

* Versioning: URI /v1 + Accept version negotiation. Sunset & Deprecation headers precede removals.
* Backward Compatibility: Default stance; incompatible change requires migration guide + dual-run window.
* Contract Diff CI: Any undocumented response/schema change blocks merge.

Non-Negotiables:

1. No inline print/debug statements committed; only central logger.
2. Security/audit logs MUST be structured and exportable.
3. Log level changes happen only via configuration — no code-level overrides in production paths.
4. Any new external adapter adds metrics + span + structured log at success/failure.
5. Export tool MUST enforce time + size limits; partial export boundaries clearly indicated.

Rationale: Central control with exportability enables rapid incident response, root-cause analysis, and consistent compliance visibility while ensuring performance and evolution remain governed.

## VI. Reusable Authentication & Authorization Artifact

Authentication & authorization ("auth core") MUST exist as an independent, reusable package (e.g., `auth_core/`) with zero imports from domain packages. It exposes:

* Boundary Adapters: FastAPI dependency providers for principal extraction, tenant resolution, role mapping.
* Domain Extension Points: Registration API for domains to declare resource types, permission predicates, fine-grained policies, and custom claims enrichers.
* Multi-Tenancy Integration: Every issued principal/object includes tenant context; cross-tenant elevation only via explicit superadmin flag + audit.
* Token & Session Abstraction: Standard interface supporting JWT, opaque tokens, and future OIDC providers; switching provider MUST NOT change downstream policy code.
* Policy Engine: Deterministic, pure function style evaluation returning ALLOW / DENY / ABSTAIN with rationale + audit emission; deny by default.
* Test Harness: Fixtures & builders enabling other projects to consume the auth module without re-implementing scaffolding; sample policies + reference tests included.
* Security Hardening: Centralized rotation hooks for signing keys, claim whitelisting (reject unknown critical claims), replay protection integration points.

Non‑Negotiables:

1. No business/domain logic in auth core—only generic identity, tenancy, and permission orchestration.
2. Domain packages MAY register policies but MAY NOT patch core internals.
3. Public interfaces versioned; breaking changes require minor/major bump of the auth package + migration guide.
4. All new domain features MUST express authorization through registered policies—no inline role checks in handlers.
5. Adding a new project reuses this artifact intact; only configuration + policy registrations differ.
6. Superadmin scope escalation paths tested (positive + negative) and produce mandatory audit events.

Rationale: Ensures consistent, secure, multi-tenant enforcement across projects, accelerates new service bootstrap, and prevents fragmented authorization logic.

## VII. Unified Configuration & Deployment Topology

All runtime configuration MUST be centralized and environment-variable access isolated in a single configuration layer. The system MUST operate in both monorepo (frontend + backend co-located) and dual-repo modes without leaking or mixing environment-specific settings.

Requirements:

* Canonical Descriptor: A machine-readable file (e.g., `config/settings.toml` + generated `config/.env.example`) enumerates each variable: name, type, required, scope (BACKEND|FRONTEND|SHARED), default (non-secret only), description.
* Single Loader: Only the config module reads OS environment; all other code imports typed settings. Direct `os.getenv` usage outside config is forbidden.
* Namespacing: Prefixes enforce isolation (`BACKEND_`, `FRONTEND_`, `SHARED_`). Frontend build pipeline only exposes `FRONTEND_` and approved `SHARED_` vars; backend refuses unknown `FRONTEND_` vars at startup.
* Validation & Fail-Fast: Startup aborts (non-zero exit) with aggregated error report if required variables missing or invalid (type coercion, regex, enum domain).
* Immutability: Settings objects frozen post-load; mutation raises an exception.
* Deployment Mode Flag: `DEPLOY_MODE=monorepo|backend-only|frontend-only|dual` drives static asset serving, health reporting, and optional reverse-proxy configuration.
* Structure Invariants: Monorepo uses `apps/backend/`, `apps/frontend/`, shared libs under `packages/` or `libs/`. Dual repo backend MUST NOT assume presence of frontend build artifacts.
* Secret Hygiene: No secret default values in repo. `.env.example` lists placeholders; CI secret scan blocks accidental commits.
* Layered Overrides: Deterministic precedence (base < environment file < environment variables). Documented order logged on startup.
* Hash & Audit: Effective non-secret configuration hash (e.g., SHA256 of sorted key=value excluding secrets) logged for traceability.
* Drift Detection: Runtime option to compare live env with descriptor; extra/missing keys produce warning or error based on severity flag.
* Frontend Isolation: Build step validates absence of `BACKEND_` tokens in transpiled bundle.
* Redaction Tool: Script produces sanitized config snapshot for support without secret values.
* Documentation Generation: Config descriptor auto-generates `/docs/config.md` (or README section) on CI; diffs reviewed.

Non‑Negotiables:

1. No direct environment access outside config layer.
2. Adding a variable requires descriptor update + regenerated template; CI fails if discrepancy.
3. Secrets must be injected at deploy/runtime only; never committed.
4. Mixed-mode assumptions (serving frontend in backend-only mode) cause explicit startup failure.
5. Configuration tests cover: missing required var, invalid enum, wrong type, unauthorized prefix, DEPLOY_MODE branch behavior.

Rationale: Guarantees reproducible deployments, prevents accidental secret leakage, and enables frictionless movement between monorepo and separated deployments without code divergence.

## VIII. Developer Experience & Embed Readiness

## IX. Code Quality & Simplicity (DRY, KISS, YAGNI, SOLID, Complexity Control)

Quality Objectives: Sustainably maintainable codebase with low accidental complexity, minimized duplication, and purposeful abstractions.

Guiding Principles:

* DRY (Don’t Repeat Yourself): Identical or near-identical logic appearing 3× triggers consolidation before feature completion unless justified (performance, isolation). Duplication tracker (static analysis / grep rules) integrated in CI.
* KISS (Keep It Simple & Small): Prefer straightforward procedural/functional solutions over meta-programming or premature class hierarchies; smallest surface to satisfy requirement.
* YAGNI (You Aren’t Gonna Need It): No abstraction, interface, feature flag, or configuration key unless a present, test-backed requirement or an approved near-term roadmap item (<2 sprints).
* SOLID Application: Apply only when it reduces net complexity—Single Responsibility and Interface Segregation prioritized; avoid over-engineering via speculative extensibility.
* Clean Code Signals: Small pure functions for business logic; side effects isolated; maximum function length (soft) 50 lines unless inherently descriptive; cyclomatic complexity >10 requires refactor or justification.
* Cohesion & Coupling: High cohesion inside modules, loose coupling across boundaries (enforced by import rules / layering linter).
* Naming: Intention-revealing; abbreviations avoided unless industry standard (e.g., ID, UUID). Public interfaces documented at definition.
* Progressive Refactor: New or modified code must not increase overall duplication/complexity metrics; opportunistic cleanup allowed if covered by tests.
* Dead Code Policy: Unused functions/branches removed in same PR when discovered; TODO for future usage not permitted without linked task.

Non-Negotiables:

1. Introducing an abstraction requires ≥2 concrete current usages (or governance-approved imminent usage) — otherwise inline.
2. Shared “utils” modules require documented contract & owning team; no dumping ground.
3. Test code duplication permissible only where reducing it would hide intent; production DRY still enforced.
4. Generated code (OpenAPI clients, migrations) excluded from duplication metrics but MUST remain unedited; customizations via extension layers.
5. Complexity budget breaches (duplication %, coverage drop, cyclomatic > threshold) block merge until addressed or formally justified.

Metrics & Enforcement:

* CI publishes: duplication %, average cyclomatic complexity, top 10 complex functions, coverage deltas.
* Thresholds (initial): duplication <8%, any single file duplication <15%; failing metrics mark PR as needs-attention.
* Refactor label required if PR reduces complexity ≥10% for tracked hotspot file.

Rationale: Codifies consistent simplicity standards so long-term velocity remains high and architectural intent stays clear.

The platform MUST be fast to bootstrap locally with minimal mandatory infrastructure, and backend APIs MUST be architected to support secure third‑party embedded contexts (e.g., iframe integrations) while preserving session continuity.

Developer Velocity Requirements:

* Single Command Bootstrap: `make dev` (or documented script) spins up mandatory services only (e.g., backend API + in-memory / lightweight DB + mock email). Optional services (Redis, external IdP, message broker) auto-fallback to in‑process or stub implementations.
* 5-Minute Rule: A new contributor reaches a green test run in ≤5 minutes (target on modern laptop) with clear failures if prerequisites missing.
* Deterministic Dev Data: Seed script creates baseline tenant, superadmin, sample tenant_admin, and feature flags. Re-runnable idempotently.
* Fast Feedback: Unit + contract test subset runnable under 10s (target) via focused test selection tooling.
* Dev Container / VS Code Config (future): Optional but when present MUST mirror minimal bootstrap path; absence must not block contributors.
* Mock & Fallbacks: Email, external auth providers, and future payment / external APIs mocked behind provider interfaces enabling offline development.
* Lint & Type Pre-Push: Pre-commit hook (documented) installs automatically (opt-out explicit) to catch style / type errors.
* Clear Failure Modes: Startup errors provide actionable remediation (missing dependency, port conflict, migrations pending) with exit code ≠0.

Embed / Iframe Readiness Requirements:

* Cookie Compatibility: Session cookies (if used) configured with `SameSite=None; Secure` for cross-origin iframe scenarios while still allowing CSRF protection via double-submit token or header-based strategy.
* Origin Allowlist: Configurable list of allowed embed parent origins; requests carrying `X-Embed-Origin` validated against allowlist.
* Token-Based Alternate: Support stateless signed short-lived embed tokens (JWT or PASETO) that encapsulate tenant_id, user_id, session_version, and allowed resource scopes.
* Session Continuity: Backend provides endpoint to exchange existing session cookie for an embed token (and reverse) without elevating privileges.
* CSP & Frame-Ancestors: Recommended CSP documentation including `frame-ancestors` directive; enforcement configurable but defaults to allow only listed origins.
* Audit & Telemetry: Embed-origin captured in audit events and request logs for security analytics.
* Rate Isolation: Embedded contexts subject to per-origin + per-tenant rate limiting distinct from primary UI traffic.
* CSRF Strategy: For cookie-based auth inside embeds, a per-frame anti-CSRF token (rotating) delivered via a secure, non-cacheable endpoint.
* PostMessage Contract (Future): Placeholder ADR required before implementing cross-frame secure messaging; not implemented by default.

Non‑Negotiables:

1. No feature may depend on heavyweight infra (e.g., external Redis, broker) for basic local CRUD & auth flows.
2. Fallback mocks MUST produce faithful contract responses (schema identical, behavior simplified) and be clearly labeled in logs.
3. Embed support MUST NOT weaken tenant isolation or RBAC; same policy engine path used for embedded requests.
4. Any new stateful session mechanism MUST document iframe implications before merge.
5. Addition of a hard dependency (cannot fallback) requires governance approval and justification of developer impact.

Rationale: Ensures low friction onboarding, consistent environments, and future-ready secure embedding without retrofitting fundamental session or auth layers later.

## Additional Constraints & Architectural Standards

1. Language & Stack: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic, Redis (caching), PostgreSQL (primary), pytest, httpx (async client), OpenTelemetry, ruff + mypy (strict).  
2. Async Only: All I/O logic async; sync calls must be isolated & justified (rare).  
3. Dependency Rules: Domain layer cannot import from infrastructure (enforced via import linter).  
4. Tenancy Strategy Default: Row-level tenant_id with composite indexes; queries MUST filter by tenant_id early.  
5. RBAC Roles (initial): superadmin (global), tenant_admin (per-tenant full tenant scope), developer, analyst, user, service_account, support_readonly. Role expansion requires: explicit use case + blast radius analysis + policy tests; new roles MUST be at or below tenant_admin level and CANNOT approximate superadmin capabilities.  
6. Auditing: All security-sensitive actions (role changes, cross-tenant reads, destructive operations) produce immutable append-only audit events (security.\* or audit.\* category) routed through central logger abstraction.  
7. Configuration: 12‑Factor compliance. Secrets via env / vault; no defaults for critical secrets.  
8. Data Validation: Pydantic for boundary validation; domain invariants inside entities (raise DomainError).  
9. Error Model: Structured error envelope {trace_id, code, message, details?, docs_url}. No raw tracebacks to clients.  
10. Identities: UUIDv5 (deterministic namespace-based) for new primary identifiers to enable idempotent seeding, stable test fixtures, and reproducible migrations. Rationale: Deterministic IDs simplify cross-environment comparison and bootstrap idempotency; time-ordering provided via created_at fields and audit logs. (Changed from UUIDv7 in v1.6.0 before any production data persisted.)  
11. Rate Limiting & Abuse Controls: Global + per-tenant + per-user where appropriate (pluggable provider).  
12. Infrastructure Parity: Local dev via docker-compose; test env mimics prod-critical services.  
13. Zero Trust on Input: All external integrations validated + sanitized.  
14. Secret Rotation & Key Management: All encryption keys versioned; rotation tested.  
15. Data Lifecycle: Soft delete default; hard delete gated & audited.  
16. Code Generation: OpenAPI spec generated on CI; divergence fails build.  
17. Documentation: Every new module must have a README with purpose, public contracts, invariants.  
18. Performance Regression Guard: Benchmark tests for hot paths; >10% regression blocks merge.  
19. Accessibility & Internationalization (if UI surfaces arise later): prepared via locale field strategy.  
20. AI / Automation Hooks: Observability events may feed anomaly detection—must remain privacy-safe.
21. Security Testing: Automated OWASP Top 10 mapping maintained; each release cycle includes dynamic security tests (auth bypass, injection, deserialization) + dependency scan; quarterly third-party penetration test required with remediation tracking.
22. Log Export & Verification: Quarterly drill executes log export tooling to validate completeness, filtering accuracy, and redaction guarantees; results documented.

## Development Workflow, Quality Gates & Review Process

Workflow Sequence per Feature:

1. Spec Draft → /plan command produces plan & constitution check.  
2. Contracts First: Pydantic schemas + OpenAPI path stubs + repository interfaces.  
3. Tests Added: Unit (domain), contract (API shape), RBAC enforcement, tenancy boundary, negative & performance baseline (if applicable).  
4. Minimal Implementation → All tests green.  
5. Refactor (architecture, duplication, performance).  
6. Observability & Security verification (add missing metrics/logs/traces).  
7. Documentation & examples updated.  
8. Merge only after Quality Gates PASS.

Quality Gates (blocking):

* Lint: ruff (no warnings) & mypy strict = PASS.  
* Tests: 100% pass; coverage thresholds (domain 90%, overall 85%).  
* Security: Bandit / dependency scan clean; no critical CVEs.  
* Contract Stability: OpenAPI diff shows only allowed changes (non-breaking unless version bump).  
* Performance: Benchmark variance within ±10% of baseline.  
* Tenancy & RBAC: Automated test matrix ensures no cross-tenant data leakage except superadmin explicit case.  
* Migration Safety: Alembic autogenerate diff reviewed; irreversible destructive changes need two approvals + rollback plan.  
* Documentation: Updated quickstart + CHANGELOG + version bump rationale.  
* Observability: New endpoints emit metrics & traces; log fields complete.  
* Complexity Justification: Any new adapter/provider or tenancy mode documented in Complexity Tracking.

Code Review Requirements:

* Two reviewers: one domain, one infra/security for sensitive changes.  
* No commented‑out code; dead code removed.  
* Large PRs (>400 LOC diff) must be split unless refactor-only.  
* Architectural deviations require ADR (Architecture Decision Record) appended.  
* Strict prohibition on TODO without linked task ID.

Branching & Release:

* trunk: always releasable; feature branches prefixed feat/, fix/, chore/, perf/, refactor/, security/.  
* Release tags: vMAJOR.MINOR.PATCH; automated changelog generation.  
* Hotfix: patch branch from tag → tests → merge back.

CI/CD:

* Pipelines: lint → typecheck → unit → integration (parallel shards) → contract diff → security scan → performance smoke → publish artifact.  
* Failing stage aborts pipeline.  
* Promotion to staging auto after green; prod requires manual approval + verification checklist.

## Governance

1. This Constitution supersedes ad hoc preferences.  
2. Amendments require: (a) proposal PR modifying this file (b) impact analysis (c) migration / reversal plan (d) version increment in footer.  
3. Breaking API changes: open deprecation issue + schedule + dual support window documented.  
4. Security & Multi-Tenancy: Any relaxation (e.g., bypassing tenant filter) must have temporary flag + expiry date + audit note.  
5. Complexity Gate: Introducing new storage/messaging/search technology requires: measurable pain + rejected simpler alternative + owner for operations.  
6. Tooling Enforcement: Pre-commit enforces formatting, lint, type; CI enforces gates; merges blocked otherwise.  
7. Superadmin Usage: Must be rare, logged, monitored; repeated cross-tenant queries trigger review.  
8. Data Privacy: Addition of PII field triggers data classification review + encryption decision.  
9. ADR Index maintained; stale ADRs reviewed quarterly.  
10. Emergency Changes: Post‑incident retro must include Constitution compliance gap analysis.

**Version**: 1.5.1 | **Ratified**: 2025-10-02 | **Last Amended**: 2025-10-02
