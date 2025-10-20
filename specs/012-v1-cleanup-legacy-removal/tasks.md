# Tasks: V1.0 Release - Legacy Code Removal & Cleanup

**Input**: Design documents from `/specs/012-v1-cleanup-legacy-removal/`
**Prerequisites**: plan.md, research.md, data-model.md, quickstart.md

## Feature Summary

Remove all backward compatibility code, unify admin routes under `/api/v1/admin/*`, enforce per-tenant email uniqueness, and establish V1.0 as clean baseline with complete dev environment automation.

**Timeline**: 8 days (Pre-Phase 0: 1 day, Implementation: 7 days)
**Total Tasks**: 65 tasks across 10 categories

---

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Pre-Phase 0: Database Audit & Tooling Setup (Day 1)

- [x] T001 Create database audit orchestration script `scripts/db_audit.sh` to execute orphan tables, missing indexes, and sensitive column checks
- [x] T002 [P] Implement orphaned tables detector `scripts/detect_orphaned_tables.py` using SQLAlchemy reflection to find tables not in ORM models
- [x] T003 [P] Implement missing indexes analyzer `scripts/analyze_missing_indexes.py` scanning for columns without indexes in WHERE/JOIN clauses (via query logs or static analysis)
- [x] T004 [P] Implement sensitive column checker `scripts/check_sensitive_columns.py` detecting unencrypted PII columns (email, phone, SSN patterns)
- [x] T005 Add GitHub Actions workflow `.github/workflows/db-audit.yml` with cron schedule (Monday 9 AM UTC) running db_audit.sh and posting results as workflow artifact
- [x] T006 Download SchemaSpy JAR file `tools/schemaspy.jar` (v6.2.4+) and create wrapper script `scripts/generate_erd.sh` with PostgreSQL JDBC driver configuration
- [x] T007 [P] Create SQLFluff configuration `.sqlfluff` with PostgreSQL dialect, line length 100, and pre-commit hook integration in `.pre-commit-config.yaml`

---

## Phase 3.1: Remove Deprecated Code (Days 2-3)

- [x] T008 [P] Delete deprecation middleware file `src/adapters/api/deprecation.py`
- [x] T009 [P] Delete deprecation warning middleware `src/adapters/api/middleware/deprecation_warning.py`
- [x] T010 Remove deprecation middleware registration from `src/adapters/api/app.py` (search for `DeprecationMiddleware` or `DeprecationWarningMiddleware` imports and `add_middleware` calls)
- [x] T011 [P] Remove deprecated query parameter handling from `src/adapters/api/routers/tenants/crud.py` (search for `tenant_id` query param extraction) - NOT FOUND, already clean
- [x] T012 [P] Remove deprecated query parameter handling from `src/adapters/api/routers/users.py` (search for `tenant_id` query param extraction) - NOT FOUND, already clean
- [x] T013 [P] Remove Sunset header logic from response middleware in `src/adapters/api/middleware/` (if exists, search for `Sunset` or `X-API-Deprecation` header setting) - NOT FOUND, already clean
- [x] T014 [P] Remove backward compatibility branches in `src/adapters/storage/` or `src/adapters/media/` (search for `# Backward compat` or `if legacy_mode` patterns) - NOT FOUND, already clean
- [x] T015 [P] Delete all legacy test files matching pattern `tests/**/test_deprecated_*.py` and `tests/**/test_legacy_*.py` - NOT FOUND, already clean
- [x] T016 Run grep audit for "deprecated" comments: `grep -r "deprecated" src/ tests/ --exclude-dir=__pycache__` and remove stale comments or code blocks

---

## Phase 3.2: Database Schema & Migration (Day 3)

