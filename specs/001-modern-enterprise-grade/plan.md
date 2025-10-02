
# Implementation Plan: Modern Enterprise-Grade Multi-Tenant FastAPI Backend

**Branch**: `001-modern-enterprise-grade` | **Date**: 2025-10-02 | **Spec**: `specs/001-modern-enterprise-grade/spec.md`
**Input**: Feature specification from `/specs/001-modern-enterprise-grade/spec.md`

## Execution Flow (/plan command scope)

```text

1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:

- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

Deliver a reusable, secure, high‑observability multi‑tenant FastAPI backend implementing strict RBAC + policy engine, unified configuration descriptor, auditable events, performance & quality gates, and embed readiness. Phase 0 & 1 artifacts (research.md, data-model.md, contracts/, quickstart.md) are complete; this plan documents architectural alignment and prepares for Phase 2 task generation (NOT executed here). Core emphasis: contract & test first (Principle II), tenant isolation (Principle III), reusable auth core (Principle VI), unified config (Principle VII), observability & performance (Principle V), and code quality & simplicity (Principle IX).

Identity Note: Primary identifiers adopt deterministic UUIDv5 (namespace-based) for tenants, users, and seed baseline entities (replacing earlier exploratory UUIDv7 idea) to guarantee idempotent seeding and stable test fixtures per Constitution Additional Constraints (#10 Identities).

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy (async 2.x), Alembic, python-jose, argon2-cffi, OpenTelemetry (api/sdk + instrumentation), httpx, pytest, ruff, mypy  
**Storage**: PostgreSQL (primary), SQLite (local dev fallback), optional in-memory repositories for tests  
**Testing**: pytest (unit, contract, integration, performance smoke), additional quality gates (xenon/radon, jscpd, safety)  
**Target Platform**: Linux container (prod), macOS/Linux dev  
**Project Type**: Single backend service (future-friendly for monorepo deployment modes)  
**Performance Goals**: CRUD p95 < 200ms, p99 < 400ms; auth token validation p95 < 50ms; heavy ops p95 < 400ms  
**Constraints**: Code quality thresholds (duplication <8%, file <15%, cyclomatic <=10 unless justified); unified configuration only; no direct env access outside config layer  
**Scale/Scope**: Reference dataset ≥10k users, ≥50k audit events, ≥25 policies, ≥1k invitations; concurrency reference 100 (stress 300 informational)

### FR-007 Pluggable Auth Strategy (Password Now, OIDC Deferred)

To satisfy FR-007 in Phase 2, only the password-based provider is implemented while establishing a generic provider interface (`AuthProvider`). OIDC / external SSO providers are explicitly deferred (DEFER-AUTH-15/16) per Clarifications C-024 and C-036. The registry must allow later addition of OIDC without modifying existing password logic or downstream authorization flow.

Phase 2 Scope:

1. Provider interface + registry (AuthProvider) (C-036 ensures single provider until OIDC enabled).
2. Password provider (Argon2id verify + hash upgrade).
3. MFA conditional branching (Hybrid-A) integrated at service layer.

Deferred (Documented Backlog):

1. OIDC discovery + claim validation stub.
2. Full authorization code flow & nonce/state enforcement.
3. Additional social providers.

Security Considerations Now: Restrict provider list to password provider (C-036), validate principal construction & role resolution, audit authentication success/failure, and prepare extension points without speculative code for external IdPs.

### FR-061 / FR-062 MFA Hybrid-A Strategy

Scope (Hybrid-A): Implement only conditional MFA branching for login & password reset, deferring full enrollment lifecycle.

Implemented Now (Phase 2 tasks):

1. Conditional branch in login: if user has ≥1 active factor and no `mfa_code` → respond with standardized `mfa_required` error (audit `auth.mfa.challenge.required`).
2. Validate provided `mfa_code` via MFARepository (in-memory stub) → success audit `auth.mfa.challenge.success`; failure `auth.mfa.challenge.failure` with `mfa_invalid` error.
3. Password reset confirm path: replicate branching to satisfy FR-061 (no factors → direct success) & FR-062 (factors → require `mfa_code`).
4. Seed/dev helper optional: ability to attach a demo TOTP secret to a test user (disabled by default) for local experimentation.

Deferred (Explicit Backlog):

- Endpoints: enroll (provision secret), activate/verify, list, disable factors.
- WebAuthn factors & recovery codes (will require ADR + new FRs).
- Rate limiting / lockout policies on repeated MFA failures.

Test Approach (Phase 2 placeholders first):

- Unit tests: login flow (mfa required vs satisfied), password reset (with vs without MFA factor).
- Contract tests: presence of optional `mfa_code` field; placeholder negative test for missing code when factor exists.
- Security tests (later): replay/incorrect code rate limiting (deferred).

Risks & Mitigation:

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Future enrollment model divergence | Refactor cost | Abstract via MFARepository interface now |
| Ambiguous “MFA enabled” state | Logic bugs | Drive off persisted factor count only |
| Error code inconsistency | UX confusion | Standardize `mfa_required`, `mfa_invalid` in shared error catalogue |

Deferral Note: MFA enrollment lifecycle intentionally deferred; scope limited to conditional enforcement for password reset & login. Adding endpoints requires new FRs.

## Constitution Check

Result: PASS (Initial & Post-Design). No outstanding violations.

| # | Principle Aspect | Status | Notes |
|---|------------------|--------|-------|
| 1 | Hexagonal purity | ✅ | Domain models/interfaces will avoid FastAPI & SQLAlchemy imports; adapters planned under `adapters/` |
| 2 | Contract & Test First | ✅ | OpenAPI fragments authored; placeholder failing contract tests exist (need expansion Phase 2) |
| 3 | Multi-Tenancy | ✅ | Tenant_id required in domain service signatures; soft delete + restore flows (FR-001, FR-018) |
| 4 | RBAC & Policies | ✅ | Policy engine + ALLOW/DENY/ABSTAIN semantics; no inline role branching planned in handlers |
| 5 | Auth Reuse | ✅ | `auth_core/` isolated; only extension registration surfaces referenced |
| 6 | Switchable Persistence | ✅ | Repository interfaces to live in `domain/*/ports`; concrete async SQLAlchemy adapter + in-memory test adapter |
| 7 | Observability | ✅ | Metrics + tracing enumerated; log export + redaction FR-071–073 covered |
| 8 | API Versioning | ✅ | /v1 prefix in contracts; future diff check gate planned |
| 9 | Performance Budgets | ✅ | Clarification C-003 sets explicit p95/p99; regression event FR-074 |
|10 | Unified Config | ✅ | Single descriptor FR-039–048; mutation guard FR-044 |
|11 | Dev Experience & Embed | ✅ | Bootstrap command FR-052; embed flows FR-053–059; mocks documented in quickstart |
|12 | Complexity Justification | ✅ | No extra infra beyond required DB; caching/broker deferred |
|13 | Security Testing | ✅ | OWASP dynamic suite FR-075; rotation, replay, redaction rules captured |
|14 | Code Quality & Simplicity | ✅ | Thresholds C-011; justification registry C-018 pending artifact creation Phase 2 |

Complexity Tracking: (empty – no deviations)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->
```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
```text
src/
   domain/                # Pure domain models & service interfaces (tenant, users, authz, audit, config)
   auth_core/             # Reusable authentication & policy evaluation package (no domain imports)
   adapters/
      api/                 # FastAPI route definitions, request/response mappers
      persistence/         # SQLAlchemy async implementations of repository ports
      logging/             # Structured logging + redaction
      observability/       # Metrics & tracing setup (OpenTelemetry)
      security/            # Token hashing, key rotation hooks
   services/              # Application service orchestrations (thin), calling domain + ports
   schemas/               # Pydantic models (transport boundary)
   cli/                   # Bootstrap & admin scripts (seed, config export)

tests/
   contract/              # OpenAPI contract tests (auto-generated + custom assertions)
   unit/                  # Pure domain & small service tests
   integration/           # Adapter-involved tests (DB, logging)
   performance/           # Latency & regression smoke tests
   security/              # Replay, role escalation, redaction, rate limit
```

Generated Artifacts Directory (this feature): `specs/001-modern-enterprise-grade/`

## Spec ↔ Data Model Alignment

| Entity | FR References | Alignment Status | Notes |
|--------|---------------|------------------|-------|
| Tenant | FR-001, FR-018, FR-039–048, FR-052, FR-077 | ✅ | Added created_by/updated_by (FR-077) – ensure repository populates system actor on seed |
| User | FR-006–009, FR-018, FR-021, FR-049–051, FR-060–065, FR-066–069, FR-077 | ✅ | Invitation → activation path; password hash upgrade handled at login |
| Invitation | FR-006 | ✅ | token_hash SHA-256 per FR-050; acceptance sets accepted_at |
| PasswordResetRequest | FR-060–065 | ✅ | Single-use enforced via consumed_at; hashed token |
| Role | FR-019, FR-031, FR-066–068 | ✅ | Hierarchy & validation enforced in policy layer |
| Policy | FR-004, FR-012, FR-020, FR-029–030, FR-036, FR-077 | ✅ | Version & rollback supported via version field |
| AuditEvent | FR-005, FR-032, FR-071–074 | ✅ | Append-only; actor & action_type categorize events |
| FeatureFlag | FR-026, FR-035, FR-053–059, FR-077 | ✅ | Global vs tenant-scoped; rollout_rules JSON future-ready |
| KeyRotationRecord | FR-022, FR-028 | ✅ | key_version continuity + grace window logic |
| PolicyEvaluationLog | FR-012, FR-020, FR-034, FR-074 | ✅ | Latency captured for regression detection |
| UserMFA | FR-061–062 | ✅ | Optional table; gating logic in auth_core |

Identified Adjustment: Tenant definition updated to include created_by/updated_by (patch applied in data-model.md) to fully satisfy FR-077.

No further misalignments detected; all mutable entities include audit metadata per FR-077.

## Phase Progress Tracking

| Phase | Description | Status | Artifacts |
|-------|-------------|--------|-----------|
| 0 | Research & Clarifications | COMPLETE | `research.md` (decisions locked) |
| 1 | Data Model & Contracts | COMPLETE | `data-model.md`, `contracts/*.yaml`, `quickstart.md` |
| 2 | Task Breakdown | PENDING (next command `/tasks`) | (to create `tasks.md`) |
| 3 | Implementation & Tests | BLOCKED (await tasks) | N/A |
| 4 | Hardening & Performance | BLOCKED | N/A |

Post-Design Constitution Check: PASS (no deviations).

## Phase 2 Preview (Do NOT execute here)

Planned Task Groupings (outline only):

1. Repository & Domain Skeletons (tenant, user, policy, feature flag, audit) + interfaces
2. Auth Core Package scaffolding (hashing, token issuance, policy evaluation stub)
3. Configuration Descriptor & Loader + drift detection & hash logging
4. OpenAPI Contract Test Expansion (cover remaining FR gaps: health, restore, policy dry-run, metrics, config export, token revoke listing)
5. Observability (logging config, redaction, metrics baseline, tracing spans)
6. Seed & Bootstrap command (FR-052, FR-069) + quickstart validation
7. Security & Quality Gates (replay detection stub, code quality metrics integration, justification registry YAML)
8. Embed Flow Endpoints & Rate Limit isolation
9. Performance Regression Event Hook + latency instrumentation
10. Pluggable SSO/OIDC Provider Interface & Stub Implementation (FR-007) + tests
11. MFA Conditional Branching (FR-061/FR-062) – login & password reset + repository stub + failing tests

MFA (Hybrid-A) Task Breakdown:

- T-MFA-01 Create `MFARepository` interface + in-memory implementation (list_factors(user), verify_code(user, code))
- T-MFA-02 Implement login flow conditional MFA branch (return `mfa_required` error if needed)
- T-MFA-03 Implement password reset confirm branch for MFA vs non-MFA users
- T-MFA-04 Add failing unit tests for login & reset MFA scenarios
- T-MFA-05 Add contract test placeholder asserting optional `mfa_code` and `mfa_required` error stub
- T-MFA-06 (Deferred) Design MFA enrollment endpoints (TOTP) + ADR
- T-MFA-07 (Deferred) WebAuthn factor support + recovery codes

Parallelization Notes: Contract tests & repository skeletons can proceed in parallel; auth_core + policy engine baseline must precede RBAC-enforced endpoint handlers; configuration layer precedes any component needing settings.

Exit Criteria for Phase 2: All FRs have at least one mapped task; failing tests created for each new endpoint & critical negative scenarios; justification registry scaffolded; OpenAPI bundle regenerates cleanly.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Scope creep adding non-essential infra (cache, broker) | Delays core delivery | Enforce YAGNI (Principle IX); defer until performance evidence |
| Policy engine complexity early | Slows adoption | Start minimal (deterministic ALLOW/DENY/ABSTAIN + rationale code) then extend DSL |
| Configuration sprawl | Increased cognitive load | Single descriptor + CI drift check FR-039–048 |
| Performance regressions unnoticed | SLA breach | Integrate regression event FR-074 + early latency histograms |
| Test gap on multi-tenancy isolation | Security leak | Mandatory negative cross-tenant tests in contract suite |

## Open Decisions (Monitored)

None (all clarifications resolved). Future ADRs: policy DSL extension, partitioning strategy, embed messaging contract.

## Approval

This plan is ready for `/tasks` execution. No constitution violations pending. Proceed when task breakdown is desired.

**Structure Decision**: (Selected single backend service layout specified above; remove remaining scaffold references during tasks generation.)

## Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

```text
For each unknown in Technical Context:
  Task: "Research {unknown} for {feature context}"
For each technology choice:
  Task: "Find best practices for {tech} in {domain}"
```

1. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts

Prerequisites: research.md complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach

Description: This section describes what the /tasks command will do - DO NOT execute during /plan.

**Task Generation Strategy**:

- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:

- TDD order: Tests before implementation
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

Scope: These phases are beyond the scope of the /plan command.

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Progress Tracking

This checklist is updated during execution flow.

**Phase Status**:

- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [ ] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.5.0 - See `/memory/constitution.md`*
