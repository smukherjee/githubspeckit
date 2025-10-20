# VS Code Testing Extension - Failure Analysis
**Date**: 2025-01-20  
**Total Tests**: 443  
**Passing**: 373 (84.2%)  
**Failing**: 31  
**Skipped**: 40

## Summary by Category

### 1. Authentication Fixture Failures (12 tests) 🔐
**Root Cause**: Database seeding issue - credentials mismatch

#### Affected Tests:
- `test_cache_headers.py` (6 tests) - All failing on `superadmin_headers` fixture
- `test_idor_tenant_isolation.py` (8 tests) - Failing on `regular_user_headers` and `superadmin_headers` fixtures

#### Error Details:
```python
# Regular user login fails
AssertionError: Login failed: {"detail":"invalid_credentials"}
assert 401 == 200
# Expected: infysightuser@infysight.com / infysightuser123

# Superadmin login fails  
assert 401 == 200
# Expected: infysightsa@infysight.com / infysightsa123
```

#### Files Affected:
1. `tests/security/test_cache_headers.py::test_user_endpoints_prevent_caching`
2. `tests/security/test_cache_headers.py::test_policy_endpoints_prevent_caching`
3. `tests/security/test_cache_headers.py::test_audit_endpoints_prevent_caching`
4. `tests/security/test_cache_headers.py::test_tenant_endpoints_prevent_caching`
5. `tests/security/test_cache_headers.py::test_feature_flags_prevent_caching`
6. `tests/security/test_cache_headers.py::test_security_headers_include_xss_protection`
7. `tests/security/test_idor_tenant_isolation.py::test_idor_query_param_rejected`
8. `tests/security/test_idor_tenant_isolation.py::test_idor_path_param_cross_tenant_denied`
9. `tests/security/test_idor_tenant_isolation.py::test_idor_path_param_same_tenant_allowed`
10. `tests/security/test_idor_tenant_isolation.py::test_idor_jwt_signature_tampering`
11. `tests/security/test_idor_tenant_isolation.py::test_idor_session_hijacking_requires_superadmin`
12. `tests/security/test_idor_tenant_isolation.py::test_idor_malformed_tenant_id_format`
13. `tests/security/test_idor_tenant_isolation.py::test_idor_protection_summary`
14. `tests/security/test_idor_tenant_isolation.py::test_idor_superadmin_cross_tenant_allowed`

**Fix Required**: 
- Check database seed script
- Verify user passwords are hashed correctly
- Ensure `conftest.py` fixture credentials match seeded users

---

### 2. User Creation Endpoint Failures (5 tests) 💥
**Root Cause**: POST `/api/v1/users` returns 500 (TypeError: internal_error)

#### Affected Tests:
1. `tests/integration/test_audit_scenarios.py::test_audit_trail_verification`
2. `tests/integration/test_superadmin_scenarios.py::test_superadmin_cross_tenant_management`
3. `tests/integration/test_tenant_admin_scenarios.py::test_tenant_admin_user_management`
4. `tests/integration/test_tenant_isolation.py::test_tenant_isolation`
5. `tests/performance/test_admin_api_performance.py::test_admin_api_performance`

#### Error Example:
```python
AssertionError: Failed to create user: {"error":{"code":"TypeError","message":"internal_error","correlation_id":"pending"}}
assert 500 == 201
```

**Fix Required**:
- Investigate POST `/api/v1/users` endpoint implementation
- Check request validation and parameter handling
- Review TypeError in user creation logic

---

### 3. Health Endpoint Authentication (6 tests) 🏥
**Root Cause**: `/health` endpoint requires authentication (returns 401)

#### Affected Tests:
1. `tests/contract/test_v1_contract.py::TestNoDeprecationHeaders::test_no_sunset_header`
2. `tests/contract/test_v1_contract.py::TestNoDeprecationHeaders::test_no_deprecation_header`
3. `tests/contract/test_v1_contract.py::TestNoDeprecationHeaders::test_no_api_warn_header`
4. `tests/contract/test_v1_contract.py::TestRateLimitingHeaders::test_rate_limit_headers_on_success`
5. `tests/contract/test_v1_contract.py::TestRateLimitingHeaders::test_rate_limit_headers_on_404`
6. `tests/contract/test_v1_contract.py::TestErrorResponseFormat::test_404_error_format`

#### Error:
```python
response = await client.get("/health")
assert response.status_code == 200
E assert 401 == 200  # Unauthorized
```

**Fix Required**:
- `/health` endpoint should be public (no authentication)
- Remove authentication middleware from health check routes

---

### 4. Tenant Context Switching (2 tests) 🔄
**Root Cause**: POST `/api/v1/admin/context/tenant` returns 500

#### Affected Tests:
1. `tests/contract/tenant_context/test_switch_tenant.py::test_switch_tenant_success_200`
2. `tests/contract/tenant_context/test_switch_tenant.py::test_switch_tenant_schema_validation`

#### Error:
```python
response = await client.post(
    "/api/v1/admin/context/tenant",
    json={"target_tenant_id": target_tenant_id},
    headers=superadmin_headers
)
assert response.status_code == 200
E assert 500 == 200  # Internal Server Error
```