- [ ] T017 Create Alembic migration `alembic/versions/XXXX_drop_global_email_unique.py` to drop `users_email_key` unique constraint (use `op.drop_constraint('users_email_key', 'users', type_='unique')`)
- [ ] T018 Create Alembic migration `alembic/versions/YYYY_add_per_tenant_email_unique.py` to add composite unique index `idx_users_email_tenant` on `(email, tenant_id)` (use `op.create_index(..., unique=True)`)
- [ ] T019 Create Alembic migration `alembic/versions/ZZZZ_add_schema_version_table.py` to create `schema_version` metadata table with columns: `version VARCHAR(20) PK`, `applied_at TIMESTAMP`, `description TEXT`, `checksum VARCHAR(64)`
- [ ] T020 Implement pre-migration validation script `scripts/validate_email_migration.py` to query duplicate (email, tenant_id) pairs and fail with clear error if conflicts detected
- [ ] T021 Test migration upgrade/downgrade cycle: run `alembic upgrade head`, then `alembic downgrade -1`, verify no data corruption and index correctly recreated

---

## Phase 3.3: Tests First - Contract Tests for New Routes (Day 3) ⚠️ MUST COMPLETE BEFORE IMPLEMENTATION

CRITICAL: These tests MUST be written and MUST FAIL before ANY router implementation

- [ ] T022 [P] Contract test GET /api/v1/admin/tenants in `tests/contract/test_v1_admin_tenants.py` (expect 401 without auth, 200 with superadmin token)
- [ ] T023 [P] Contract test POST /api/v1/admin/tenants in `tests/contract/test_v1_admin_tenants.py` (expect 403 for non-superadmin)
- [ ] T024 [P] Contract test GET /api/v1/admin/users in `tests/contract/test_v1_admin_users.py` (expect 401 without auth, 200 with admin token)
- [ ] T025 [P] Contract test POST /api/v1/admin/users with duplicate email same tenant in `tests/contract/test_v1_admin_users.py` (expect 409 with code EMAIL_ALREADY_EXISTS)
- [ ] T026 [P] Contract test POST /api/v1/admin/users with duplicate email different tenant in `tests/contract/test_v1_admin_users.py` (expect 201 success)
- [ ] T027 [P] Contract test GET /api/v1/admin/policies in `tests/contract/test_v1_admin_policies.py` (expect 401 without auth, 200 with admin token)
- [ ] T028 [P] Contract test GET /api/v1/admin/roles in `tests/contract/test_v1_admin_roles.py` (expect 401 without auth, 200 with admin token)
- [ ] T029 [P] Contract test deprecated route GET /api/v1/tenants in `tests/contract/test_legacy_routes_removed.py` (expect 404 Not Found)
- [ ] T030 [P] Contract test deprecated route GET /api/v1/users in `tests/contract/test_legacy_routes_removed.py` (expect 404 Not Found)

---

## Phase 3.4: Router Prefix Updates (Days 3-4) (ONLY after T022-T030 are failing)

- [ ] T031 Update tenants router `src/adapters/api/routers/tenants/crud.py` include in `app.py` to use prefix `/api/v1/admin` instead of `/api/v1/tenants`
- [ ] T032 Update users router `src/adapters/api/routers/users.py` include in `app.py` to use prefix `/api/v1/admin` instead of `/api/v1/users`
- [ ] T033 Update policies router `src/adapters/api/routers/policies.py` include in `app.py` to use prefix `/api/v1/admin` instead of `/api/v1/policies`
- [ ] T034 Update roles router `src/adapters/api/routers/roles.py` include in `app.py` to use prefix `/api/v1/admin` instead of `/api/v1/roles` (if separate router exists)
- [ ] T035 Update OpenAPI tags for admin routers in `app.py` router includes (e.g., `tags=["admin-tenants"]`, `tags=["admin-users"]`)
- [ ] T036 [P] Update integration tests in `tests/integration/tenant_security/` to use new `/api/v1/admin/*` route paths
- [ ] T037 [P] Update unit tests with hardcoded route references (search for `/api/v1/tenants`, `/api/v1/users` strings in tests/)
- [ ] T038 Add explicit 404 test in `tests/contract/test_legacy_routes_removed.py` verifying GET /api/v1/tenants returns 404
- [ ] T039 Run full contract test suite `pytest tests/contract/ -v` and ensure all T022-T030 tests now pass

---

## Phase 3.5: Email Uniqueness Enforcement (Day 4)

