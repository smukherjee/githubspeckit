# Phase 0 Research: V1.0 Release - Legacy Code Removal & Cleanup

**Feature**: 012-v1-cleanup-legacy-removal  
**Date**: 2025-10-20

---

## 1. Database Migration Strategy (Alembic UNIQUE Constraint Changes)

### Decision
Use Alembic with transaction-safe migration to drop global `UNIQUE(email)` constraint and add composite `UNIQUE INDEX idx_users_email_tenant ON users (email, tenant_id)`.

### Implementation Pattern
```python
# alembic/versions/xxxx_per_tenant_email_uniqueness.py
def upgrade():
    # Drop global unique constraint (if exists)
    op.drop_constraint('users_email_key', 'users', type_='unique')
    
    # Create composite unique index
    op.create_index(
        'idx_users_email_tenant',
        'users',
        ['email', 'tenant_id'],
        unique=True
    )

def downgrade():
    # Remove composite index
    op.drop_index('idx_users_email_tenant', table_name='users')
    
    # Restore global unique constraint (WARNING: May fail if duplicates exist)
    op.create_unique_constraint('users_email_key', 'users', ['email'])
```

### Pre-Migration Validation Script
```python
# scripts/validate_email_migration.py
async def check_duplicate_emails_within_tenants():
    """Verify no email conflicts exist within any single tenant before migration"""
    query = """
        SELECT tenant_id, email, COUNT(*) as cnt
        FROM users
        GROUP BY tenant_id, email
        HAVING COUNT(*) > 1
    """
    # If any rows returned: migration will fail, manual cleanup required
```

### Rationale
- **Transaction Safety**: Alembic wraps DDL in transactions (PostgreSQL supports transactional DDL)
- **Rollback Strategy**: Downgrade function provided but may fail if duplicate global emails introduced post-upgrade
- **Index vs Constraint**: Using UNIQUE INDEX provides same enforcement with better PostgreSQL query planner integration
- **Case Insensitivity**: Application layer normalizes email to lowercase before storage; database constraint is case-sensitive

### Alternatives Considered
1. **Zero-Downtime Migration**: Complex dual-write pattern rejected (V1.0 is breaking change release, brief downtime acceptable)
2. **Manual SQL**: Rejected in favor of Alembic for version tracking and rollback support
3. **Global Unique Kept**: Rejected per spec requirement FR-116 (per-tenant email namespaces)

---

## 2. OpenAPI V1.0 Generation

### Decision
Use FastAPI automatic OpenAPI generation with manual consolidation and curation in `contracts/openapi-v1.0.yaml`.

### Workflow
1. **Generate Base**: FastAPI's `/openapi.json` endpoint produces initial spec
2. **Consolidate Fragments**: Merge existing `contracts/openapi-base.yaml`, `contracts/openapi-auth-policy.yaml`, `contracts/openapi-observability.yaml`
3. **Manual Curation**:
   - Set `info.version: "1.0.0"`
   - Remove deprecated endpoints (if any lingering)
   - Add `x-rate-limit` extension info for rate-limited endpoints
   - Validate with OpenAPI 3.1.0 schema validator
4. **Contract Testing**: Use Schemathesis to auto-generate conformance tests

