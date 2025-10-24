# Tasks.md Replacement Summary

**Date**: 2025-10-20  
**Branch**: 012-v1-cleanup-legacy-removal  
**Action**: Replaced tasks.md with revised version aligned to updated plan.md scope

---

## What Changed

### Old tasks.md (backed up as tasks-old-backup.md)
- **Lines**: 496
- **Tasks**: 13 (incomplete, original scope)
- **Timeline**: 8 days
- **Scope**: Included rate limiting implementation, policy routes

### New tasks.md
- **Lines**: 584
- **Tasks**: 75 (comprehensive, revised scope)
- **Timeline**: 10 days
- **Scope**: **Defers** policies, rate limiting, feature flags, invitations to Phase 2

---

## Key Differences

### ✅ Added to New tasks.md

1. **Test Cleanup Tasks (T019-T025)** - 7 tasks
   - Mark 14 policy integration tests as skipped (spec 017)
   - Mark 2 feature flag tests as skipped (spec 017)
   - Mark 8 rate limiting tests as skipped (spec 018)
   - Mark 3 deprecation header tests as skipped
   - Fix 14 async fixture errors (cache headers + IDOR tests)

2. **Comprehensive TDD Test Suite (T012-T018)** - 7 contract tests
   - Deprecated routes return 404
   - Admin routes exist and require auth
   - Email uniqueness per-tenant enforcement
   - No deprecation headers in responses
   - OpenAPI version is 1.0.0
   - Health endpoint returns V1.0 version

3. **Enhanced Documentation (T057-T065)** - 9 tasks
   - CHANGELOG-V1.0.md with breaking changes
   - MIGRATION-TO-V1.0.md step-by-step guide
   - Database schema exports and ERD generation
   - Metrics and logging documentation updates

4. **Docker Compose Environment (T050-T056)** - 7 tasks
   - 4-service docker-compose.yml (PostgreSQL, Redis, pgAdmin, API)
   - Dockerfile with hot-reload support
   - Makefile Docker workflow targets
   - Environment testing on clean macOS/Linux

5. **Quality & Polish (T066-T075)** - 10 tasks
   - Full test suite validation (0 failures target)
   - Quickstart.md end-to-end validation
   - Performance benchmarks (<5% variance)
   - Security regression tests
   - Duplication/complexity checks
   - OWASP ZAP dynamic security testing

### ❌ Removed from New tasks.md

1. **Rate Limiting Implementation**
   - Removed slowapi/fastapi-limiter setup
   - Removed rate limit middleware tasks
   - Deferred to spec 018

2. **Policy Routes Implementation**
   - Removed `/api/v1/admin/policies` router tasks
   - Removed policy management integration
   - Deferred to spec 017

3. **Feature Flags Enhancement**
   - Removed feature flag visibility tasks
   - Deferred to spec 017

---

## Alignment with Updated plan.md

The new tasks.md correctly reflects the plan.md revision made earlier today:

### Plan.md Changes (Summary Section)
```markdown
**V1.0 Release Scope (Revised)**:
- ✅ Remove deprecation code
- ✅ Enforce per-tenant email uniqueness
- ✅ Keep working admin routes only
- ✅ Mark incomplete feature tests as skipped

**Deferred to Phase 2**:
- ❌ Tenant-scoped policy routes (spec 017)
- ❌ Rate limiting implementation (spec 018)
- ❌ Feature flags visibility (spec 017)
- ❌ Invitation acceptance endpoints
```

### Tasks.md Alignment
- ✅ T019-T022: Mark deferred feature tests as skipped
- ✅ T038: Remove incomplete policy routes from app.py
- ✅ T010: Remove rate limiting config from descriptor.toml
- ✅ T047: OpenAPI description lists deferred features
- ✅ No rate limiting implementation tasks included

---

## Task Breakdown by Phase

| Phase | Tasks | Description |
|-------|-------|-------------|
| **Pre-Phase 0** | T001-T007 (7) | Database audit tooling, SchemaSpy, SQLFluff |
| **Phase 3.1** | T008-T011 (4) | Setup: schema_version table, env config |
| **Phase 3.2** | T012-T025 (14) | **Tests First (TDD)** + mark deferred tests skipped |
| **Phase 3.3** | T026-T045 (20) | Core: remove deprecated code, migrations, email uniqueness |
| **Phase 3.4** | T046-T062 (17) | Integration: OpenAPI, Docker, documentation |
| **Phase 3.5** | T063-T065 (3) | Observability: audit events, metrics, logging |
| **Phase 3.6** | T066-T075 (10) | Polish: testing, validation, quality gates |
| **TOTAL** | **75 tasks** | **10-day timeline** |

