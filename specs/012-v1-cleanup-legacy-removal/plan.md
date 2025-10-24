
# Implementation Plan: V1.0 Release - Legacy Code Removal & Cleanup

**Branch**: `012-v1-cleanup-legacy-removal` | **Date**: 2025-10-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/sujoymukherjee/code/githubspeckit/specs/012-v1-cleanup-legacy-removal/spec.md`

## Execution Flow (/plan command scope)
```
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

Prepare the codebase for V1.0 production release by removing all backward compatibility code, legacy APIs, and deprecated patterns. This is a **breaking change release** that establishes V1.0 as the stable API contract. Key deliverables include:

1. **Code Cleanup**: Remove deprecated middleware (`DeprecationMiddleware`, `DeprecationWarningMiddleware`) and all backward compatibility logic
2. **Route Unification**: Migrate all admin endpoints to `/api/v1/admin/*` prefix (removing legacy flat `/api/*` patterns)
3. **Email Uniqueness**: Change database constraint from global unique email to per-tenant unique (email, tenant_id)
4. **Schema Publication**: Generate V1.0 database schema documentation with SchemaSpy-generated ERD and HTML docs
5. **Dev Environment**: Complete Docker Compose setup (PostgreSQL, Redis, pgAdmin, API) for turnkey contributor experience
6. **Documentation**: Publish OpenAPI v1.0.0 spec, migration guide, and updated developer quickstart

**Technical Approach**: Database migration with constraint modification, route prefix updates via FastAPI router includes, middleware removal, comprehensive test updates, and automated schema documentation generation via SchemaSpy with CI integration.

## Technical Context

**Language/Version**: Python 3.13+ (3.12+ compatible)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, asyncpg, python-jose, Argon2  
**Storage**: PostgreSQL (primary production), Redis (caching/rate limiting)  
**Testing**: pytest, pytest-asyncio, httpx (async client), coverage  
**Target Platform**: Linux server (production), macOS/Linux (dev)  
**Project Type**: Backend API (single project, hexagonal architecture)  
**Performance Goals**: p95 < 200ms CRUD operations, p99 < 500ms heavy operations, login p95 < 300ms  
**Constraints**: Zero breaking changes to V1.0 API contract after release, maintain >85% test coverage overall, >90% domain coverage  
**Scale/Scope**: Multi-tenant SaaS with RBAC, ~50 API endpoints, 12 database tables, estimated 10k+ users per tenant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluate and explicitly confirm (checklist) before proceeding:

1. **Architecture**: ✅ PASS - No new domain logic added, only cleanup of adapters/API layer (Principle I)
2. **Test-First & Coverage**: ✅ PASS - Contract tests for email uniqueness exist, migration tests planned, route tests to be updated, coverage maintained at >85% overall, >90% domain (Principle II)
3. **Multi-Tenancy**: ✅ PASS - Email uniqueness change **strengthens** tenant isolation (per-tenant constraint), no new data access paths (Principles I & III)
4. **RBAC & Policies**: ✅ PASS - No authorization changes, existing RBAC enforcement continues (Principles III & VI)
5. **Auth Reuse**: ✅ PASS - No auth core modifications (Principle VI)
6. **Switchable Persistence**: ✅ PASS - Repository interfaces unchanged, only database constraint modified via Alembic (Principle IV)
7. **Observability**: ✅ PASS - Audit events include version metadata (v1.0.0), metrics dashboards updated for new route patterns, log aggregation queries updated (NFR-027) (Principle V)
8. **API Versioning**: ✅ PASS - OpenAPI spec version bumped to 1.0.0, breaking changes documented in CHANGELOG-V1.0.md and MIGRATION-TO-V1.0.md (Principle V)
9. **Performance Budgets**: ✅ PASS - Benchmark tests ensure p95 latency within 5% of pre-V1.0, database query plans reviewed for new constraints (NFR-026) (Principle V)
10. **Unified Configuration**: ✅ PASS - Docker Compose uses existing env variables, `.env.example` to be created as part of FR-121 (Principle VII)
11. **Developer Experience & Embed**: ⚠️ NEEDS REVIEW - Docker Compose addition justified (FR-121: <5 min turnkey setup for contributors), existing `make bootstrap` remains primary path (Principle VIII)
12. **Complexity**: ⚠️ NEEDS JUSTIFICATION - Docker Compose adds infrastructure complexity, SchemaSpy adds Java dependency (see Complexity Tracking) (Governance & Principle IV)
13. **Security Testing**: ✅ PASS - Email enumeration protection via rate limiting (SEC-023: 100 attempts/hour/IP), migration data integrity validation (SEC-024), existing OWASP tests continue (Additional Constraints & Principle V)
14. **Code Quality & Simplicity**: ✅ PASS - Feature **removes** complexity (deprecated middleware, legacy routes, commented code), duplication reduced (Principle IX)

**Summary**: 12/14 PASS, 2 NEEDS JUSTIFICATION (see Complexity Tracking below)