- [ ] T040 Add method `get_by_email_and_tenant(email: str, tenant_id: UUID)` to `src/adapters/persistence/user_repository.py` using case-insensitive query (`func.lower(UserModel.email) == email.lower()`)
- [ ] T041 Update `create_user` method in `src/services/user_service.py` to call `get_by_email_and_tenant` and raise `DomainError(code="EMAIL_ALREADY_EXISTS")` if user exists
- [ ] T042 Update error message in domain error to: "Email '{email}' is already registered in this tenant"
- [ ] T043 [P] Add unit test in `tests/unit/test_user_service.py` for same email cross-tenant allowed scenario (mock repository, verify no exception)
- [ ] T044 [P] Add unit test in `tests/unit/test_user_service.py` for same email same tenant rejected scenario (mock repository, verify DomainError raised)
- [ ] T045 Run contract tests T025-T026 to verify API-level email uniqueness enforcement (expect both to pass)

---

## Phase 3.6: Rate Limiting Implementation (Day 5)

- [ ] T046 Research and select rate limiting library: evaluate `slowapi` vs `fastapi-limiter` (decision: use slowapi per research.md)
- [ ] T047 Add `slowapi` and `redis` dependencies to `requirements.txt` (slowapi>=0.1.8, redis>=4.5.0)
- [ ] T048 Add `RATE_LIMIT_USER_CREATION` config to `config/descriptor.toml` with type=int, default=100, description="Max user creation attempts per hour per IP"
- [ ] T049 Create rate limiting middleware in `src/adapters/security/rate_limit.py` with slowapi Limiter, Redis backend, and `get_remote_address` key function
- [ ] T050 Integrate rate limiter in `src/adapters/api/app.py` (add `app.state.limiter`, register exception handler for `RateLimitExceeded`)
- [ ] T051 Apply rate limiter decorator to POST /api/v1/admin/users endpoint in `src/adapters/api/routers/users.py` with dynamic limit from config
- [ ] T052 Implement admin bypass mechanism: add `exempt_when=is_superadmin` to rate limiter decorator (check RBAC role in dependency)
- [ ] T053 [P] Add security test in `tests/contract/test_rate_limiting.py` verifying 429 response after threshold exceeded (set RATE_LIMIT_USER_CREATION=5 for test)
- [ ] T054 [P] Add security test in `tests/contract/test_rate_limiting.py` verifying superadmin bypass (create 10 users as superadmin, expect all 201)

---

## Phase 3.7: OpenAPI V1.0 Generation (Day 5)

- [ ] T055 Consolidate existing contract fragments (`contracts/openapi-base.yaml`, `contracts/openapi-auth-policy.yaml`, `contracts/openapi-observability.yaml`) into single `contracts/openapi-v1.0.yaml`
- [ ] T056 Update OpenAPI info block in `contracts/openapi-v1.0.yaml`: set version=1.0.0, add breaking changes description, add license=MIT
- [ ] T057 Remove deprecated endpoints from `contracts/openapi-v1.0.yaml` (if any lingering references to old flat routes)
- [ ] T058 Add rate limiting documentation to OpenAPI spec: `x-rate-limit` extension on POST /api/v1/admin/users with threshold and window details
- [ ] T059 [P] Generate schemathesis contract tests in `tests/contract/test_openapi_v1_compliance.py` using `schemathesis.from_uri("http://localhost:8000/openapi.json")`

---

## Phase 3.8: Documentation & Migration Guide (Day 6)

- [ ] T060 Create `docs/CHANGELOG-V1.0.md` with breaking changes list (deprecation middleware removed, admin route prefix changes, per-tenant email uniqueness, rate limiting added)
- [ ] T061 Create `docs/MIGRATION-TO-V1.0.md` with step-by-step upgrade instructions (backup DB, run migrations, update API clients, test, rollback procedure)
- [ ] T062 Update `README.md`: add V1.0 release notes section, reference new quick start, add Docker Compose instructions
- [ ] T063 Export database schema `docs/database-schema-v1.0.sql` via `pg_dump --schema-only -U postgres infysight_users > docs/database-schema-v1.0.sql`
- [ ] T064 Generate ERD `docs/database-erd-v1.0.png` via SchemaSpy: `scripts/generate_erd.sh` (output HTML + PNG diagrams)
- [ ] T065 Create `docs/database-indexes-v1.0.md` documenting all indexes with rationale (e.g., idx_users_email_tenant for per-tenant email uniqueness + login performance)

