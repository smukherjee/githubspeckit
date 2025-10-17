# Tasks: Admin API Endpoints for Multi-Tenant Backend# Tasks: Admin API Endpoints for Multi-Tenant Backend



**Input**: Design documents from `/specs/002-react-admin-frontend/`  **Input**: Design documents from `/specs/002-react-admin-frontend/`

**Prerequisites**: plan.md, research.md, data-model.md, contracts/openapi-admin.yaml, quickstart.md**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/openapi-admin.yaml, quickstart.md



## Execution Flow## Execution Flow (main)



```text```text

1. Tech stack: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic1. Load plan.md from feature directory

2. Structure: Single backend API (hexagonal architecture)   → Tech stack: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic

3. Entities: 6 (User, Tenant, Policy, FeatureFlag, Invitation, AuditEvent)   → Structure: Single backend API (hexagonal architecture)

4. Endpoints: 22 admin API endpoints across 6 resource types2. Load design documents:

5. Test scenarios: 7 integration scenarios + performance validation   → data-model.md: 6 entities (User, Tenant, Policy, FeatureFlag, Invitation, AuditEvent)

6. Tasks: 63 tasks across setup → tests → implementation → polish   → contracts/openapi-admin.yaml: 22 endpoints across 6 resource types

7. TDD ordering: All tests before implementation   → quickstart.md: 7 integration test scenarios with performance validation

```3. Generate tasks by category:

   → Setup: project structure, dependencies, linting

## Task Format   → Tests: contract tests (22), integration tests (7 scenarios)

   → Core: Pydantic schemas, FastAPI handlers, service layer

- **[P]**: Can run in parallel (different files, no dependencies)   → Integration: RBAC policies, tenant filtering, bulk operations

- All paths relative to repository root   → Polish: unit tests, performance validation, documentation

4. Apply task rules:

## Phase 3.1: Setup   → Different files = mark [P] for parallel

   → Same file/endpoint = sequential (no [P])

- [ ] T001 Create admin API structure in `src/adapters/api/admin/` directory   → Tests before implementation (TDD)

- [ ] T002 Create admin schemas structure in `src/schemas/admin/` directory  5. Number tasks sequentially (T001, T002...)

- [ ] T003 [P] Create contract test directory `tests/contract/admin/`6. Generate dependency graph with parallel execution examples

- [ ] T004 [P] Configure pytest-asyncio for async testing in `pytest.ini````



## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3## Task Format



CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation- **[P]**: Can run in parallel (different files, no dependencies)

- Include exact file paths in descriptions

### Contract Tests (API Shape Validation)- All paths relative to repository root



- [ ] T005 [P] Contract test GET/POST /api/v1/admin/tenants in `tests/contract/admin/test_tenants_contract.py`## Phase 3.1: Setup

- [ ] T006 [P] Contract test GET/POST/PUT/DEL /api/v1/admin/users in `tests/contract/admin/test_users_contract.py`

- [ ] T007 [P] Contract test GET/POST /api/v1/admin/policies in `tests/contract/admin/test_policies_contract.py`- [ ] T001 Create admin API structure in `src/adapters/api/admin/` directory

- [ ] T008 [P] Contract test GET/POST /api/v1/admin/feature-flags in `tests/contract/admin/test_feature_flags_contract.py`- [ ] T002 Create admin schemas structure in `src/schemas/admin/` directory  

- [ ] T009 [P] Contract test GET/POST /api/v1/admin/invitations in `tests/contract/admin/test_invitations_contract.py`- [ ] T003 [P] Create contract test directory `tests/contract/admin/`

- [ ] T010 [P] Contract test GET /api/v1/admin/audit-events in `tests/contract/admin/test_audit_events_contract.py`- [ ] T004 [P] Configure pytest-asyncio for async testing in `pytest.ini`

- [ ] T011 [P] Contract test POST /api/v1/admin/users/bulk/export in `tests/contract/admin/test_bulk_operations_contract.py`

- [ ] T012 [P] Contract test POST /api/v1/admin/users/bulk/import in `tests/contract/admin/test_bulk_operations_contract.py`## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3



### Integration Tests (End-to-End Scenarios)CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation



- [ ] T013 [P] Integration test Scenario 1: Superadmin cross-tenant management in `tests/integration/test_superadmin_scenarios.py`### Contract Tests (API Shape Validation)

- [ ] T014 [P] Integration test Scenario 2: Tenant admin user management in `tests/integration/test_tenant_admin_scenarios.py`- [ ] T005 [P] Contract test GET/POST /api/v1/admin/tenants in `tests/contract/admin/test_tenants_contract.py`

