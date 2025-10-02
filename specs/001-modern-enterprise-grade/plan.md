
# Implementation Plan: Modern Enterprise-Grade Multi-Tenant FastAPI Backend

**Branch**: `001-modern-enterprise-grade` | **Date**: 2025-10-02 | **Spec**: `/specs/001-modern-enterprise-grade/spec.md`
**Input**: Feature specification (see linked spec with Clarifications C-001–C-050 all resolved)

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

Deliver a modern, multi-tenant, enterprise-grade FastAPI backend with: strict tenant isolation, deterministic & idempotent seeding, policy-driven authorization (ALLOW/DENY/ABSTAIN), transparent key rotation, comprehensive structured observability (metrics, tracing, redaction-aware logging), unified configuration governance, and test-first development across all critical paths. Phase 2 operates on in-memory repositories to accelerate contract & behavior validation. Phase 3 introduces an async SQLAlchemy + Alembic persistence layer (with soft-delete oriented design) without regressing existing latency budgets (CRUD p95 < 200ms, p99 < 400ms) or test coverage guarantees (≥90% domain, ≥85% overall, 100% critical path). Performance and governance constraints are enforced via metrics, regression events, and coverage gates.

## Technical Context

**Language/Version**: Python 3.13 (pyproject: >=3.12; target runtime 3.13 for performance & typing improvements)  
**Primary Dependencies**: FastAPI, Pydantic v2, Async SQLAlchemy, Alembic, Argon2 (argon2-cffi), python-jose (JWT), httpx, OpenTelemetry (api/sdk + instrumentation), pytest  
**Storage (Phase 2 → 3)**: Phase 2 in-memory repositories; Phase 3 PostgreSQL via async SQLAlchemy with Alembic migrations (deterministic naming).  
**Testing**: pytest (unit, contract, integration), coverage gate script enforcing Constitution thresholds; future perf harness for latency regression events.  
**Target Platform**: Linux containers & macOS dev (baseline hardware C-015).  
**Project Type**: Backend service (single repository, hexagonal modular domains under `src/domain/*` + adapters).  
**Performance Goals**: CRUD p95 < 200ms / p99 < 400ms; policy eval histogram per C-044; authentication validation p95 < 50ms; bootstrap < 120s (C-034).  
**Constraints**: Multi-tenancy isolation mandatory (implicit tenant filters); config immutability (C-014); redaction of sensitive keys (C-007); deterministic seeding (C-009/C-038); no premature DB coupling pre-Phase 3 (C-050).  
**Scale/Scope (Reference Dataset)**: ≥10k users, ≥50k audit events, ≥25 policies, ≥1k invitations (C-003).  

## Constitution Check

Status (Initial & Post-Design): PASS. No violations requiring Complexity Tracking.

| Principle / Gate | Verification Summary |
|------------------|----------------------|
| Domain Isolation | Domain entities & services avoid framework imports; adapters planned for persistence & observability. |
| Test-First & Coverage | Contract, unit, integration tests scaffold; coverage gate script present; future persistence paths marked critical pending implementation. |
| Multi-Tenancy | Tenant context required for all repository access; superadmin cross-tenant explicit parameter + audit (FR-011). |
| RBAC & Policy Engine | Policy evaluation tri-state; no inline role branching allowed; role hierarchy clarified (C-010). |
| Auth Reuse | Auth core modular; providers pluggable (only password active per C-024/C-036). |
| Switchable Persistence | Repositories interface-first; Phase 2 memory adapters; Phase 3 DB adapter behind ports (C-050). |
| Observability | Metrics (C-030, C-044, C-048), structured logs + redaction (C-005, C-007), tracing planned for API & DB spans. |
| API Versioning | /v1 endpoints initial; deprecation header strategy documented in spec. |
| Performance Budgets | CRUD & heavy operation budgets codified (C-003, C-042, C-074 event triggers). |
| Unified Configuration | Single descriptor, hash excludes secrets (C-037), immutability enforced (C-014). |
| Dev Experience & Embed | Bootstrap <120s (C-034); embed clarifications & docs artifact (C-047). |
| Complexity Governance | No extraneous abstractions; persistence deferred to reduce early complexity (C-050). |
| Security Testing | OWASP cadence & waiver path (C-016); redaction violation handling (C-048). |
| Code Quality | Thresholds & justification registry (C-011, C-018). |

No deviations require entries in Complexity Tracking at this phase.

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
src/
   domain/            # Pure domain logic per bounded context (tenants, users, authz, audit, config, policies, embed)
   adapters/          # Infrastructure edges (api, persistence (Phase 3), logging, observability, security)
   services/          # Application service layer orchestrating domain + adapters
   schemas/           # Pydantic models for API boundary (distinct from domain entities)
   cli/               # Bootstrap / administrative commands (seed, migrate health)
alembic/             # Migration env + versions (Phase 3 persistence)
specs/001-modern-enterprise-grade/  # Feature spec + design artifacts
tests/
   unit/
   contract/
   integration/
   performance/ (future regression harness)
scripts/             # Utility scripts (coverage gate, quality checks)
```

**Structure Decision**: Single backend service (hexagonal). Persistence added in Phase 3 via `adapters/persistence` & `alembic` without altering domain package boundaries.

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

3. **Consolidate findings** in `research.md` using format:
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

Scope: Beyond /plan command (planning only). Key forward-looking commitments:

**Phase 3 (Persistence Introduction)**:

- Implement async SQLAlchemy models & Alembic initial migration (deterministic naming conventions `pk_`, `fk_`, `ix_`, `uq_`).
- Add repository adapters; maintain interface parity with in-memory versions (parity test first).
- Enforce soft delete semantics (tenants, users) with RESTRICT FKs—no large fan-out physical cascades; limited CASCADE only for ephemeral or association tables (password_resets, user_roles) per updated Performance Considerations note to avoid contradiction.
- Introduce slow query logging + histogram integration; threshold default 100ms (configurable via `DB_SLOW_QUERY_THRESHOLD_MS`).
- Seed script upgrades to durable mode preserving deterministic IDs (C-009/C-038) & conflict detection (C-043).
- Migration head health surfaced in health endpoint (FR-015) and drift detection gating startup if mismatch (task-based enforcement).

**Phase 4 (Feature Hardening & Observability Depth)**:

- Performance regression harness, partitioning ADR (high-write logs), retention policy configuration (evaluation logs), redaction violation sampling improvements.

**Phase 5 (Validation & Optimization)**:

- Full latency + load validation across persistence-backed paths; coverage gate elevation to enforce critical persistence paths (adapters/persistence, migrations) at 100%.

This staging ensures persistence introduction does not regress latency budgets or violate the earlier mandate to avoid broad cascade deletes.

## Complexity Tracking

Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Progress Tracking

This checklist is updated during execution flow.

**Phase Status**:

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning approach documented (this file) (no tasks.md generation yet)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (C-001–C-050)
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v1.5.1 - See `/memory/constitution.md`*