---

## Phase 3.9: Dev Environment Setup (Day 7)

- [ ] T066 Create `docker-compose.yml` with 4 services: postgres:15-alpine (port 5432), redis:7-alpine (port 6379), dpage/pgadmin4 (port 5050), api (port 8000, build from Dockerfile)
- [ ] T067 Create `Dockerfile` for API container with Python 3.13-slim base, install dependencies from requirements.txt, expose port 8000, volume mount `src/` for hot reload
- [ ] T068 Add Makefile targets `docker-up` (docker-compose up -d), `docker-down` (docker-compose down), `docker-logs` (docker-compose logs -f api), `docker-reset` (docker-compose down -v && docker-compose up --build -d)
- [ ] T069 Create `.env.example` with all required environment variables (DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, RATE_LIMIT_USER_CREATION, LOG_LEVEL)
- [ ] T070 Update `README.md` with Docker Compose quick start section (prerequisites: Docker + Docker Compose installed, commands: make docker-up, verify health)
- [ ] T071 Create `CONTRIBUTING.md` with dev workflow documentation (branch naming, commit conventions, test requirements, PR process, code review checklist)
- [ ] T072 Test native `make bootstrap` on clean macOS environment (verify <5 minute setup, no errors)
- [ ] T073 Test Docker `make docker-up` on clean Linux environment (verify all 4 services healthy, API accessible, pgAdmin web UI works)

---

## Phase 3.10: Observability Updates (Day 7)

- [ ] T074 Add version metadata (v1.0.0) to audit event schema in `src/adapters/logging/audit_logger.py` (add `version` field to event payload)
- [ ] T075 [P] Update metrics dashboard documentation in `docs/observability/metrics-dashboards.md` with new route patterns (replace `/api/v1/tenants` with `/api/v1/admin/tenants` in Grafana queries)
- [ ] T076 [P] Update log aggregation documentation in `docs/observability/log-queries.md` with new route patterns (update Elasticsearch/Kibana queries for admin routes)

---

## Phase 3.11: Testing & Validation (Day 8)

- [ ] T077 Run full test suite `pytest tests/ -v --cov --cov-report=html` and ensure 100% pass rate with coverage ≥85% overall, ≥90% domain
- [ ] T078 Execute quickstart.md validation scenarios TS-001 through TS-013 end-to-end (health check, deprecated routes, auth, email uniqueness, rate limiting, OpenAPI, Docker)
- [ ] T079 Execute migration validation scenarios MV-001 and MV-002 (upgrade succeeds, downgrade works if no conflicts)
- [ ] T080 Run performance benchmarks `pytest tests/performance/ --benchmark-only` and verify <5% variance from baseline (p95 latency targets)
- [ ] T081 Execute security regression tests in `tests/security/` (RBAC enforcement, tenant isolation, rate limiting, no unauthorized access)
- [ ] T082 Validate OpenAPI spec against OpenAPI 3.1.0 schema using `openapi-spec-validator contracts/openapi-v1.0.yaml`

---

## Dependencies

**Sequential Chains**:
- Pre-Phase 0 (T001-T007) must complete before Phase 3.1
- T017-T019 (migrations) must complete before T040-T045 (email uniqueness logic)
- T022-T030 (contract tests) must complete and FAIL before T031-T039 (router implementation)
- T031-T039 (router updates) must complete before T036-T037 (test updates)
- T046-T054 (rate limiting) must complete before T078 (quickstart validation)
- T055-T059 (OpenAPI) must complete before T082 (spec validation)
- All implementation (T008-T076) must complete before testing & validation (T077-T082)