- [ ] T015 [P] Integration test Scenario 3: RBAC policy management in `tests/integration/test_rbac_scenarios.py`- [ ] T006 [P] Contract test GET/POST/PUT/DEL /api/v1/admin/users in `tests/contract/admin/test_users_contract.py`

- [ ] T016 [P] Integration test Scenario 4: Feature flag management in `tests/integration/test_feature_flag_scenarios.py`- [ ] T007 [P] Contract test GET/POST /api/v1/admin/policies in `tests/contract/admin/test_policies_contract.py`

- [ ] T017 [P] Integration test Scenario 5: User invitation flow in `tests/integration/test_invitation_scenarios.py`- [ ] T008 [P] Contract test GET/POST /api/v1/admin/feature-flags in `tests/contract/admin/test_feature_flags_contract.py`

- [ ] T018 [P] Integration test Scenario 6: Audit trail verification in `tests/integration/test_audit_scenarios.py`- [ ] T009 [P] Contract test GET/POST /api/v1/admin/invitations in `tests/contract/admin/test_invitations_contract.py`

- [ ] T019 [P] Integration test Scenario 7: Bulk operations in `tests/integration/test_bulk_operations_scenarios.py`- [ ] T010 [P] Contract test GET /api/v1/admin/audit-events in `tests/contract/admin/test_audit_events_contract.py`

- [ ] T011 [P] Contract test POST /api/v1/admin/users/bulk/export in `tests/contract/admin/test_bulk_operations_contract.py`

### RBAC & Tenant Isolation Tests- [ ] T012 [P] Contract test POST /api/v1/admin/users/bulk/import in `tests/contract/admin/test_bulk_operations_contract.py`



- [ ] T020 [P] RBAC boundary test: Cross-tenant access prevention in `tests/integration/test_tenant_isolation.py`### Integration Tests (End-to-End Scenarios)

- [ ] T021 [P] RBAC boundary test: Role-based endpoint access in `tests/integration/test_rbac_enforcement.py`- [ ] T013 [P] Integration test Scenario 1: Superadmin cross-tenant management in `tests/integration/test_superadmin_scenarios.py`

- [ ] T022 [P] Performance test: Response time validation (<200ms p95) in `tests/performance/test_admin_api_performance.py`- [ ] T014 [P] Integration test Scenario 2: Tenant admin user management in `tests/integration/test_tenant_admin_scenarios.py`

- [ ] T015 [P] Integration test Scenario 3: RBAC policy management in `tests/integration/test_rbac_scenarios.py`

## Phase 3.3: Core Implementation (ONLY after tests are failing)- [ ] T016 [P] Integration test Scenario 4: Feature flag management in `tests/integration/test_feature_flag_scenarios.py`

- [ ] T017 [P] Integration test Scenario 5: User invitation flow in `tests/integration/test_invitation_scenarios.py`

### Pydantic Response/Request Schemas- [ ] T018 [P] Integration test Scenario 6: Audit trail verification in `tests/integration/test_audit_scenarios.py`

- [ ] T019 [P] Integration test Scenario 7: Bulk operations in `tests/integration/test_bulk_operations_scenarios.py`

- [ ] T023 [P] Admin tenant schemas in `src/schemas/admin/tenants.py`

- [ ] T024 [P] Admin user schemas in `src/schemas/admin/users.py`### RBAC & Tenant Isolation Tests

- [ ] T025 [P] Admin policy schemas in `src/schemas/admin/policies.py`- [ ] T020 [P] RBAC boundary test: Cross-tenant access prevention in `tests/integration/test_tenant_isolation.py`

- [ ] T026 [P] Admin feature flag schemas in `src/schemas/admin/feature_flags.py`- [ ] T021 [P] RBAC boundary test: Role-based endpoint access in `tests/integration/test_rbac_enforcement.py`

- [ ] T027 [P] Admin invitation schemas in `src/schemas/admin/invitations.py`- [ ] T022 [P] Performance test: Response time validation (<200ms p95) in `tests/performance/test_admin_api_performance.py`

- [ ] T028 [P] Admin audit event schemas in `src/schemas/admin/audit_events.py`

- [ ] T029 [P] Common admin schemas (ListResponse, ErrorResponse, etc.) in `src/schemas/admin/common.py`## Phase 3.3: Core Implementation (ONLY after tests are failing)



### FastAPI Route Handlers### Pydantic Response/Request Schemas

- [ ] T023 [P] Admin tenant schemas in `src/schemas/admin/tenants.py`

- [ ] T030 [P] Tenant CRUD endpoints in `src/adapters/api/admin/tenants.py`- [ ] T024 [P] Admin user schemas in `src/schemas/admin/users.py`

- [ ] T031 User CRUD endpoints in `src/adapters/api/admin/users.py` (sequential - shared user logic)- [ ] T025 [P] Admin policy schemas in `src/schemas/admin/policies.py`