### Version Metadata Structure
```yaml
info:
  title: githubspeckit Backend API
  version: 1.0.0
  description: |
    Multi-tenant SaaS backend with RBAC, audit logging, and policy engine.
    
    **Breaking Changes in V1.0**:
    - Admin routes now under `/api/v1/admin/*` prefix
    - Email uniqueness scoped per-tenant (not global)
    - Removed backward compatibility middleware
  contact:
    name: API Support
    email: api-support@example.com
  license:
    name: MIT
  x-breaking-changes:
    - Query parameter `tenant_id` no longer supported
    - Deprecation headers (X-API-Deprecation, Sunset) removed
```

### Rationale
- **Accuracy**: Auto-generation ensures spec matches actual implementation
- **Maintainability**: Single source of truth (FastAPI route definitions)
- **Validation**: Schemathesis provides property-based contract testing

### Alternatives Considered
1. **Pure Manual YAML**: Rejected (high drift risk, maintenance burden)
2. **Code-First Tools** (e.g., pydantic-to-openapi): Redundant with FastAPI built-in generation
3. **Versioned Specs** (separate v0.9, v1.0 files): Rejected (V1.0 is only supported version post-release)

---

## 3. Router Architecture (FastAPI Prefix Changes)

### Decision
Use nested `APIRouter` pattern with hierarchical prefixes and tag-based OpenAPI grouping.

### Implementation Pattern
```python
# src/adapters/api/app.py
from fastapi import FastAPI
from adapters.api.routers.tenants import crud as tenants_crud
from adapters.api.routers import users, policies, roles

app = FastAPI(title="githubspeckit API", version="1.0.0")

# Admin routes (superadmin + tenant_admin within scope)
app.include_router(
    tenants_crud.router,
    prefix="/api/v1/admin",
    tags=["admin-tenants"]
)
app.include_router(
    users.router,
    prefix="/api/v1/admin",
    tags=["admin-users"]
)
app.include_router(
    policies.router,
    prefix="/api/v1/admin",
    tags=["admin-policies"]
)
app.include_router(
    roles.router,
    prefix="/api/v1/admin",
    tags=["admin-roles"]
)

# Tenant-scoped routes
app.include_router(
    users.tenant_scoped_router,  # If separate router for /tenants/{tenant_id}/users
    prefix="/api/v1",
    tags=["tenant-users"]
)

# Public routes
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)
```

### Router Nesting Best Practices
- **Path Parameters**: Inherited automatically from parent prefix
- **Dependency Injection**: RBAC dependencies applied at router level
- **Tags**: Group endpoints in OpenAPI UI for discoverability
- **Avoid Over-Nesting**: Max 2 levels (`/api/v1/admin` is sufficient; avoid `/api/v1/admin/section/subsection`)

### Testing Approach
```python
# tests/contract/test_v1_admin_routes.py
@pytest.mark.parametrize("path", [
    "/api/v1/admin/tenants",
    "/api/v1/admin/users",
    "/api/v1/admin/policies",
])
def test_admin_routes_exist(client, path):
    """Verify all admin routes reachable (404 vs 401/403 indicates route exists)"""
    response = client.get(path)
    assert response.status_code in [401, 403], f"Route {path} not found (got 404)"

@pytest.mark.parametrize("deprecated_path", [
    "/api/v1/tenants",  # Old flat route
    "/api/v1/users",    # Old flat route
])
def test_legacy_routes_removed(client, deprecated_path):
    """Verify old routes return 404 after prefix migration"""
    response = client.get(deprecated_path)
    assert response.status_code == 404
```

### Rationale
- **Modularity**: Each router (`tenants_crud`, `users`, etc.) remains independent
- **OpenAPI Grouping**: Tags create logical sections in generated docs
- **RBAC Integration**: Admin prefix signals admin-only access visually

### Alternatives Considered
1. **Flat Routers with Shared Prefix**: Harder to maintain consistent prefixes across files
2. **Blueprint Pattern** (Flask-style): Not idiomatic in FastAPI
3. **Manual Path Concatenation**: Error-prone, doesn't leverage FastAPI's router system

---

## 4. Dev Environment Strategy (Docker Compose + Native Workflow)

### Decision
Provide **independent** native Makefile workflow AND Docker Compose 4-service turnkey environment. Developers choose one path; no integration between them.

### Docker Compose Architecture
```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    ports: ['5432:5432']
    environment:
      POSTGRES_DB: infysight_users
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ['6379:6379']
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  pgadmin:
    image: dpage/pgadmin4:latest
    ports: ['5050:80']
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
      PGADMIN_CONFIG_SERVER_MODE: 'False'
    volumes:
      - pgadmin_data:/var/lib/pgadmin

  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports: ['8000:8000']
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/infysight_users
      REDIS_URL: redis://redis:6379/0
      LOG_LEVEL: INFO
    volumes:
      - ./src:/app/src  # Hot reload
      - ./alembic:/app/alembic
    command: uvicorn src.adapters.api.app:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
  redis_data:
  pgadmin_data:

networks:
  default:
    name: githubspeckit-net
```

### Makefile Integration
```makefile
# New targets for Docker workflow
.PHONY: docker-up docker-down docker-logs docker-reset

docker-up:
	docker-compose up -d
	@echo "Services starting... Check health with: make docker-logs"
	@echo "API: http://localhost:8000"
	@echo "pgAdmin: http://localhost:5050"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

docker-reset:
	docker-compose down -v  # Remove volumes too
	docker-compose up --build -d
```

### Native Workflow (Unchanged)
```makefile
# Existing targets continue to work independently
.PHONY: bootstrap dev test

bootstrap:
	# Create venv, install deps, setup DB, seed, start server
	# No Docker dependency
```

### Rationale
- **Contributor Flexibility**: Native for speed (local dev), Docker for consistency (cross-platform)
- **No Lock-In**: Either path works fully; no hybrid complexity
- **Hot Reload**: API volume mount enables fast iteration in Docker
- **pgAdmin**: GUI reduces learning curve for SQL debugging

### Alternatives Considered
1. **Docker-Only**: Rejected (slower iteration, overkill for experienced devs with local DB)
2. **Native-Only**: Rejected (excludes contributors without PostgreSQL expertise or incompatible OS)
3. **Hybrid Integration** (make bootstrap uses Docker if detected): Rejected (adds complexity, violates "choose one path" principle)

---

## 5. Rate Limiting Approach (Email Enumeration Protection)

### Decision
Use **slowapi** (FastAPI-compatible fork of Flask-Limiter) with Redis backend for distributed rate limiting.

### Implementation Strategy
```python
# src/adapters/api/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Global fallback
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window"
)

# In app.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On user creation endpoint
@router.post("/users", dependencies=[Depends(require_admin)])
@limiter.limit(lambda: f"{settings.RATE_LIMIT_USER_CREATION}/hour")
async def create_user(...):
    ...
```

### Configuration
```toml
# config/descriptor.toml
[security]
RATE_LIMIT_USER_CREATION = { type = "int", default = 100, description = "Max user creation attempts per hour per IP" }
```

### Scope & Bypass
- **Scope**: Per source IP address (via `get_remote_address`)
- **Admin Bypass**: Check RBAC role; if superadmin → skip rate limit
```python
@limiter.limit(lambda: f"{settings.RATE_LIMIT_USER_CREATION}/hour", exempt_when=is_superadmin)
```

### HTTP 429 Response Format
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "retry_after": 3600
    }
  },
  "trace_id": "abc-123-def"
}
```
Headers: `Retry-After: 3600` (seconds until reset)

### Rationale
- **Distributed**: Redis backend allows horizontal scaling
- **Configurable**: Environment variable enables production tuning
- **Transparent**: slowapi integrates natively with FastAPI dependency injection
- **Graceful Degradation**: If Redis unavailable, in-memory fallback (loses distributed property)

### Alternatives Considered
1. **fastapi-limiter**: Similar but less mature documentation
2. **Nginx-Level Limiting**: Rejected (loses application-level context like RBAC bypass)
3. **In-Memory Counters**: Rejected (not distributed, lost on restart)
4. **Per-Tenant Limiting**: Considered but rejected (IP-based is simpler, covers anonymous enumeration attempts)

---

## Summary

All research tasks completed. Key decisions:

1. **Database**: Transaction-safe Alembic migration with pre-validation
2. **OpenAPI**: FastAPI auto-gen + manual curation → v1.0 spec
3. **Routers**: Nested APIRouter with `/api/v1/admin` prefix
4. **Dev Env**: Independent Docker Compose (4 services) + native Makefile
5. **Rate Limiting**: slowapi + Redis with configurable threshold (default: 100/hour/IP)

**Ready for Phase 1**: All technical unknowns resolved.

---

**Version**: 1.0  
**Status**: Complete  
**Next Phase**: Phase 1 (Design & Contracts)
