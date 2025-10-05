# Feature Specification: Phase 3 — Data Model Persistence

**Feature Branch**: `003-fill-the-specs`  
**Created**: 2025-10-04  
**Status**: Draft  
**Input**: User description: "reuse all the specs developed in /Users/sujoymukherjee/code/githubspeckit/specs/001-modern-enterprise-grade to create the persistence layer"

## Purpose

Implement a persistence layer that maps the canonical Phase 1 data model to durable storage, provides a test-friendly in-memory adapter, and an operational SQL adapter (PostgreSQL) with deterministic migrations and adapter test harnesses so contract and integration tests can run reliably across environments.

## Reused Artifacts (source of truth)

- Canonical data model: /Users/sujoymukherjee/code/githubspeckit/specs/001-modern-enterprise-grade/data-model.md
- Contract tests and OpenAPI fragments: /Users/sujoymukherjee/code/githubspeckit/specs/001-modern-enterprise-grade/contracts/
- Quickstart and example flows: /Users/sujoymukherjee/code/githubspeckit/specs/001-modern-enterprise-grade/quickstart.md

All persistence mappings, constraints and indexes MUST follow the definitions in the canonical `data-model.md`. Any deviation requires an explicit data-model change in that directory and a cross-team sign-off.

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a developer, I want repository adapters so I can run contract tests and integration scenarios against in-memory and SQL-backed stores, ensuring behavior parity and deterministic test outcomes.

### Acceptance Scenarios

1. **Given** the canonical `data-model.md`, **When** the SQL adapter is initialized in a clean environment, **Then** the required tables, indexes, and constraints are present and migrations are idempotent.
2. **Given** a running contract test suite that targets repository interfaces, **When** tests run with the in-memory adapter and then the SQL adapter, **Then** the same contract tests should pass for semantic equivalence (within documented adapter caveats).
3. **Given** a tenant-scoped query, **When** executed, **Then** results must only include rows belonging to the tenant context and never leak cross-tenant data.

### Edge Cases

- Concurrent updates to the same entity: behavior must be defined (see Clarifications).  
- Partial failures during multi-step operations must roll back SQL transactions and surface structured audit/log events.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-301**: Provide a repository abstraction per domain aggregate exposing async CRUD operations, returning domain models (no ORM model objects in domain layer).
- **FR-302**: Provide two adapters for Phase 3: in-memory (for fast tests) and SQL/PostgreSQL (for integration/staging).
- **FR-303**: Support deterministic, idempotent schema migrations for the SQL adapter (Alembic or equivalent), runnable in CI and local dev.
- **FR-304**: Enforce tenant-scoped visibility for all queries; tenant context must be required and validated at repository entry points.
- **FR-305**: Provide transactional semantics with rollback for multi-step domain operations when using the SQL adapter.
- **FR-306**: Supply a deterministic seed mechanism for dev/test data (TestTenant, sample users, policies) with idempotent behavior.
- **FR-307**: Provide adapter fixtures and a test harness enabling the same contract test suite (from `/specs/001-modern-enterprise-grade/contracts/`) to run against both adapters.
- **FR-309**: Implement an async SQL adapter (SQLAlchemy 2.x async or equivalent) that maps exactly to the canonical data-model entities, including indexes and unique constraints.
- **FR-310**: Provide Alembic migration scripts (or deterministic DDL generation) tracked in source under `alembic/versions/` and callable via a `make migrate` dev task.
- **FR-311**: Add adapter integration tests that run the repository contract test set against both adapters; tests must be failing prior to implementation (TDD).
- **FR-312**: Document per-entity mapping notes (field→column, index, tenant scope) in `src/adapters/persistence/README.md`.

### Non-Functional Requirements

- **NFR-321**: Repository operations should aim for p95 < 200ms in local integration tests for standard CRUD patterns (monitor and document deviations).
- **NFR-322**: Migrations and seed operations must be idempotent and complete within a few seconds for dev datasets.
- **NFR-323**: Observability: Each adapter must emit metrics for operation latency, errors, and transaction rollbacks; tracing spans must be created at adapter boundaries.

## Key Entities (derived from canonical data-model)

- Reuse entities defined in `/Users/sujoymukherjee/code/githubspeckit/specs/001-modern-enterprise-grade/data-model.md` (Tenant, User, AuditEvent, Policy, etc.).

## Clarifications

### Session 1 (2025-10-04)

- Q: Conflict resolution strategy for concurrent writes → A: [NEEDS ANSWER]

This answer affects schema design (version columns), transaction isolation guidance, and contract test expectations.

## Implementation Notes (phase 3 scope)

- Create `src/adapters/persistence/` with:
  - `inmemory_adapter.py` — in-memory, concurrency-safe implementation (async-friendly).
  - `sqlalchemy_adapter.py` — SQLAlchemy async adapter mapping to canonical models.
  - `__init__.py` and a small adapter factory to select adapter by config.
- Add Alembic migration scripts under `alembic/versions/` matching the canonical model.
- Add adapter test fixtures under `tests/contract/adapters/` that run the contract test suite against each adapter.
- Add `src/adapters/persistence/README.md` documenting mapping and tenant scoping rules.

## Review & Acceptance Checklist

- [ ] Implementation exists for in-memory adapter and SQL adapter.
- [ ] Alembic migrations present and idempotent in CI.
- [ ] Adapter contract tests pass against both adapters.
- [ ] Documentation under `src/adapters/persistence/README.md` completed.

---

**Version**: draft | **Branch**: 003-fill-the-specs

# Feature Specification: Phase 3 — Data Model Persistence

**Feature Branch**: `003-fill-the-specs`  
**Created**: 2025-10-04  
**Status**: Draft  
**Input**: User description: "fill the specs for phase 3 - data model persistence"

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

- Focus on WHAT data persistence responsibilities must exist for Phase 3 and WHY (not implementation how).
- Mark ambiguities explicitly with [NEEDS CLARIFICATION: ...].

---

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

[Describe the main user journey in plain language]

### Acceptance Scenarios

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

### Edge Cases

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

---

## Review & Acceptance Checklist

GATE: Automated checks run during main() execution*

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

Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---
