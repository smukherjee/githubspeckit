# Feature Specification: GitHub SpecKit SDK Package

**Feature ID**: 006  
**Priority**: 🔴 BLOCKING (MUST DO BEFORE /implement)  
**Status**: Planning  
**Owner**: Platform Team  
**Timeline**: 2 weeks (80 hours)  
**Related Findings**: CON2 (CRITICAL), E1 (HIGH), E2 (HIGH), C2 (MEDIUM)

## Overview

Build `githubspeckit-sdk` - a pip-installable Python package enabling third-party developers to integrate authentication and authorization in their applications with minimal code. Provides "plug-and-play" developer experience similar to Azure Entra ID / Auth0 SDKs.

## Problem Statement

**Current State**:

- ✅ `auth_core` package exists (internal reuse only)
- ❌ No pip-installable package for external developers
- ❌ No SDK client libraries
- ❌ No framework decorators (@require_auth)
- ❌ No cookiecutter template for new apps
- ❌ No integration guide for third-party developers

**Constitutional Violation**: Principle VIII (Developer Experience & Embed Readiness) requires "fast to bootstrap" and "embed-ready".

**User Requirement**: "plug and play like azure entraid without the user having to bother on the inner workings of the app"

## Solution Approach

### SDK Package Structure

```text
githubspeckit-sdk/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── src/
│   └── githubspeckit_sdk/
│       ├── __init__.py
│       ├── client.py          # AuthClient class
│       ├── decorators.py      # @require_auth, @require_roles
│       ├── models.py          # Pydantic models (User, Tenant, Token)
│       ├── exceptions.py      # Custom exceptions
│       ├── middleware.py      # Framework middleware adapters
│       └── utils.py           # Helper functions
├── tests/
│   ├── test_client.py
│   ├── test_decorators.py
│   └── test_models.py
└── examples/
    ├── fastapi_example.py
    ├── flask_example.py
    └── django_example.py
```

### Minimal Integration Example

```python
# 4 lines of code to add authentication
from githubspeckit_sdk import AuthClient, require_auth

auth = AuthClient(api_base_url="https://api.example.com", client_id="...", client_secret="...")

@app.get("/protected")
@require_auth(roles=["admin"])
async def protected_endpoint(user: User):
    return {"message": f"Hello {user.full_name}"}
```

## Functional Requirements

### FR-101: AuthClient SDK Class

**Priority**: P0 (CRITICAL)  
**Description**: Core client class for authentication operations.

**Acceptance Criteria**:

- ✅ `AuthClient(api_base_url, client_id, client_secret, timeout=30)` constructor
- ✅ `async login(email, password) -> TokenResponse` - Email/password authentication
- ✅ `async login_social(provider) -> str` - Initiate social login (returns auth URL)
- ✅ `async exchange_code(code, provider) -> TokenResponse` - Exchange OAuth2 code
- ✅ `async refresh(refresh_token) -> TokenResponse` - Refresh access token
- ✅ `async get_user(access_token) -> User` - Fetch current user
- ✅ `async validate_token(access_token) -> User` - Validate JWT + return user
- ✅ Automatic token refresh when access_token expires
- ✅ Connection pooling for efficient HTTP reuse

### FR-102: Framework Decorators

**Priority**: P0 (CRITICAL)  
**Description**: Decorators for FastAPI, Flask, Django route protection.

**Acceptance Criteria**:

- ✅ `@require_auth()` - Requires valid JWT, injects `User` into function args
- ✅ `@require_roles(*roles)` - Requires user has at least one specified role
- ✅ `@require_tenant(tenant_id)` - Validates user belongs to tenant
- ✅ FastAPI: Dependency injection compatible
- ✅ Flask: Blueprint-compatible decorator
- ✅ Django: Middleware + decorator pattern
- ✅ Returns 401 Unauthorized if token invalid/missing
- ✅ Returns 403 Forbidden if role check fails

### FR-103: Pydantic Models

**Priority**: P0 (CRITICAL)  
**Description**: Type-safe models for API responses.

**Acceptance Criteria**:

- ✅ `User(id, tenant_id, email, full_name, roles, is_active, created_at)`
- ✅ `Tenant(id, name, is_active, settings)`
- ✅ `TokenResponse(access_token, refresh_token, expires_in, token_type)`
- ✅ `Policy(id, tenant_id, resource, action, effect, conditions)`
- ✅ All models JSON-serializable
- ✅ Validation errors with clear messages

### FR-104: Error Handling

**Priority**: P1 (HIGH)  
**Description**: Standardized exception hierarchy.

**Acceptance Criteria**:

- ✅ `AuthenticationError` - Invalid credentials, token expired
- ✅ `AuthorizationError` - Insufficient permissions
- ✅ `TokenExpiredError` - Access token expired (trigger refresh)
- ✅ `NetworkError` - API unreachable, timeout
- ✅ `ValidationError` - Invalid input data
- ✅ All exceptions include: `message`, `code`, `details`, `docs_url`

### FR-105: Middleware Adapters

**Priority**: P2 (MEDIUM)  
**Description**: Framework-specific middleware for automatic authentication.

**Acceptance Criteria**:

- ✅ `FastAPIAuthMiddleware(auth_client)` - FastAPI middleware
- ✅ `FlaskAuthMiddleware(auth_client)` - Flask WSGI middleware
- ✅ `DjangoAuthMiddleware(auth_client)` - Django middleware
- ✅ Extracts JWT from `Authorization: Bearer <token>` header
- ✅ Injects authenticated user into request context
- ✅ Configurable public paths (skip auth for `/health`, `/docs`)

## Non-Functional Requirements

### NFR-101: Package Distribution

**Description**: SDK must be pip-installable from PyPI with semantic versioning.

**Acceptance Criteria**:

- ✅ Published to PyPI: `pip install githubspeckit-sdk`
- ✅ Versioning: SemVer 2.0 (e.g., v1.0.0)
- ✅ Python compatibility: 3.9+
- ✅ Dependencies: `httpx`, `pydantic>=2.0`, `python-jose[cryptography]`
- ✅ Changelog maintained (keep-a-changelog format)

### NFR-102: Documentation

**Description**: Comprehensive documentation for developers.

**Acceptance Criteria**:

- ✅ README.md: Installation, quickstart, examples
- ✅ API Reference: All classes, methods, parameters documented
- ✅ Integration guides: FastAPI, Flask, Django
- ✅ Error handling guide: Common errors + solutions
- ✅ Migration guide: Upgrading between versions
- ✅ Hosted documentation: Read the Docs or GitHub Pages

### NFR-103: Testing

**Description**: SDK must have ≥90% test coverage.

**Acceptance Criteria**:

- ✅ Unit tests: All public methods
- ✅ Integration tests: Mocked backend API responses
- ✅ Framework tests: FastAPI, Flask, Django decorator/middleware
- ✅ Coverage: ≥90% line coverage
- ✅ CI/CD: GitHub Actions runs tests on PR

### NFR-104: Performance

**Description**: SDK must not introduce significant overhead.

**Acceptance Criteria**:

- ✅ Token validation: <10ms (local JWT verification)
- ✅ API calls: Connection pooling reduces latency 30%
- ✅ Memory footprint: <50MB per process
- ✅ No global state (thread-safe)

## Technical Constraints

1. **Build Tool**: `hatch` for package management
2. **HTTP Client**: `httpx` (async + sync support)
3. **JWT Library**: `python-jose` (same as backend)
4. **Python Versions**: 3.9, 3.10, 3.11, 3.12, 3.13
5. **License**: MIT (permissive for commercial use)
6. **No Backend Code Imports**: SDK must be self-contained (no auth_core imports)

## Success Criteria

### Exit Criteria

- ✅ CON2 finding resolved: SDK package published to PyPI
- ✅ E1 finding resolved: Third-party integration guide complete
- ✅ E2 finding resolved: Cookiecutter template created
- ✅ C2 finding resolved: Constitutional Principle VIII compliance
- ✅ Package published: `pip install githubspeckit-sdk` works
- ✅ Examples: 3 framework examples (FastAPI, Flask, Django)
- ✅ Documentation: Integration guide published
- ✅ Testing: ≥90% coverage, CI passing

### Metrics

- **Adoption**: 10+ third-party apps using SDK (6-month target)
- **Developer Experience**: Quickstart <30 minutes (feedback surveys)
- **Reliability**: 99.9% PyPI availability
- **Performance**: <10ms token validation overhead

## Dependencies

- Backend API: JWT token validation endpoints
- PyPI account: Package publishing credentials
- Documentation hosting: Read the Docs or GitHub Pages

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking API changes | HIGH | SemVer versioning + deprecation warnings |
| Framework compatibility | MEDIUM | Extensive testing across framework versions |
| Security vulnerabilities | CRITICAL | Dependency scanning + quarterly security audits |
| Adoption resistance | MEDIUM | Clear documentation + example apps + support |

## Out of Scope

- JavaScript/TypeScript SDK (future: 007-js-sdk)
- Mobile SDK (iOS/Android) (future: 008-mobile-sdk)
- CLI tool for SDK setup (future enhancement)
- SDK admin UI for key management (future enhancement)

## Appendix

### Related Documents

- Security Analysis Report: Finding CON2, E1, E2, C2
- Constitution Principle VIII: Developer Experience & Embed Readiness
- Azure Entra ID SDK (reference implementation)
- Auth0 SDK (reference implementation)

### Example Integration (FastAPI)

```python
from fastapi import FastAPI, Depends
from githubspeckit_sdk import AuthClient, require_auth, User

app = FastAPI()
auth = AuthClient(
    api_base_url="https://api.githubspeckit.com",
    client_id="my-app-client-id",
    client_secret="my-app-secret"
)

# Public endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}

# Protected endpoint
@app.get("/profile")
@require_auth()
async def get_profile(user: User = Depends(auth.current_user)):
    return {"user": user.dict()}

# Admin-only endpoint
@app.post("/admin/tenants")
@require_auth(roles=["tenant_admin", "superadmin"])
async def create_tenant(user: User = Depends(auth.current_user)):
    return {"message": "Tenant created"}
```

### Cookiecutter Template Structure

```text
cookiecutter-githubspeckit-app/
├── {{cookiecutter.project_name}}/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   └── tests/
│       └── test_main.py
└── cookiecutter.json
    {
      "project_name": "my-app",
      "framework": ["fastapi", "flask", "django"],
      "python_version": "3.11",
      "use_async": true
    }
```