Document any violation in Complexity Tracking with justification BEFORE continuing.

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

```text
# Backend API (Hexagonal Architecture)
src/
├── domain/                        # Pure domain logic (no changes)
│   ├── tenants/
│   ├── users/
│   ├── authz/                    # RBAC + policy engine
│   └── audit/
├── adapters/
│   ├── api/
│   │   ├── app.py                # ⚠️ MODIFIED: Remove DeprecationMiddleware, update router includes
│   │   ├── routes/               # ⚠️ MODIFIED: Update route paths to /api/v1/admin/*
│   │   ├── middleware/
│   │   │   ├── deprecation_warning.py  # ❌ DELETE
│   │   └── deprecation.py        # ❌ DELETE
│   ├── persistence/              # ⚠️ MODIFIED: Users repository for email constraint
│   └── observability/            # Metrics, logging (no changes)
├── auth_core/                    # Reusable auth package (no changes)
└── services/                     # Application services (no changes)

alembic/
└── versions/
    └── XXXX_email_uniqueness_per_tenant.py  # ✅ NEW: Migration for constraint change

tests/
├── contract/
│   ├── test_email_uniqueness_*.py      # ⚠️ MODIFIED: Update for per-tenant uniqueness
│   └── test_openapi_*.py               # ⚠️ MODIFIED: Validate v1.0.0 spec
├── integration/
│   ├── test_routes_*.py                # ⚠️ MODIFIED: Update all route paths
│   └── test_deprecated_*.py            # ❌ DELETE: Legacy compatibility tests
└── unit/
    └── test_user_repository.py         # ⚠️ MODIFIED: Per-tenant uniqueness logic

docs/
├── database-schema-v1.0.sql      # ✅ NEW: Generated DDL export
├── database-erd-v1.0.png         # ✅ NEW: SchemaSpy-generated ERD
├── database-indexes-v1.0.md      # ✅ NEW: Index documentation
├── migration-to-v1.0.md          # ✅ NEW: Migration guide
├── CHANGELOG-V1.0.md             # ✅ NEW: Breaking changes log
└── schemaspy/                    # ✅ NEW: SchemaSpy HTML output (interactive docs)

contracts/
└── openapi-v1.0.yaml             # ⚠️ MODIFIED: Version bump, remove deprecated endpoints

config/
└── descriptor.toml               # ⚠️ MODIFIED: Add RATE_LIMIT_USER_CREATION

docker-compose.yml                # ✅ NEW: PostgreSQL + Redis + pgAdmin + API
.env.example                      # ✅ NEW: Environment variable template
README.md                         # ⚠️ MODIFIED: Updated quickstart
CONTRIBUTING.md                   # ✅ NEW: Contributor guide
```

**Structure Decision**: Hexagonal architecture (single backend project) with domain isolation intact. This cleanup feature primarily modifies adapters (API routes, middleware), database migrations, and documentation. No frontend components exist. Docker Compose setup is additive (no code changes required in src/).

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

The /tasks command will generate implementation tasks organized by functional requirement (FR-114 through FR-121) from the feature spec. Each FR maps to a task group:

1. **FR-114 (Remove Backward Compatibility Code)**:
   - Task: Delete deprecated middleware files (`deprecation.py`, `deprecation_warning.py`)
   - Task: Remove middleware registration from `app.py`
   - Task: Update tests (remove deprecated middleware tests)
   - **Parallel**: All file deletions can be done in parallel [P]

2. **FR-115 (Unified Route Prefix Structure)**:
   - Task: Update router includes in `app.py` to use `/api/v1/admin` prefix
   - Task: Update all route path strings in router files (if any hardcoded paths)
   - Task: Update test fixtures to use new route paths
   - Task: Validate OpenAPI spec reflects new paths
   - **Dependencies**: Route updates before test updates

3. **FR-116 (Per-Tenant Email Uniqueness)**:
   - Task: Create Alembic migration (per research.md patterns)
   - Task: Create pre-migration validation script (`scripts/validate_email_migration.py`)
   - Task: Update user repository validation logic (check_email_exists scoped to tenant)
   - Task: Update contract tests (`test_email_uniqueness_*.py`)
   - **Dependencies**: Validation script → Migration → Repository logic → Tests

4. **FR-117 (Database Schema V1.0 Finalization)**:
   - Task: Add schema_version table via Alembic migration
   - Task: Create Makefile target `make schemaspy` (per research.md)
   - Task: Generate schema documentation (run SchemaSpy)
   - Task: Export DDL to `docs/database-schema-v1.0.sql`
   - Task: Create `docs/database-indexes-v1.0.md`
   - **Dependencies**: schema_version table → SchemaSpy setup → documentation generation

5. **FR-118 (Legacy Test Code Removal)**:
   - Task: Identify and delete commented-out tests
   - Task: Delete legacy compatibility test files
   - Task: Review and fix/remove skipped tests
   - Task: Validate coverage remains >85% overall, >90% domain
   - **Parallel**: File deletions [P]; Coverage validation last