---

## Parallel Execution Capability

The new tasks.md includes **37 parallel tasks [P]** across:
- Contract tests (T012-T018): 7 parallel
- Test cleanup (T019-T022): 4 parallel
- Database audit scripts (T002-T004): 3 parallel
- Setup (T010-T011): 2 parallel
- Delete deprecated code (T026, T027, T031, T032): 4 parallel
- Documentation (T057-T062): 6 parallel
- Observability docs (T064-T065): 2 parallel
- Polish (T071-T073): 3 parallel

**Parallel execution examples** provided for:
1. Writing 7 contract tests simultaneously
2. Marking deferred tests as skipped in 4 terminals
3. Deleting deprecated code in 4 terminals
4. Creating 5 documentation files simultaneously

---

## Expected Test Suite Outcome

### Before Tasks Execution
- 368 passing
- 40 skipped
- **32 failing** (blocking V1.0)
- 20 ERROR (async fixture issues)

### After Tasks Execution (Target)
- ~368 passing (maintained)
- **65+ skipped** (40 existing + 25 deferred features)
- **0 failing** ✅
- **0 ERROR** ✅ (T023-T024 fix async issues)

### Skipped Test Breakdown
- 14 policy integration tests (spec 017)
- 8 rate limiting tests (spec 018)
- 2 feature flag tests (spec 017)
- 3 deprecation header tests (V1.0 baseline)
- ~38 existing skipped tests (other deferred features)

---

## Validation & Quality Gates

New tasks.md includes comprehensive validation:

- **T066**: Full test suite (0 failures requirement)
- **T067**: Quickstart.md end-to-end validation (22 scenarios)
- **T068**: Performance benchmarks (email lookup p95 <30ms)
- **T069**: Security regression tests (RBAC, tenant isolation)
- **T070**: OpenAPI spec validation (3.1.0 schema compliance)
- **T071**: Test coverage thresholds (≥85% overall, ≥90% domain)
- **T072**: Duplication check (<3% threshold via jscpd)
- **T073**: Complexity check (avg B, max C via xenon)
- **T074**: OWASP ZAP dynamic security testing
- **T075**: Quality justifications documentation

---

## Files Changed

### Replaced
- `specs/012-v1-cleanup-legacy-removal/tasks.md` (496 → 584 lines)

### Backup Created
- `specs/012-v1-cleanup-legacy-removal/tasks-old-backup.md` (original 496 lines preserved)

### New Summary Document
- `specs/012-v1-cleanup-legacy-removal/TASKS_REPLACEMENT_SUMMARY.md` (this file)

---

## Next Steps

1. ✅ **Review** tasks.md to ensure alignment with revised scope
2. ⏹️ **Execute** tasks starting with T001 (database audit tooling)
3. ⏹️ **Track** progress by marking completed tasks with `[x]`
4. ⏹️ **Validate** after each phase (run tests, check quality gates)
5. ⏹️ **Complete** all 75 tasks for V1.0 release readiness

---

## Constitutional Compliance

The new tasks.md maintains constitutional alignment:

- ✅ **Test-First (Principle II)**: Phase 3.2 tests MUST fail before Phase 3.3 implementation
- ✅ **Complexity Reduction (Principle IX)**: Deferred features reduce V1.0 scope, lowering implementation complexity
- ✅ **Quality Gates (Governance)**: T072-T075 enforce duplication <3%, complexity avg B/max C
- ✅ **Observability (Principle V)**: T063-T065 update metrics, logging, audit events for V1.0
- ✅ **Developer Experience (Principle VIII)**: T050-T056 Docker Compose + native workflows

---

**Status**: ✅ REPLACEMENT COMPLETE  
**Backup**: tasks-old-backup.md (496 lines)  
**Active**: tasks.md (584 lines, 75 tasks)  
**Ready**: Execute T001 to begin Pre-Phase 0

