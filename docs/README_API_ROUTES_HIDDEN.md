# API Routes Hidden & Tests Skipped - Complete Summary

## Overview
This document provides a complete overview of the changes made to hide feature-flags and policies API routes from OpenAPI documentation and mark all dependent tests as skipped.

## Changes Made

### 1. API Routes Commented Out

**Files Modified:**
- `src/adapters/api/app.py` (lines 30, 31, 287, 288)
- `src/adapters/api/routers/tenants/__init__.py`

**Routes Hidden:**
- `POST /api/v1/feature-flags` - Create feature flag
- `GET /api/v1/feature-flags` - List feature flags
- `POST /api/v1/policies/dry-run` - Policy dry-run evaluation
- `POST /api/v1/policies/register` - Register policy
- `GET /api/v1/policies` - List policies
- `PUT /api/v1/policies/{policy_id}/disable` - Disable policy
- `PUT /api/v1/policies/{policy_id}/enable` - Enable policy
- `DELETE /api/v1/policies/{policy_id}` - Delete policy
- `GET /api/v1/tenants/{tenant_id}/policies` - Tenant-scoped policies

**Status:** ✅ Complete
**Documentation:** `OPENAPI_ROUTES_HIDDEN.md`

### 2. Tests Marked as Skipped

**Files Modified:**
- `tests/contract/test_openapi_feature_flags.py` (1 test)
- `tests/contract/test_openapi_policy_dry_run.py` (2 tests)
- `tests/contract/test_openapi_policy_registration.py` (1 test)
- `tests/integration/test_feature_flag_scenarios.py` (1 test)
- `tests/integration/test_policy_api.py` (11 tests)

**Total:** 5 files, ~16 test functions

**Method:** Module-level `pytestmark = pytest.mark.skip(...)` added to each file

**Status:** ✅ Complete, Verified
**Documentation:** `TESTS_MARKED_SKIPPED.md`

## Files Created

### Documentation
1. **OPENAPI_ROUTES_HIDDEN.md** (3.7 KB)
   - Details which API routes were commented out
   - Lists all endpoints that are no longer in OpenAPI docs
   - Provides rollback instructions

2. **TESTS_MARKED_SKIPPED.md** (5.0 KB)
   - Lists all tests marked as skipped
   - Explains which tests were NOT modified and why
   - Provides commands to verify and re-enable tests

3. **README_API_ROUTES_HIDDEN.md** (this file)
   - High-level overview of all changes
   - Quick reference guide

### Scripts
4. **mark_tests_skipped.py** (2.3 KB)
   - Python script used to systematically add skip markers
   - Reusable for similar tasks

### Backups
5. **src/adapters/api/app.py.backup**
   - Original app.py before route comments
   - Can be used to restore routes

## Quick Reference

### To Verify Changes

```bash
# Check that routes are commented out
grep -n "# from adapters.api.routers import policies" \
    src/adapters/api/app.py

grep -n "# app.include_router(policies_router" \
    src/adapters/api/app.py

# Verify tests are skipped
.venv/bin/pytest tests/contract/test_openapi_feature_flags.py \
                  tests/contract/test_openapi_policy_dry_run.py \
                  tests/contract/test_openapi_policy_registration.py -v
```

### To Restore Everything

```bash
# 1. Restore API routes
cp src/adapters/api/app.py.backup src/adapters/api/app.py

# Manually uncomment in src/adapters/api/routers/tenants/__init__.py:
# - from .policies import router as policies_router
# - router.include_router(policies_router)

# 2. Remove test skip markers
sed -i '' '/^pytestmark = pytest.mark.skip/d' \
    tests/contract/test_openapi_*.py

sed -i '' '/^pytestmark = pytest.mark.skip/d' \
    tests/integration/test_*_api.py

# 3. Run tests to verify
.venv/bin/pytest tests/contract tests/integration -v
```

## Impact Assessment

### API
- ✅ Routes are hidden from OpenAPI/Swagger docs at `/docs`
- ⚠️ Existing API clients will receive 404 errors
- ⚠️ Frontend must be updated to remove these route calls

### Tests
- ✅ Contract tests (4 tests) marked as skipped
- ✅ Integration tests (~12 tests) marked as skipped
- ✅ Unit/persistence tests unchanged (don't call HTTP endpoints)
- ✅ Test suite can still run with `pytest tests/`

### Frontend
- ⚠️ **Action Required:** Update frontend to remove references to:
  - `/api/v1/feature-flags`
  - `/api/v1/policies`
  - Feature flag and policy resource components
  - Data provider special handling for these resources

## Related Documentation

- **OPENAPI_ROUTES_HIDDEN.md** - Detailed API route changes
- **TESTS_MARKED_SKIPPED.md** - Detailed test modifications
- **src/adapters/api/app.py.backup** - Original API router configuration

## Timeline

- **Date:** October 20, 2025
- **Task 1:** Comment out API routes (✅ Complete)
- **Task 2:** Mark tests as skipped (✅ Complete)
- **Next:** Update frontend to remove references to these endpoints

## Notes

- No code was deleted - routes and tests are preserved for future use
- All changes are easily reversible
- Clear skip reasons and comments explain why routes are hidden
- Documentation provides full context for future developers

---

**For questions or to restore functionality, see the detailed documentation files listed above.**