6. **FR-119 (OpenAPI Spec V1.0 Publication)**:
   - Task: Update `app.py` FastAPI version to "1.0.0"
   - Task: Update description with breaking changes summary
   - Task: Regenerate OpenAPI spec (contracts/openapi-v1.0.yaml)
   - Task: Validate with Schemathesis contract tests
   - **Dependencies**: Version update → Regeneration → Validation

7. **FR-120 (Documentation & Migration Guide)**:
   - Task: Create `docs/CHANGELOG-V1.0.md` (breaking changes)
   - Task: Create `docs/MIGRATION-TO-V1.0.md` (upgrade guide)
   - Task: Update README.md (V1.0 quickstart)
   - Task: Update API documentation references
   - **Parallel**: All documentation files [P]

8. **FR-121 (Complete Dev Environment Setup)**:
   - Task: Create `docker-compose.yml` (per research.md design)
   - Task: Create `.env.example` with all required variables
   - Task: Create Makefile targets (docker-up, docker-down, docker-logs, docker-reset)
   - Task: Create `CONTRIBUTING.md` (contributor guide)
   - Task: Update README.md (Docker setup section)
   - Task: Test bootstrap flow (<5 min validation)
   - **Dependencies**: docker-compose.yml → Makefile targets → Documentation → Validation

**Ordering Strategy**:

- **Phase 1 (Cleanup)**: FR-114, FR-118 (remove deprecated code first)
- **Phase 2 (Database)**: FR-116, FR-117 (schema changes + documentation)
- **Phase 3 (API)**: FR-115, FR-119 (route changes + OpenAPI spec)
- **Phase 4 (Infrastructure)**: FR-121 (Docker Compose)
- **Phase 5 (Documentation)**: FR-120 (comprehensive guides)

**Parallelization Markers**:
- [P]: Independent file operations (deletions, documentation)
- Sequential: Database migrations, route updates (change → test → validate)

**Estimated Output**: 40-45 numbered tasks organized by FR, with clear dependencies and parallel execution opportunities

**Validation Checkpoints**:
1. After FR-114/118: All tests green (coverage maintained)
2. After FR-116: Migration rollback tested, constraint enforcement validated
3. After FR-115/119: OpenAPI spec validated, all route tests passing
4. After FR-121: Docker bootstrap completes <5 min, health check succeeds
5. After FR-120: Documentation reviewed for accuracy and completeness

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
| Docker Compose setup (new infra) | FR-121: <5 minute turnkey contributor experience (open source readiness), addresses contributor friction of manual PostgreSQL + Redis setup | Manual setup requires contributors to install/configure PostgreSQL (psql CLI, createdb, user permissions), Redis server, and understand platform-specific variations (Homebrew on macOS, apt on Ubuntu, etc.). Contributor attrition observed in similar projects. Docker Compose provides deterministic, isolated environment with `docker-compose up` single command. |
| SchemaSpy (Java dependency) | FR-117: Production-grade ERD generation + interactive HTML documentation (comprehensive schema browsing, automatic relationship detection, SQL DDL export) required for V1.0 release | Alternatives: (1) Python ERD libs (sqlalchemy_schemadisplay, eralchemy): Limited relationship detection, no HTML docs, PNG-only. (2) dbdiagram.io: Manual schema entry, not automated. (3) Manual Mermaid: High maintenance burden, no interactive drill-down. SchemaSpy provides comprehensive, automated, professional documentation matching enterprise expectations with minimal ongoing dev load (one-time CI setup). |
| Make-primary + Docker Compose (dual workflows) | FR-121 clarification: Native development remains default for core team velocity (no Docker overhead), Docker Compose provides optional isolated environment for occasional contributors without polluting host system | Forcing Docker-only would slow core team iteration (container rebuild cycles, volume mount performance on macOS). Forcing native-only blocks contributors without PostgreSQL/Redis expertise or on restrictive corporate laptops. Dual approach maximizes developer choice. |


## Progress Tracking

This checklist is updated during execution flow.

**Phase Status**:

- [x] Phase 0: Research complete (/plan command) - ✅ research.md exists with 7 research areas
- [x] Phase 1: Design complete (/plan command) - ✅ data-model.md exists, contracts/openapi-v1.0.yaml exists, quickstart.md exists
- [x] Phase 2: Task planning complete (/plan command - describe approach only) - ✅ 40-45 tasks across 8 FRs planned
- [ ] Phase 3: Tasks generated (/tasks command) - **NEXT STEP**
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS (12/14, 2 justified in Complexity Tracking)
- [x] Post-Design Constitution Check: PASS (all 14 items PASS or JUSTIFIED after Phase 1)
- [x] All NEEDS CLARIFICATION resolved (via clarification session - 10 Q&As documented in spec.md)
- [x] Complexity deviations documented (Docker Compose, SchemaSpy, dual workflows)

---
*Based on Constitution v1.5.1 - See `/memory/constitution.md`*
