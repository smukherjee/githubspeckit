
# Implementation Plan: Admin API Endpoints for Multi-Tenant Backend

**Branch**: `002-react-admin-frontend` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-react-admin-frontend/spec.md`

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

Comprehensive backend API endpoints for administrative operations in the multi-tenant system. The APIs are frontend-agnostic and designed to support any client framework through well-defined REST contracts. Endpoints enable role-based operations (superadmin, tenant_admin, standard) across tenants, users, feature flags, policies, invitations, and audit logs with proper RBAC enforcement and tenant isolation.

**User Input Context**: This project is backend-only with FastAPI and should be frontend agnostic, following constitutional principles of hexagonal architecture.

## Technical Context
**Language/Version**: Python 3.13  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic  
**Storage**: PostgreSQL (primary), Redis (caching)  
**Testing**: pytest, httpx (async client)  
**Target Platform**: Linux server, Docker containers  
**Project Type**: Single backend API (hexagonal architecture)  
**Performance Goals**: p95 <200ms CRUD operations, p99 <500ms bulk operations  
**Constraints**: Multi-tenant isolation, RBAC enforcement, audit logging  
**Scale/Scope**: Support multiple frontend clients, 6 resource types, 3 user roles

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluate and explicitly confirm (checklist) before proceeding:

1. ✅ **Architecture**: Admin API endpoints implemented as FastAPI adapters, domain logic in pure Python models and services (Principle I).
2. ✅ **Test-First & Coverage**: Contract tests for each endpoint, domain logic tests, RBAC tests, tenant isolation tests planned (Principle II).
3. ✅ **Multi-Tenancy**: All data access paths include explicit tenant_id filtering, superadmin cross-tenant access properly controlled (Principles I & III).
4. ✅ **RBAC & Policies**: Authorization via policy engine registration, no inline role checks in FastAPI handlers (Principles III & VI).
5. ✅ **Auth Reuse**: Admin endpoints register with existing auth_core package, no domain-specific auth logic (Principle VI).
6. ✅ **Switchable Persistence**: Admin operations use existing repository interfaces, no direct ORM access (Principle IV).
7. ✅ **Observability**: Admin endpoints emit structured logs, metrics for CRUD operations, tracing spans (Principle V).
8. ✅ **API Versioning**: All endpoints under /api/v1, OpenAPI contract generation, backward compatibility (Principle V).
9. ✅ **Performance Budgets**: p95 <200ms CRUD, p99 <500ms bulk operations (Principle V).
10. ✅ **Unified Configuration**: Admin endpoints respect DEPLOY_MODE, no direct env access (Principle VII).
11. ✅ **Developer Experience & Embed**: APIs support iframe embedding via CORS/cookie config (Principle VIII).
12. ✅ **Complexity**: Reuses existing domain models, services, and auth - no new infrastructure (Governance & Principle IV).
13. ✅ **Security Testing**: RBAC boundary tests, tenant isolation tests, input validation tests (Additional Constraints & Principle V).
14. ✅ **Code Quality & Simplicity**: Follows existing patterns, no duplication of CRUD logic (Principle IX).

**Status**: PASS - All constitutional requirements satisfied

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
├── domain/                    # Pure business logic (existing)
│   ├── tenants/              # Tenant domain models and services
│   ├── users/                # User domain models and services  
│   ├── authz/                # Authorization domain logic
│   ├── audit/                # Audit event domain logic
│   └── config/               # Configuration domain logic
├── adapters/                 # Infrastructure adapters (existing)
│   ├── api/                  # FastAPI HTTP adapters
│   │   ├── admin/            # NEW: Admin endpoint handlers
│   │   │   ├── tenants.py   # Tenant CRUD endpoints
│   │   │   ├── users.py     # User CRUD endpoints
│   │   │   ├── policies.py  # Policy CRUD endpoints
│   │   │   ├── feature_flags.py # Feature flag endpoints
│   │   │   ├── invitations.py # Invitation endpoints
│   │   │   └── audit.py     # Audit log endpoints
│   │   └── __init__.py
│   ├── persistence/          # Database adapters (existing)
│   └── observability/        # Logging, metrics, tracing (existing)
├── auth_core/                # Reusable auth package (existing)
└── schemas/                  # Pydantic models (existing + new admin schemas)
    └── admin/                # NEW: Admin-specific request/response schemas

tests/
├── contract/                 # NEW: API contract tests for admin endpoints
│   ├── test_admin_tenants.py
│   ├── test_admin_users.py
│   ├── test_admin_policies.py
│   ├── test_admin_feature_flags.py
│   ├── test_admin_invitations.py
│   └── test_admin_audit.py
├── integration/              # Integration tests (existing + new admin tests)
└── unit/                     # Unit tests (existing domain tests)

contracts/                    # OpenAPI contract fragments (repository root)
├── openapi-admin.yaml       # NEW: Admin endpoints OpenAPI spec
└── [existing contract files]
```

**Structure Decision**: Single backend project with hexagonal architecture. New admin endpoints added as FastAPI adapters that reuse existing domain models, services, and auth_core package. No frontend code in this repository - APIs are frontend-agnostic and consumable by any client framework.

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

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS  
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.5.1 - See `/memory/constitution.md`*