**Fix Required**:
- Implement or fix tenant context switching endpoint
- Check endpoint exists in router configuration

---

### 5. Missing Dependency (1 test) 📦
**Root Cause**: `jsonschema` module not installed

#### Affected Test:
- `tests/contract/tenant_context/test_tenant_scoped_users.py::test_list_tenant_users_schema_validation`

#### Error:
```python
import jsonschema
E ModuleNotFoundError: No module named 'jsonschema'
```

**Fix Required**:
- Add `jsonschema` to requirements.txt
- Run `pip install jsonschema`

---

### 6. Rate Limiting Tests - AsyncIO Loop Issues (2 tests) ⚙️
**Root Cause**: PostgreSQL connection attached to different asyncio loop

#### Affected Tests:
1. `tests/security/test_rate_limiting.py::test_rate_limit_enforcement_exceeding_threshold_returns_429`
2. `tests/security/test_rate_limiting.py::test_superadmin_bypasses_rate_limit`

#### Error:
```python
RuntimeError: Task <Task pending...> got Future <Future pending...> attached to a different loop
asyncpg/protocol/protocol.pyx:375: RuntimeError
```

**Fix Required**:
- Fixture scope issue with async database connections
- Use proper event loop management for async fixtures
- Possibly related to mixing SQLite (conftest) with PostgreSQL (rate limiting tests)

---

### 7. Rate Limiting - User Creation Still 500 (1 test) 💥
**Root Cause**: Same as category #2 (related)

#### Affected Test:
- `tests/security/test_rate_limiting.py::test_rate_limit_headers_present_in_responses`

#### Error:
```python
response = await client.post("/api/v1/users", json={...})
assert response.status_code == 201, f"Expected 201, got {response.status_code}"
E AssertionError: Expected 201, got 500
```

**Fix Required**: Same as category #2

---

## Prioritized Fix Plan

### Priority 1: Critical Infrastructure (18 tests)
**Impact**: Blocks multiple test categories

1. **Fix Database Seeding** (12 tests)
   - Verify seed script creates correct users
   - Check password hashing in seed
   - Validate `conftest.py` credentials match seed data

2. **Fix POST `/api/v1/users` Endpoint** (6 tests)
   - Debug TypeError in user creation
   - Check request validation
   - Verify all required fields handled correctly

### Priority 2: Configuration Issues (7 tests)
**Impact**: Quick wins, simple fixes

3. **Make `/health` Public** (6 tests)
   - Remove authentication requirement
   - Update router configuration

4. **Install jsonschema** (1 test)
   - Add to requirements.txt
   - `pip install jsonschema`

### Priority 3: Feature Implementation (2 tests)
**Impact**: May need new code

5. **Implement Tenant Context Switching** (2 tests)
   - Create or fix `/api/v1/admin/context/tenant` endpoint
   - Add route to admin router

### Priority 4: AsyncIO Architecture (2 tests)
**Impact**: Complex, requires refactoring

6. **Fix Rate Limiting Async Fixtures** (2 tests)
   - Review fixture scopes
   - Ensure proper event loop management
   - Consider using same DB engine for all tests

---

## Quick Reference

### Tests by File

| File | Failed | Total | Pass Rate |
|------|--------|-------|-----------|
| `test_cache_headers.py` | 6 | 6 | 0% |
| `test_idor_tenant_isolation.py` | 8 | 8 | 0% |
| `test_v1_contract.py` | 6 | ~50 | ~88% |
| `test_rate_limiting.py` | 3 | 4 | 25% |
| `test_switch_tenant.py` | 2 | 2 | 0% |
| `test_audit_scenarios.py` | 1 | 1 | 0% |
| `test_superadmin_scenarios.py` | 1 | 1 | 0% |
| `test_tenant_admin_scenarios.py` | 1 | 1 | 0% |
| `test_tenant_isolation.py` | 1 | 1 | 0% |
| `test_admin_api_performance.py` | 1 | 1 | 0% |
| `test_tenant_scoped_users.py` | 1 | 1 | 0% |

### Root Causes Summary

| Issue | Tests Affected | Complexity |
|-------|----------------|------------|
| Auth fixture login failures | 12 | Low - Seed data |
| User creation 500 error | 6 | Medium - API bug |
| Health endpoint auth | 6 | Low - Config |
| Missing jsonschema | 1 | Trivial - Dependency |
| Tenant switching 500 | 2 | Medium - Implementation |
| AsyncIO loop issues | 2 | High - Architecture |

---

## Immediate Next Steps

1. **Check database seed** → Fix auth fixture failures (12 tests)
2. **Debug user creation endpoint** → Fix 500 errors (6 tests)
3. **Make /health public** → Fix contract tests (6 tests)
4. **Install jsonschema** → Fix 1 test
5. **Implement tenant switching** → Fix 2 tests
6. **Refactor rate limiting fixtures** → Fix 2 tests

**Expected Result**: All 31 failing tests should pass
**Estimated Time**: 
- Priority 1: 2-3 hours
- Priority 2: 30 minutes
- Priority 3: 1-2 hours
- Priority 4: 2-3 hours

**Total**: ~6-9 hours to fix all failures