**Parallel Groups**:
- T002, T003, T004, T007 (independent scripts)
- T008, T009, T011, T012, T014, T015 (different file deletions)
- T022-T030 (independent contract test files)
- T036, T037 (integration vs unit test updates)
- T043, T044 (unit tests, different scenarios)
- T053, T054 (rate limiting tests, different scenarios)
- T075, T076 (documentation updates, different files)

---

## Parallel Execution Example

```bash
# Pre-Phase 0 tooling (T002-T004, T007 in parallel)
Task: "Implement orphaned tables detector scripts/detect_orphaned_tables.py"
Task: "Implement missing indexes analyzer scripts/analyze_missing_indexes.py"
Task: "Implement sensitive column checker scripts/check_sensitive_columns.py"
Task: "Create SQLFluff configuration .sqlfluff"

# Remove deprecated code (T008-T009, T011-T012, T014-T015 in parallel)
Task: "Delete deprecation middleware src/adapters/api/deprecation.py"
Task: "Delete deprecation warning middleware src/adapters/api/middleware/deprecation_warning.py"
Task: "Remove deprecated query param handling in routers/tenants/crud.py"
Task: "Remove deprecated query param handling in routers/users.py"
Task: "Remove backward compatibility branches in adapters/storage/"
Task: "Delete legacy test files test_deprecated_*.py"

# Contract tests (T022-T030 in parallel)
Task: "Contract test GET /api/v1/admin/tenants in tests/contract/test_v1_admin_tenants.py"
Task: "Contract test POST /api/v1/admin/tenants in tests/contract/test_v1_admin_tenants.py"
Task: "Contract test GET /api/v1/admin/users in tests/contract/test_v1_admin_users.py"
Task: "Contract test POST /api/v1/admin/users duplicate email same tenant in tests/contract/test_v1_admin_users.py"
Task: "Contract test POST /api/v1/admin/users duplicate email different tenant in tests/contract/test_v1_admin_users.py"
Task: "Contract test GET /api/v1/admin/policies in tests/contract/test_v1_admin_policies.py"
Task: "Contract test GET /api/v1/admin/roles in tests/contract/test_v1_admin_roles.py"
Task: "Contract test deprecated route GET /api/v1/tenants in tests/contract/test_legacy_routes_removed.py"
Task: "Contract test deprecated route GET /api/v1/users in tests/contract/test_legacy_routes_removed.py"
```

---

## Task Validation Checklist

GATE: Verified before execution

- [x] All contract endpoints have corresponding test tasks (T022-T030)
- [x] All entities modified have repository/service tasks (T040-T045 for User)
- [x] All tests written before implementation (T022-T030 before T031-T039)
- [x] Parallel tasks are truly independent (verified file paths)
- [x] Each task specifies exact file path or command
- [x] No task modifies same file as another [P] task
- [x] Database migrations before application logic (T017-T021 before T040-T045)
- [x] Documentation tasks at end (T060-T065 after implementation)
- [x] Validation tasks last (T077-T082 after all implementation)

---

## Notes

- **TDD Enforcement**: Contract tests T022-T030 must fail before router implementation T031-T039
- **Migration Testing**: Always test upgrade + downgrade in dev environment (T021)
- **Rate Limiting**: Lower `RATE_LIMIT_USER_CREATION` to 5 for easier testing (T053)
- **Docker vs Native**: Both workflows must work independently (T072-T073)
- **Breaking Changes**: Document every change in CHANGELOG-V1.0.md and MIGRATION-TO-V1.0.md
- **Commit Frequency**: Commit after each task or logical group
- **Performance**: Re-run benchmarks after any DB schema changes (T080)

---

**Total Tasks**: 82 tasks (65 implementation + 17 testing/validation)
**Estimated Timeline**: 8 days (1 day Pre-Phase 0 + 7 days implementation/validation)
**Success Criteria**: All 22 quickstart scenarios pass, <5% performance variance, 100% test pass rate

---

**Version**: 1.0  
**Status**: Ready for execution  
**Next Step**: Execute tasks sequentially, mark completed with ✅ or failed with ❌