- [ ] T032 [P] Policy CRUD endpoints in `src/adapters/api/admin/policies.py`- [ ] T026 [P] Admin feature flag schemas in `src/schemas/admin/feature_flags.py`

- [ ] T033 [P] Feature flag CRUD endpoints in `src/adapters/api/admin/feature_flags.py`- [ ] T027 [P] Admin invitation schemas in `src/schemas/admin/invitations.py`

- [ ] T034 [P] Invitation CRUD endpoints in `src/adapters/api/admin/invitations.py`- [ ] T028 [P] Admin audit event schemas in `src/schemas/admin/audit_events.py`

- [ ] T035 [P] Audit event query endpoints in `src/adapters/api/admin/audit_events.py`- [ ] T029 [P] Common admin schemas (ListResponse, ErrorResponse, etc.) in `src/schemas/admin/common.py`

- [ ] T036 Bulk operations endpoints (CSV import/export) in `src/adapters/api/admin/bulk_operations.py`

### FastAPI Route Handlers

### Admin Router Integration- [ ] T030 [P] Tenant CRUD endpoints in `src/adapters/api/admin/tenants.py`

- [x] T031 User CRUD endpoints in `src/adapters/api/routers/users.py` - ✅ COMPLETE
  - [x] GET /api/v1/users - List users (tenant-scoped)
  - [x] POST /api/v1/users - Create user
  - [x] GET /api/v1/users/{user_id} - Get user details
  - [x] PUT /api/v1/users/{user_id} - Update user (email, roles, status) - ✅ IMPLEMENTED
  - [x] DELETE /api/v1/users/{user_id} - Soft delete user (set status=disabled)
  - [x] POST /api/v1/users/{user_id}/restore - Restore disabled user
  - [x] POST /api/v1/users/{user_id}/reset-password - Admin password reset
  - Note: Extended profile fields (full_name, job_title, department, phone, timezone, language) 
    managed via /api/v1/users/{user_id}/profile endpoint (feature 003-user-profile-details)
  - RBAC: Users update own email; Tenant admins update tenant users; Superadmins update all
  - Audit logging: user.create, user.update, user.disable, user.restore, user.password_reset

- [ ] T037 Admin API router setup in `src/adapters/api/admin/__init__.py`- [ ] T032 [P] Policy CRUD endpoints in `src/adapters/api/admin/policies.py`

- [ ] T038 Mount admin router in main FastAPI app in `src/adapters/api/app.py`- [ ] T033 [P] Feature flag CRUD endpoints in `src/adapters/api/admin/feature_flags.py`

- [ ] T034 [P] Invitation CRUD endpoints in `src/adapters/api/admin/invitations.py`

## Phase 3.4: Integration & Security- [ ] T035 [P] Audit event query endpoints in `src/adapters/api/admin/audit_events.py`

- [ ] T036 Bulk operations endpoints (CSV import/export) in `src/adapters/api/admin/bulk_operations.py`

### RBAC Integration

### Admin Router Integration

- [ ] T039 Register admin resource policies with auth_core in `src/auth_core/admin_policies.py`- [ ] T037 Admin API router setup in `src/adapters/api/admin/__init__.py`

- [ ] T040 Tenant filtering middleware for admin endpoints in `src/adapters/api/admin/middleware.py`- [ ] T038 Mount admin router in main FastAPI app in `src/adapters/api/app.py`

- [ ] T041 Superadmin cross-tenant access validation in admin handlers

- **Total Tasks**: 64

### Input Validation & Error Handling- **Estimated Effort**: 70-90 hours (3-4 weeks solo, 1.5 weeks team of 3)

- **Parallel Tasks**: 35 tasks marked [P] (can run simultaneously)

- [ ] T042 Admin request validation with detailed error responses- **Critical Path**: T001-T005 (setup) → T006-T020 (tests) → T021-T055 (implementation) → T056-T064 (polish)

- [ ] T043 Admin endpoint error handling with structured responses

- [ ] T044 Admin audit logging for all operations## Format: `[ID] [P?] Description`



### Bulk Operations Implementation- **[P]**: Can run in parallel (different files, no dependencies)

- **File paths**: Relative to `githubspeckit-frontend/` repository root

- [ ] T045 CSV export service with tenant filtering in `src/services/admin/export_service.py`

- [ ] T046 CSV import service with validation and dry-run in `src/services/admin/import_service.py`---

- [ ] T047 File upload handling and security validation

## Phase 3.1: Repository & Project Setup ✅ COMPLETE

## Phase 3.5: Polish & Documentation

**Objective**: Initialize separate frontend repository with Vite + React + TypeScript + React-admin

### Unit Tests

