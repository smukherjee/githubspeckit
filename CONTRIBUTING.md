# Contributing to githubspeckit

Thank you for your interest in contributing! This document outlines our development workflow, quality standards, and contribution process.

---

## Table of Contents

1. [Development Workflow](#development-workflow)
2. [Test-Driven Development (TDD)](#test-driven-development-tdd)
3. [Code Quality Standards](#code-quality-standards)
4. [Testing Requirements](#testing-requirements)
5. [Pull Request Process](#pull-request-process)
6. [Commit Conventions](#commit-conventions)
7. [Branch Strategy](#branch-strategy)

---

## Development Workflow

### Prerequisites

- Python 3.12+ (3.13 recommended)
- PostgreSQL 13+ (or use Docker Compose)
- Redis 6+ (optional for local dev, falls back to in-memory)
- Git

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/sujoymukherjee-corp/githubspeckit.git
cd githubspeckit

# 2. Bootstrap complete environment (native)
make bootstrap
# Output:
# - Creates .venv with all dependencies
# - Creates PostgreSQL database "infysight_users"
# - Runs Alembic migrations
# - Seeds infysight tenant + superadmin user
# - Starts API server on http://localhost:8000

# 3. Verify health
curl http://localhost:8000/v1/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

**Alternative: Docker Compose (Turnkey Environment)**

```bash
# Start all services (PostgreSQL, Redis, pgAdmin, API)
make docker-up

# View logs
make docker-logs

# Stop and remove containers
make docker-down

# Full cleanup (including volumes)
make docker-reset
```

---

## Test-Driven Development (TDD)

**CRITICAL**: This project **strictly enforces Test-Driven Development**. All new features and bug fixes MUST follow the Red-Green-Refactor cycle.

### TDD Red-Green-Refactor Cycle

```
1. RED: Write a failing test that defines desired behavior
2. GREEN: Write minimum code to make the test pass
3. REFACTOR: Improve code quality while keeping tests green
```

### Step-by-Step TDD Workflow

#### 1. **RED Phase: Write Failing Test First**

**Before writing ANY implementation code**, create a failing test that defines the expected behavior.

**Example** (adding a new API endpoint):

```python
# tests/contract/test_new_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_user_preferences_returns_preferences(client: AsyncClient, regular_user_headers):
    """GET /api/v1/users/{user_id}/preferences should return user preferences."""
    user_id = "some-user-uuid"
    
    response = await client.get(
        f"/api/v1/users/{user_id}/preferences",
        headers=regular_user_headers
    )
    
    # This will FAIL initially (404 Not Found) - that's expected!
    assert response.status_code == 200
    data = response.json()
    assert "theme" in data
    assert "language" in data
```

**Commit this failing test**:

```bash
git add tests/contract/test_new_feature.py
git commit -m "test(contract): Add failing test for user preferences endpoint (RED phase)"
```

**Run the test to confirm it fails**:

```bash
pytest tests/contract/test_new_feature.py::test_get_user_preferences_returns_preferences -v
# Expected: FAILED (404 Not Found)
```

✅ **RED Phase Complete** - You now have a failing test that defines the requirement.

#### 2. **GREEN Phase: Implement Minimum Code**

Now write the **minimum code** needed to make the test pass. Don't over-engineer!

**Example**:

```python
# src/adapters/api/routers/users.py

@router.get("/users/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """Get user preferences (minimal implementation)."""
    return {
        "theme": "light",
        "language": "en"
    }
```

**Run the test again**:

```bash
pytest tests/contract/test_new_feature.py::test_get_user_preferences_returns_preferences -v
# Expected: PASSED
```

**Commit the minimal implementation**:

```bash
git add src/adapters/api/routers/users.py
git commit -m "feat(users): Add user preferences endpoint (GREEN phase - minimal)"
```

✅ **GREEN Phase Complete** - Test is now passing.

#### 3. **REFACTOR Phase: Improve Code Quality**

Now improve the implementation while keeping the test green. Add:
- Proper dependency injection
- Database queries
- RBAC enforcement
- Error handling
- Additional tests for edge cases

**Example**:

```python
# src/adapters/api/routers/users.py

@router.get("/users/{user_id}/preferences")
async def get_user_preferences(
    user_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db)
):
    """Get user preferences with RBAC enforcement."""
    # RBAC: User can view own preferences, admins can view any
    tenant_context = request.state.tenant_context
    if not tenant_context.is_superadmin and str(tenant_context.user_id) != user_id:
        raise HTTPException(403, "Can only view own preferences")
    
    # Fetch from database
    prefs = await preferences_repo.get_by_user_id(session, user_id)
    if not prefs:
        raise HTTPException(404, "Preferences not found")
    
    return {
        "theme": prefs.theme,
        "language": prefs.language,
        "timezone": prefs.timezone
    }
```

**Run ALL tests** to ensure refactoring didn't break anything:

```bash
pytest tests/ -v
# All tests should still pass
```

**Commit the refactored code**:

```bash
git add src/adapters/api/routers/users.py src/adapters/persistence/repositories.py
git commit -m "refactor(users): Add RBAC and database integration to preferences endpoint"
```

✅ **REFACTOR Phase Complete** - Code is production-ready.

---

### TDD Pre-Merge Checklist

Before submitting a PR, verify you followed TDD:

- [ ] **Failing test committed BEFORE implementation** (check git history)
- [ ] **Test failure captured** (include test output in PR description or comments)
- [ ] **Minimal implementation made test pass** (GREEN phase commit exists)
- [ ] **Refactoring improved code quality** (REFACTOR phase commit exists)
- [ ] **All tests still pass after refactoring** (run `pytest tests/`)
- [ ] **Coverage maintained or improved** (run `make test` to check coverage)

**Example Git History** (correct TDD workflow):

```
* refactor(users): Add RBAC and database integration to preferences endpoint (HEAD)
* feat(users): Add user preferences endpoint (GREEN phase - minimal)
* test(contract): Add failing test for user preferences endpoint (RED phase)
```

**Anti-Pattern** (implementation-first, test-later - **DO NOT DO THIS**):

```
* test(users): Add tests for preferences endpoint  ❌ WRONG
* feat(users): Implement preferences endpoint      ❌ WRONG
```

---

## Code Quality Standards

### Coverage Requirements

**Hard Requirements** (CI enforced):
- **Domain layer**: ≥ 90% line coverage
- **Overall repository**: ≥ 85% line coverage
- **Critical paths** (auth, multi-tenancy): 100% statement coverage

**Coverage Gates**:
- New/changed files MUST NOT reduce aggregate coverage
- Coverage drop >0.5% requires justification in PR description
- Coverage drop >1.0% blocks merge until addressed

**Check coverage**:

```bash
make test  # Runs pytest with coverage report
# View HTML report: open htmlcov/index.html
```

### Code Quality Tools

**Linting** (Ruff):

```bash
make lint
# Fixes auto-fixable issues: ruff check --fix src/ tests/
```

**Type Checking** (Mypy - strict mode):

```bash
make typecheck
# Must pass with zero errors
```

**Complexity Analysis**:
- Maximum cyclomatic complexity: 10 per function
- Use `xenon` to analyze: `xenon --max-absolute B --max-modules B src/`

**Duplication Detection**:
- Maximum duplication: 8% overall, 15% per file
- Use `jscpd` to check: `jscpd src/`

---

## Testing Requirements

### Test Categories

**1. Unit Tests** (`tests/unit/`)
- Pure domain logic tests
- No external dependencies (mocked)
- Fast execution (<10ms per test)

**2. Integration Tests** (`tests/integration/`)
- API endpoint tests with real database
- Middleware integration tests
- Slower execution (50-200ms per test)

**3. Contract Tests** (`tests/contract/`)
- OpenAPI schema validation
- Request/response format verification
- RBAC enforcement tests

**4. Security Tests** (`tests/security/`)
- Authentication bypass attempts
- Tenant isolation boundary tests
- RBAC privilege escalation tests

### Writing Tests

**Test Naming Convention**:

```python
def test_<action>_<expected_result>_<conditions>():
    """Test that <action> <expected_result> when <conditions>."""
    pass

# Examples:
def test_create_user_returns_201_when_valid_data():
def test_get_user_raises_403_when_different_tenant():
def test_login_returns_jwt_token_when_credentials_valid():
```

**Test Structure** (Arrange-Act-Assert):

```python
@pytest.mark.asyncio
async def test_tenant_admin_cannot_access_other_tenant_users(client, tenant_admin_headers):
    """Tenant admin should receive 403 when accessing users from different tenant."""
    # ARRANGE
    other_tenant_id = "00000000-0000-0000-0000-000000000999"
    
    # ACT
    response = await client.get(
        f"/api/v1/tenants/{other_tenant_id}/users",
        headers=tenant_admin_headers
    )
    
    # ASSERT
    assert response.status_code == 403
    assert "cannot access other tenant" in response.json()["detail"].lower()
```

---

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b feat/user-preferences-endpoint
# Branch naming: feat/, fix/, chore/, perf/, refactor/, security/
```

### 2. Follow TDD Workflow

See [Test-Driven Development](#test-driven-development-tdd) section above.

### 3. Run Quality Checks

```bash
# Run all checks
make quality

# Individual checks:
make lint        # Ruff linting
make typecheck   # Mypy type checking
make test        # Pytest with coverage
```

### 4. Commit Changes

Follow [Commit Conventions](#commit-conventions) below.

### 5. Push and Create PR

```bash
git push origin feat/user-preferences-endpoint
# Create PR on GitHub
```

### 6. PR Requirements

**PR Description MUST include**:
- [ ] **User Story/Context**: What problem does this solve?
- [ ] **TDD Evidence**: Link to RED phase commit (failing test)
- [ ] **Testing**: List test categories covered (unit, integration, contract, security)
- [ ] **Coverage**: Confirm coverage maintained/improved (paste coverage report excerpt)
- [ ] **Breaking Changes**: Document any API changes
- [ ] **Migration**: Include Alembic migration if database changes

**PR Template**:

```markdown
## User Story
As a [user type], I want [feature] so that [benefit].

## TDD Evidence
- RED phase: [link to failing test commit]
- GREEN phase: [link to minimal implementation commit]
- REFACTOR phase: [link to refactored code commit]

## Testing
- [x] Unit tests (5 tests added)
- [x] Integration tests (2 tests added)
- [x] Contract tests (3 tests added)
- [x] Security tests (1 test added)

## Coverage
- Domain coverage: 92% → 93% (+1%)
- Overall coverage: 87% → 87% (maintained)

## Breaking Changes
None

## Checklist
- [x] Failing test committed before implementation
- [x] All tests passing
- [x] Coverage maintained (≥85% overall, ≥90% domain)
- [x] Lint passed (ruff)
- [x] Type check passed (mypy strict)
- [x] Documentation updated
```

### 7. Code Review

**Two reviewers required**:
- One domain expert (business logic, domain models)
- One infrastructure expert (API design, database, security)

**Review Criteria**:
- TDD workflow followed (check git history)
- Tests cover positive + negative scenarios
- RBAC enforcement present for protected endpoints
- Tenant isolation maintained
- Error handling comprehensive
- No commented-out code or TODOs without linked issues

---

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `test`: Adding or updating tests
- `refactor`: Code change that neither fixes bug nor adds feature
- `perf`: Performance improvement
- `chore`: Maintenance tasks (dependencies, tooling)
- `docs`: Documentation changes
- `security`: Security improvements

**Examples**:

```bash
git commit -m "feat(users): Add user preferences endpoint"
git commit -m "fix(auth): Prevent JWT replay attacks via jti validation"
git commit -m "test(rbac): Add tenant isolation boundary tests"
git commit -m "refactor(users): Extract email validation to domain layer"
git commit -m "security(logs): Add RBAC enforcement to log export endpoint"
```

---

## Branch Strategy

**Main Branches**:
- `main`: Always releasable, production-ready code
- `feat/*`: Feature branches (merge to main via PR)
- `fix/*`: Bug fix branches
- `security/*`: Security fix branches (fast-track review)

**Release Process**:
- Tags: `v1.0.0`, `v1.1.0`, etc. (semantic versioning)
- Automated changelog generation from commit messages
- Hotfix branches from release tags if needed

---

## Development Best Practices

### 1. **Small, Focused PRs**
- Ideal size: <400 lines of code changes
- One feature or bug fix per PR
- Split large features into incremental PRs

### 2. **Test Isolation**
- Each test should be independent
- Use fixtures for shared setup
- Clean up resources in teardown

### 3. **No Commented Code**
- Delete unused code, don't comment it out
- Use git history to recover old code if needed

### 4. **No TODOs Without Issues**
- Link TODOs to GitHub issues: `# TODO(#123): Implement retry logic`
- Unlinked TODOs block merge

### 5. **Security First**
- Never commit secrets (use `.env`, not `.env.production`)
- Validate all user inputs
- Enforce RBAC on protected endpoints
- Add audit events for sensitive operations

---

## Questions?

- **Slack**: #githubspeckit-dev
- **GitHub Discussions**: [Link to discussions]
- **Office Hours**: Wednesdays 2-3 PM UTC

---

**Happy Contributing!** 🎉

*Version: 1.0.0 | Last Updated: 2025-10-20*
