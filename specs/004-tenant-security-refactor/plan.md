
# Implementation Plan: Tenant Context Security Refactor

**Branch**: `004-tenant-security-refactor` | **Date**: 2025-10-19 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/Users/sujoymukherjee/code/githubspeckit/specs/004-tenant-security-refactor/spec.md`

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

Remediate OWASP A01:2021 Broken Access Control vulnerability by refactoring tenant_id from user-controlled query parameters to secure JWT claims + path parameters + session-based patterns. Implements comprehensive route reorganization with 5 route categories: PUBLIC, ADMIN, TENANT-SCOPED, SELF-SERVICE, and DOMAIN routes. Prevents IDOR attacks while maintaining backward compatibility via 30-day deprecation period.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastAPI 0.104+, Pydantic v2, python-jose (JWT), starlette.middleware.sessions  
**Storage**: PostgreSQL (existing schema, no changes), Redis (session storage)  
**Testing**: pytest, pytest-asyncio, httpx (test client), OWASP ZAP (security scanning)  
**Target Platform**: Linux server (Docker containerized)  
**Project Type**: Web (backend API only, hexagonal architecture)  
**Performance Goals**: <5ms JWT extraction overhead (p95), <2ms middleware overhead (p99)  
**Constraints**: Zero database schema changes, 30-day deprecation period, maintain existing JWT structure  
**Scale/Scope**: 8 router files, 22 contract tests, 7 integration tests, 5 new middleware components

**Route Organization Strategy** (user-provided clarification):

The refactor implements a 5-tier route hierarchy replacing the current flat `/api/v1/*` structure:

1. **PUBLIC Routes** (`/api/v1/auth/*`):
   - No authentication required
   - Rate-limited by IP
   - Examples: login, token refresh, password reset

2. **ADMIN Routes** (`/api/v1/admin/*`):
   - Platform administration operations
   - Superadmin: Full cross-tenant access
   - Tenant Admin: Scoped to their tenant_id (RBAC enforced)
   - Examples: Create tenant, cross-tenant user search, platform settings

3. **TENANT-SCOPED Routes** (`/api/v1/tenants/{tenant_id}/*`):
   - Operations scoped to explicit tenant_id in path
   - RBAC enforces: `user.tenant_id == path.tenant_id` unless superadmin
   - Examples: `/api/v1/tenants/{tenant_id}/users`, `/api/v1/tenants/{tenant_id}/policies`

4. **SELF-SERVICE Routes** (`/api/v1/users/*`):
   - Current user operations
   - `/me` endpoints for profile, preferences, notifications
   - RBAC: Users edit own data; admins edit subordinates

5. **DOMAIN Routes** (`/api/v1/{domain_resource}/*`):
   - Custom tenant application domains
   - Tenant-scoped by default (implicit tenant_id from JWT)
   - Examples: `/api/v1/projects`, `/api/v1/orders`, `/api/v1/documents`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluate and explicitly confirm (checklist) before proceeding:

1. ✅ **Architecture**: Domain layer free of framework/infrastructure imports (Principle I).
   - TenantContext middleware stays in adapters layer
   - Domain services receive tenant_id as parameter (no FastAPI imports)

2. ✅ **Test-First & Coverage**: Planned failing tests exist AND projected coverage meets thresholds (≥90% domain, ≥85% overall; 100% critical auth/tenancy paths) (Principle II).
   - 22 contract tests (RBAC + tenant isolation scenarios)
   - 7 integration tests (cross-tenant access attempts, session switching)
   - 100% coverage: `src/adapters/api/middleware/tenant_context.py` (critical path)

3. ✅ **Multi-Tenancy**: Every new data access path includes tenant context + filtering (Principles I & III).
   - Middleware extracts tenant_id from JWT claims for every request
   - Path-based tenant scoping for superadmin cross-tenant operations
   - Session-based tenant switching (superadmin UI only)

4. ✅ **RBAC & Policies**: Authorization expressed via registered policies—no inline role branching (Principles III & VI).
   - Authorization middleware checks policies (not inline `if is_superadmin`)
   - Policy engine evaluates: `user.tenant_id == requested_tenant_id OR isSuperadmin(user)`

5. ✅ **Auth Reuse**: No domain-specific logic added inside auth core; only registrations/extensions (Principle VI).
   - Tenant context extraction uses existing `auth_core` interfaces
   - No modifications to JWT token structure (tenant_id already exists)

6. ✅ **Switchable Persistence**: Repositories stay interface-driven; no leakage of ORM/session into domain (Principle IV).
   - No database schema changes required
   - Repositories already accept tenant_id parameter

7. ✅ **Observability**: Planned metrics, centrally configurable structured logs (export + redaction), tracing spans for each new boundary (Principle V).
   - Audit events: `security.tenant_context.extracted`, `auth.cross_tenant.denied`, `auth.cross_tenant.allowed`
   - Metrics: `tenant_context_extraction_duration`, `auth_tenant_isolation_violations`
   - OpenTelemetry spans: Middleware execution, policy evaluation

8. ✅ **API Versioning**: New/changed endpoints supply version impact assessment (Principle V).
   - **Breaking Change**: Query parameter `?tenant_id=` removed
   - **Mitigation**: 30-day deprecation period + `Deprecation: true` header
   - **Migration Guide**: Published in `docs/MIGRATION_TENANT_SECURITY.md`

9. ✅ **Performance Budgets**: Declared baseline p95/p99 expectations (Principle V).
   - JWT extraction: <5ms overhead (p95)
   - Middleware: <2ms per request (p99)
   - No database queries for tenant validation

10. ✅ **Unified Configuration**: Single descriptor (no direct env access) + DEPLOY_MODE implications addressed (Principle VII).
    - Session backend configurable: `SESSION_BACKEND=cookie|redis` (config/descriptor.toml)
    - Session secret: `SESSION_SECRET=${SESSION_SECRET}` (environment variable)

11. ✅ **Developer Experience & Embed**: Minimal local infra (fallback mocks) + embed session/cookie strategy documented (Principle VIII).
    - Local dev: Encrypted cookie sessions (no Redis required)
    - Production: Redis session storage (optional)
    - Embed-ready: `SameSite=None; Secure` for iframe compatibility

12. ✅ **Complexity**: Any new adapter/infra addition justified vs simpler alternative (Governance & Principle IV).
    - Session middleware: Justified for superadmin tenant switching (alternative: re-authentication rejected due to UX)
    - No new databases or external services

13. ✅ **Security Testing**: OWASP Top 10 mapping updates + dynamic/pen test considerations documented (Additional Constraints & Principle V).
    - OWASP ZAP authenticated scan: IDOR vulnerability tests
    - Penetration test scenarios: Cross-tenant access attempts, session hijacking
    - Security contract tests: 008-security-idor-tests (separate feature)

14. ✅ **Code Quality & Simplicity**: DRY/KISS/YAGNI respected; no premature abstractions; duplication/complexity impact considered (Principle IX).
    - Single middleware component (tenant context extraction + validation)
    - No over-engineering: Path-based routing uses FastAPI native features
    - DRY: Common authorization logic in reusable middleware

**Initial Constitution Check**: ✅ PASS (no violations)

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
src/
├── adapters/
│   └── api/
│       ├── middleware/
│       │   ├── tenant_context.py         # NEW: Tenant extraction middleware
│       │   ├── authorization.py          # NEW: Tenant isolation enforcement
│       │   └── session.py                # NEW: Session management
│       └── routers/
│           ├── auth.py                   # MODIFIED: Add /admin/context/tenant
│           ├── admin/                    # NEW: Admin-scoped routes
│           │   ├── tenants.py            # MODIFIED: Move from /tenants
│           │   ├── users.py              # MODIFIED: Cross-tenant user mgmt
│           │   └── policies.py           # MODIFIED: Platform policies
│           ├── tenants/                  # NEW: Tenant-scoped routes
│           │   ├── users.py              # NEW: /tenants/{id}/users
│           │   ├── policies.py           # NEW: /tenants/{id}/policies
│           │   └── settings.py           # NEW: /tenants/{id}/settings
│           └── users/
│               ├── me.py                 # NEW: /users/me endpoints
│               └── profile.py            # MODIFIED: Self-service routes
├── domain/
│   └── tenants/
│       └── tenant_context.py             # NEW: Domain model (no FastAPI deps)
└── auth_core/
    └── tenant_resolution.py              # MODIFIED: Extract tenant from JWT

tests/
├── contract/
│   ├── admin/
│   │   ├── test_admin_tenants.py         # MODIFIED: Update for path params
│   │   ├── test_admin_users.py           # MODIFIED: Cross-tenant scenarios
│   │   └── test_admin_policies.py        # MODIFIED: Platform policies
│   ├── tenants/
│   │   ├── test_tenant_users.py          # NEW: Tenant-scoped user tests
│   │   ├── test_tenant_policies.py       # NEW: Tenant-scoped policy tests
│   │   └── test_tenant_isolation.py      # NEW: IDOR protection tests
│   └── users/
│       └── test_me_endpoints.py          # NEW: Self-service tests
├── integration/
│   ├── test_tenant_security.py           # NEW: End-to-end security tests
│   ├── test_superadmin_switching.py      # NEW: Session tenant switching
│   └── test_rbac_tenant_isolation.py     # MODIFIED: Update expectations
└── unit/
    └── middleware/
        ├── test_tenant_context.py        # NEW: Middleware unit tests
        └── test_authorization.py         # NEW: Policy enforcement tests
```

**Structure Decision**: 

Hexagonal architecture (Principle I) with adapters layer for FastAPI-specific code. This refactor:

1. **Adds 3 new middleware components** (`tenant_context.py`, `authorization.py`, `session.py`)
2. **Reorganizes routes into 5 categories**:
   - PUBLIC: Existing `/api/v1/auth/*` (no changes)
   - ADMIN: New `/api/v1/admin/*` hierarchy (moved from flat structure)
   - TENANT-SCOPED: New `/api/v1/tenants/{tenant_id}/*` routes
   - SELF-SERVICE: New `/api/v1/users/me` endpoints
   - DOMAIN: Future tenant app routes (implicit tenant_id from JWT)
3. **Updates 22 contract tests** to validate new route patterns
4. **Adds 7 integration tests** for security scenarios (IDOR, session switching)
5. **Maintains domain purity**: `domain/tenants/tenant_context.py` has zero FastAPI imports

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

The /tasks command will generate implementation tasks following TDD principles:

1. **Domain Layer Tasks** (6 tasks):
   - T001: Create TenantContext domain model [P]
   - T002: Create TenantAccessPolicy domain service [P]
   - T003: Create PolicyEvaluationResult value object [P]
   - T004-006: Unit tests for domain models

2. **Middleware Tasks** (9 tasks):
   - T007: Create TenantContextMiddleware (JWT extraction) [P]
   - T008: Create AuthorizationMiddleware (policy enforcement) [P]
   - T009: Create SessionMiddleware configuration
   - T010-015: Unit tests for middleware components

3. **Route Refactoring Tasks** (12 tasks):
   - T016: Refactor admin routes to `/api/v1/admin/*` hierarchy
   - T017: Create tenant-scoped routes `/api/v1/tenants/{id}/*`
   - T018: Create self-service routes `/api/v1/users/me`
   - T019: Add tenant switching endpoint `/admin/context/tenant`
   - T020-027: Update 8 router files with new patterns

4. **Contract Test Tasks** (22 tasks):
   - T028-035: Admin route contract tests (cross-tenant scenarios)
   - T036-041: Tenant-scoped route contract tests (RBAC validation)
   - T042-045: Self-service route contract tests
   - T046-049: IDOR protection tests (expect 403)

5. **Integration Test Tasks** (7 tasks):
   - T050: Superadmin tenant switching flow
   - T051: Standard user cross-tenant denial
   - T052: Session expiration test
   - T053: JWT tenant override (superadmin)
   - T054: Backward compatibility (deprecation warnings)
   - T055: Performance baseline (<5ms overhead)
   - T056: Audit logging completeness

6. **Migration Tasks** (5 tasks):
   - T057: Add deprecation middleware (30-day grace period)
   - T058: Create migration guide documentation
   - T059: Update OpenAPI specs (remove query params)
   - T060: Add sunset date enforcement (2025-11-19)
   - T061: Update integration tests for new patterns

**Ordering Strategy**:

1. **Phase 1 (Domain)**: T001-T006 (domain models + tests) - Foundation layer
2. **Phase 2 (Middleware)**: T007-T015 (middleware + tests) - Cross-cutting concerns
3. **Phase 3 (Routes)**: T016-T027 (route refactoring) - API changes
4. **Phase 4 (Testing)**: T028-T056 (contract + integration tests) - Validation
5. **Phase 5 (Migration)**: T057-T061 (deprecation + docs) - Rollout support

**Parallelization**:

- Tasks marked [P] can execute in parallel (no dependencies)
- Domain model creation (T001-T003) can run concurrently
- Middleware creation (T007-T009) can run concurrently after domain models complete
- Contract test files (T028-T049) can run in parallel after routes refactored

**Estimated Output**: 61 numbered, ordered tasks in tasks.md

**Critical Path**: T001 → T007 → T016 → T028 → T050 (domain → middleware → routes → tests → integration)

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

- [x] Phase 0: Research complete (/plan command) - ✅ research.md generated
- [x] Phase 1: Design complete (/plan command) - ✅ data-model.md, contracts/, quickstart.md generated
- [x] Phase 2: Task planning complete (/plan command - describe approach only) - ✅ 61 tasks described
- [x] Phase 3: Tasks generated (/tasks command) - ✅ tasks.md with 61 ordered tasks
- [ ] Phase 4: Implementation complete (execute tasks T001-T061)
- [ ] Phase 5: Validation passed (run quickstart.md scenarios)

**Gate Status**:

- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅ (no new violations introduced)
- [x] All NEEDS CLARIFICATION resolved ✅ (user provided route organization strategy)
- [x] Complexity deviations documented ✅ (none - all principles satisfied)

**Artifacts Generated**:

- [x] plan.md (this file)
- [x] research.md (6 decisions documented)
- [x] data-model.md (domain models, policies, state transitions)
- [x] contracts/ (openapi-tenant-context.yaml - 3 endpoints)
- [x] quickstart.md (8 test scenarios)
- [x] .github/copilot-instructions.md (updated with tenant security context)
- [x] tasks.md (61 ordered implementation tasks)

---
*Based on Constitution v1.5.1 - See `/.specify/memory/constitution.md`*
