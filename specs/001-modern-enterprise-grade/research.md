# Phase 0 Research & Decisions

Source Spec: `/specs/001-modern-enterprise-grade/spec.md`
Date: 2025-10-02

## Methodology

Extracted all clarifications (C-001–C-018), mapped to functional requirements, validated against Constitution v1.5.0 principles. Focus: eliminate residual ambiguity before Phase 1 design generation.

## Decisions

### D-001 Language & Runtime

- Decision: Python 3.13
- Rationale: Matches modern typing (PEP 695 generics) and performance improvements; ecosystem maturity for FastAPI & async.
- Alternatives: 3.11 (stable but 3.12 is current), Rust (higher complexity), Go (less native Pydantic integration).

### D-002 Web Framework

- Decision: FastAPI
- Rationale: Async-first, OpenAPI generation, ecosystem alignment with spec.
- Alternatives: Starlette (lower-level), Django (heavier ORM coupling), Flask (sync-first).

### D-003 Auth Core Packaging

- Decision: Internal `auth_core/` Python package.
- Rationale: Enforces reuse, decouples domain from auth specifics, enables potential publishing.
- Alternatives: Monolithic package (reduces clarity), External identity provider only (limits policy flexibility early).

### D-004 Password Hashing

- Decision: Argon2id via argon2-cffi with configurable memory/time/parallelism.
- Rationale: Recommended PHC winner, resistant to GPU attacks.
- Alternatives: bcrypt (wider legacy), scrypt (similar profile), PBKDF2 (slower vs modern GPU resistance).

### D-005 Token Storage Hashing

- Decision: SHA-256 hashing of sensitive tokens before persistence.
- Rationale: Prevent token leakage from storage; aligns with FR-050.
- Alternatives: BLAKE2 (could be future enhancement), SHA-512 (more output, no significant gain here).

### D-006 Repository Abstraction

- Decision: Interface-style protocols + SQLAlchemy 2 async implementation.
- Rationale: Switchable persistence (Principle IV) while leveraging mature ORM.
- Alternatives: Direct SQL (leaner but increases duplication), Prisma (less Python maturity), Tortoise ORM (less adoption).

### D-007 Configuration Descriptor Format

- Decision: `config/descriptor.toml` + generated `.env.example`.
- Rationale: TOML readability, tooling ease.
- Alternatives: YAML (indent issues), JSON (no comments), Python settings module (execution risk).

### D-008 Logging & Observability Stack

- Decision: Standard logging + structlog-like adapter (or pure structured JSON formatter) + OpenTelemetry metrics/traces.
- Rationale: Simplicity, minimal vendor lock.
- Alternatives: Direct ELK integration (heavier), proprietary APM SDK (lock-in).

### D-009 Metrics Implementation

- Decision: OpenTelemetry SDK + Prometheus exporter.
- Rationale: Open standard, broad tooling.
- Alternatives: StatsD only (narrow), bespoke counters (reinventing wheel).

### D-010 Rate Limiting

- Decision: Token bucket using optional Redis backend; in-memory fallback for dev.
- Rationale: Scalability + dev friendliness.
- Alternatives: External API gateway only (reduces portability), purely in-memory (non-scalable).

### D-011 Performance Regression Detection

- Decision: Compare latency histograms from test harness vs thresholds, emit event.
- Rationale: Lightweight, CI integrable.
- Alternatives: Full APM anomaly detection (overkill early).

### D-012 Seed Strategy

- Decision: Deterministic UUIDv5 for TestTenant (namespace + slug) and baseline users (namespace + normalized email) enabling idempotent seed re-runs & stable integration test references.
- Rationale: Simplifies test fixtures, cross-env diffing, reproducible migrations; time-ordering needs satisfied by created_at.
- Alternatives: UUIDv7 (time-ordered but non-deterministic for idempotent seed), random UUIDv4 (no deterministic upsert), database-generated sequences (break portability, leak ordering semantics).

### D-013 Policy Engine

- Decision: Pure function evaluation with ALLOW/DENY/ABSTAIN result object + rationale.
- Rationale: Testability & composability.
- Alternatives: DSL engine (higher complexity now), rule engine library (overkill initial scope).

### D-014 Redaction

- Decision: Middleware scanning configured keys + structured field replacement with `REDACTED`.
- Rationale: Simplicity + central enforcement.
- Alternatives: Logger patching per call site (error prone), external proxy sanitizer (extra moving part).

### D-015 Code Quality Measurement

- Decision: Use radon (complexity) + duplication tool (e.g., jscpd) invoked via `quality_gate.py`.
- Rationale: Commodity tools, script orchestrates gating.
- Alternatives: SonarQube (heavier infra), custom AST walker (reinvention).

### D-016 Contract Testing

- Decision: Generate OpenAPI spec fragments per endpoint + pytest contract tests using pydantic validation.
- Rationale: Ensures spec & implementation parity.
- Alternatives: Postman collections (external), bespoke schema assertions.

### D-017 Embed Tokens

- Decision: Short-lived one-time token endpoint separate from standard login, invalidated on exchange.
- Rationale: Limits replay & leak surface.
- Alternatives: Direct session cookie issuance (less control), long-lived embed keys (higher risk).

### D-018 Justification Registry

- Decision: `quality_justifications.yml` with ID, rationale, owner, expiry.
- Rationale: Prevents permanent exceptions.
- Alternatives: Inline comments only (no lifecycle), database table (overkill initial).

## Deferrals / Not in Initial Scope

- Full multi-strategy tenancy (schema/db-per-tenant) – ADR placeholder for future.
- Advanced replay protection store (initial minimal nonce store only).
- Continuous profiling integration (placeholder instrumentation hooks only).
- External message bus, search engine, object storage.
- Multi-region failover.

## Risk & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Argon2 parameter misconfiguration | Weak hashing security | Central config with safe defaults + test asserting min cost |
| Logging PII leak | Compliance & breach risk | Redaction middleware + violation audit + CI sample log scan |
| Schema drift vs descriptor | Startup/runtime errors | Descriptor validation & drift detection feature |
| Performance regressions hidden | SLA breach | regression event + CI threshold gating |
| Policy engine misuse | Authorization gaps | Provide reference policies + denial tests template |

## Open Items

None (all clarifications resolved).

## Phase 0 Completion

All decisions mapped; no unresolved NEEDS CLARIFICATION markers remain.
