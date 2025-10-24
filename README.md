# githubspeckit-backend

**Version**: 1.0.0  
**Status**: Production Ready

Modern enterprise-grade multi-tenant FastAPI backend (hexagonal, auth core, observability, quality gates).

📚 **[Migration Guide to V1.0](docs/MIGRATION-TO-V1.0.md)** - Step-by-step instructions for upgrading from pre-V1.0 versions

## Prerequisites

### Native Development

- Python 3.13 or newer (recommended: 3.13)
- pip (comes with Python)
- [uv](https://github.com/astral-sh/uv) (for dependency management)
- GNU Make (for running Makefile targets)
- PostgreSQL 14+ (for database)

Install `uv` if not present:

```sh
pip install uv
```

### Docker Development (Recommended for Quick Start)

- Docker 20.10+ and Docker Compose 2.0+
- GNU Make (for running Makefile targets)

## Quickstart for Developers

### Option 1: Docker Compose (Recommended for Quick Start)

The fastest way to get started is using Docker Compose, which sets up all services (PostgreSQL, Redis, pgAdmin, API) automatically:

```sh
# 1. Clone the repository
git clone <your-repo-url>
cd githubspeckit

# 2. Start all services (builds on first run)
make docker-up

# 3. Wait for services to be healthy (~30 seconds)
# API will be available at http://localhost:8000
# pgAdmin at http://localhost:5050 (admin@example.com / admin)
# PostgreSQL at localhost:5432 (postgres / postgres)

# 4. Run database migrations
make docker-migrate

# 5. Check API health
curl http://localhost:8000/health

# 6. View logs
make docker-logs

# 7. Stop all services
make docker-down
```

**Docker Services:**

- **API**: FastAPI application with hot-reload (port 8000)
- **PostgreSQL 15**: Primary database (port 5432)
- **Redis 7**: Cache and rate limiting (port 6379)
- **pgAdmin 4**: Database management UI (port 5050)

**Useful Docker Commands:**

```sh
make docker-build    # Rebuild containers
make docker-ps       # Show running containers
make docker-shell    # Open shell in API container
make docker-reset    # Stop, remove volumes, and restart fresh
```

### Option 2: Native Development

### 1. Clone the Repository

```sh
git clone <your-repo-url>
cd githubspeckit
```

### 2. Set Up and Install All Dependencies

Use the Makefile to create the virtual environment and install everything needed for development:

```sh
make full-dev-setup
```

This will:

- Remove any old virtual environment and caches
- Create a new `.venv`
- Install all runtime and dev dependencies
- Prepare the project for development and testing

### 3. Set Up Environment Variables

Copy the example env file and adjust as needed:

```sh
cp env.dev .env
```

### 4. Run Database Migrations (if applicable)

```sh
# Placeholder: add migration command if/when implemented
```

### 5. Run the API Server

```sh
make up
```

The server will start on the default port (see `.env` or Makefile).

### 6. Run Tests

```sh
make test
```

### 7. Generate OpenAPI Docs

```sh
make openapi-html
```

## Documentation

- **[Migration Guide to V1.0](docs/MIGRATION-TO-V1.0.md)** - Upgrade guide with breaking changes, rollback plan, troubleshooting
- **[Database Schema](docs/database-schema-v1.0.sql)** - PostgreSQL DDL (821 lines, 16 tables)
- **[Database ERD](docs/database-erd-v1.0.png)** - Entity-relationship diagram (generated with SchemaSpy)
- **[Database Indexes](docs/database-indexes-v1.0.md)** - Index strategy with 46 indexes documented
- **[Metrics Guide](docs/METRICS.md)** - Prometheus metrics documentation with query examples
- **[Logging Guide](docs/LOGGING.md)** - Structured logging with export API and PII redaction
- **[Quickstart Guide](specs/001-modern-enterprise-grade/quickstart.md)** - Detailed setup and usage scenarios

## V1.0 Features

### Implemented
- ✅ **Multi-Tenancy**: Tenant-scoped routes (`/api/v1/admin/*` for superadmin)
- ✅ **RBAC & Role Management**: 3 system roles (superadmin, tenant_admin, user) + custom roles
- ✅ **Policy Engine**: Tri-state evaluation (ALLOW/DENY/ABSTAIN) with audit trail
- ✅ **Authentication**: Argon2id password hashing, JWT tokens, token refresh
- ✅ **Email Uniqueness**: Per-tenant email constraints (FR-116)
- ✅ **Audit Trail**: FR-077 created/updated metadata on all entities
- ✅ **Observability**: OpenTelemetry tracing, Prometheus metrics, structured logging
- ✅ **Security**: OWASP ZAP scans (0 HIGH/MEDIUM/LOW vulnerabilities), RBAC enforcement
- ✅ **Admin Routes**: 8 admin endpoints for tenant/user/role/policy management
- ✅ **Database**: PostgreSQL 15+ with 46 optimized indexes, Alembic migrations

### Deferred to Phase 2
- ⏳ **Tenant-Scoped Policy Routes** (spec 017): `/api/v1/tenants/{tenant_id}/policies`
- ⏳ **Advanced Rate Limiting** (spec 018): Per-user/tenant/global rate limits with Redis
- ⏳ **Feature Flags Visibility** (spec 017): Tenant-accessible feature flag endpoints
- ⏳ **Invitation Acceptance** (spec 017): `/api/v1/invitations/{id}/accept` endpoint
- ⏳ **User Profile Details** (spec 003): Extended profile with photo upload

## Additional Commands

- `make dev` — Install dev tools (linters, test runners, etc.)
- `make full-dev-setup` — Clean, install, and test in one go
- `make env-show` — Show merged environment variables

## Notes

- All code is under `src/`.
- Tests are under `tests/`.
- Use the provided `.gitignore` to keep your repo clean.
- For more details, see [Quickstart Guide](specs/001-modern-enterprise-grade/quickstart.md)
