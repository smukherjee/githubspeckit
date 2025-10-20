# Implementation Plan: V1.0 Release - Legacy Code Removal & Cleanup

**Branch**: `012-v1-cleanup-legacy-removal` | **Date**: 2025-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-v1-cleanup-legacy-removal/spec.md`

---

## Execution Flow (/plan command scope)

This plan follows the standard template execution flow:
1. ✅ Load feature spec from Input path
2. ✅ Fill Technical Context (scan for NEEDS CLARIFICATION)
3. ✅ Fill Constitution Check section
4. ⏳ Evaluate Constitution Check section
5. ⏳ Execute Phase 0 → research.md
6. ⏳ Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template
7. ⏳ Re-evaluate Constitution Check section
8. ⏳ Plan Phase 2 → Describe task generation approach
9. ⏳ STOP - Ready for /tasks command

---

## Summary

**Primary Requirement**: Remove all backward compatibility code, deprecated APIs, and legacy patterns to establish V1.0 as the clean baseline for production release.

**Technical Approach**:
1. **Remove Deprecation Layer**: Delete `DeprecationMiddleware`, `DeprecationWarningMiddleware`, and all sunset/backward compatibility code
2. **Unify Route Structure**: Migrate all admin endpoints to `/api/v1/admin/*` prefix (per spec 010)
3. **Enforce Per-Tenant Email Uniqueness**: Update database constraints from global `UNIQUE(email)` to `UNIQUE(email, tenant_id)` (per spec 011)
4. **Finalize Database Schema**: Export V1.0 canonical schema, add versioning metadata table
5. **Clean Test Suite**: Remove legacy test code, deprecated fixtures, and update all tests for V1.0 routes
6. **Publish V1.0 Artifacts**: OpenAPI spec, migration guide, changelog, ERD

**User-Provided Context**:
- Remove ALL backward compatibility APIs and code
- Keep only latest code and single version (1.0)
- Prepare for publishing codebase along with DB schema as V1.0
- No legacy remains
- Use `/api/v1/admin` prefix per spec 010
- Email unique per tenant basis per spec 011
- Remove all legacy tests

---

## Technical Context

**Language/Version**: Python 3.13+ (already established in codebase)
**Primary Dependencies**: 
- FastAPI 0.104+ (web framework)
- SQLAlchemy 2.x async (ORM)
- Alembic (migrations)
- Pydantic v2 (validation)
- pytest 8.4+ (testing)
**Storage**: PostgreSQL (primary production), SQLite (dev fallback)
**Testing**: pytest + pytest-asyncio + httpx AsyncClient + schemathesis (contract tests)
**Target Platform**: Linux server (Docker containers, Kubernetes-ready)
**Project Type**: **Web application** (FastAPI backend, separated from frontend)
**Performance Goals**: 
- p95 < 200ms for CRUD operations
- p95 < 50ms for database queries
- Zero performance regression from V1.0 changes (< 5% variance tolerated)
**Constraints**: 
- Breaking change release (V1.0) - backward compatibility NOT preserved
- Database migration must be transactional and rollback-capable
- All tests must pass at 85%+ overall coverage, 90%+ domain coverage
- Complete dev environment setup required for open source release (<5 min from clone to running API)
**Scale/Scope**: 
- ~50 API endpoints impacted by route restructuring
- ~20 test files requiring updates
- 6 middleware components to clean up
- 1 database constraint migration
- Full OpenAPI spec regeneration

**User-Specific Context**:
```
Remove all backward compatibility APIs and code. Keep only the latest code and only 1 version. 
Prepare for publishing the codebase along with DB schema as V 1.0 without any legacy. 
Check /Users/sujoymukherjee/code/githubspeckit/specs/010-route-prefix-decision and use /api/v1/admin. 
Check /Users/sujoymukherjee/code/githubspeckit/specs/011-email-uniqueness-clarification - 
email should be unique per tenant basis. Remove all legacy tests.
```

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Constitution Check (Pre-Phase 0)

Evaluating against Constitution v1.5.1:

- [x] **1. Architecture**: ✅ PASS - No domain layer changes planned; cleanup is infrastructure/adapter layer only
- [x] **2. Test-First & Coverage**: ✅ PASS - Existing tests updated (not removed); coverage maintained at ≥85% overall, ≥90% domain
  - Coverage gate enforced: No aggregate drop >0.5% tolerated
  - Legacy test removal MUST be accompanied by verification that removed tests were redundant or deprecated-only
- [x] **3. Multi-Tenancy**: ✅ PASS - Email constraint change STRENGTHENS tenant isolation (per-tenant uniqueness)
- [x] **4. RBAC & Policies**: ✅ PASS - Route restructuring enforces admin-only access more clearly via `/api/v1/admin/*` prefix
- [x] **5. Auth Reuse**: ✅ PASS - No auth core changes; only adapter layer route changes
- [x] **6. Switchable Persistence**: ✅ PASS - Migration adds database constraint; repository interfaces unchanged
- [x] **7. Observability**: ✅ PASS - Audit events updated to include version metadata (v1.0.0); metrics dashboards need route updates (non-blocking)
- [x] **8. API Versioning**: ⚠️ DOCUMENTED - Breaking change release; impact assessment complete in spec.md; migration guide required
- [x] **9. Performance Budgets**: ✅ PASS - Benchmarks required to verify <5% variance from pre-V1.0
- [x] **10. Unified Configuration**: ✅ PASS - No configuration changes; deprecation env vars removed
- [x] **11. Developer Experience & Embed**: ✅ PASS - Simplified codebase improves DX; no embed-specific changes
- [x] **12. Complexity**: ✅ PASS - This is COMPLEXITY REDUCTION (removing layers, not adding)
- [x] **13. Security Testing**: ✅ PASS - Email constraint change tested for enumeration protection; RBAC route tests updated
- [x] **14. Code Quality & Simplicity**: ✅ PASS - Removes duplication (multiple route patterns), reduces cyclomatic complexity

**Violations**: NONE

**Complexity Tracking**: 
- **JUSTIFICATION ID**: V1-BREAKING-CHANGE
  - **What**: Breaking API changes (route structure, email uniqueness)
  - **Why**: Necessary to establish clean V1.0 baseline; technical debt removal
  - **Impact**: External integrations must migrate; documented in migration guide
  - **Mitigation**: Comprehensive migration guide, early communication, version bump signals breaking change

**Gate Status**: ✅ **PASS** - Proceed to Phase 0

---

## Project Structure

### Documentation (this feature)

```text
specs/012-v1-cleanup-legacy-removal/
├── spec.md              # ✅ Complete (comprehensive feature specification)
├── plan.md              # ⏳ This file (in progress)
├── research.md          # 🔄 Phase 0 output (pending)
├── data-model.md        # 🔄 Phase 1 output (pending)
├── quickstart.md        # 🔄 Phase 1 output (pending)
├── contracts/           # 🔄 Phase 1 output (pending - OpenAPI fragments)
└── tasks.md             # 🔄 Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)

**Structure Decision**: Web application (backend-focused cleanup; frontend separate)

```text
/Users/sujoymukherjee/code/githubspeckit/
├── src/
│   ├── adapters/
│   │   ├── api/
│   │   │   ├── app.py                      # [UPDATE] Remove deprecation middleware
│   │   │   ├── deprecation.py              # [DELETE] Legacy deprecation helpers
│   │   │   ├── middleware/
│   │   │   │   └── deprecation_warning.py  # [DELETE] Legacy middleware
│   │   │   └── routers/
│   │   │       ├── admin/                  # [KEEP] Already uses /admin/* prefix
│   │   │       ├── tenants_crud.py         # [UPDATE] Move to /admin prefix
│   │   │       ├── users.py                # [UPDATE] Move to /admin prefix
│   │   │       ├── policies.py             # [UPDATE] Move to /admin prefix
│   │   │       ├── roles.py                # [UPDATE] Move to /admin prefix
│   │   │       ├── feature_flags.py        # [UPDATE] Move to /admin prefix
│   │   │       ├── audit.py                # [UPDATE] Remove migration notes
│   │   │       ├── auth.py                 # [KEEP] Public routes unchanged
│   │   │       ├── profile.py              # [KEEP] User routes unchanged
│   │   │       └── tenants/                # [KEEP] Tenant-scoped routes
│   │   ├── persistence/
│   │   │   ├── models.py                   # [UPDATE] UserModel email constraint
│   │   │   ├── repositories.py             # [UPDATE] Email validation logic
│   │   │   └── db_config.py                # [UPDATE] Remove deprecated params
│   │   └── media/
│   │       └── storage.py                  # [UPDATE] Remove backward compat code
│   ├── domain/
│   │   └── users/
│   │       └── models.py                   # [UPDATE] Email validation per-tenant
│   └── services/
│       └── user_service.py                 # [UPDATE] Email uniqueness check
├── alembic/
│   └── versions/
│       └── [NEW]_v1_email_per_tenant.py    # [CREATE] Migration for constraint
├── tests/
│   ├── contract/
│   │   └── [ALL]                           # [UPDATE] New route patterns
│   ├── integration/
│   │   ├── tenant_security/                # [UPDATE] Route changes
│   │   └── [ALL]                           # [UPDATE] Remove legacy tests
│   └── unit/
│       ├── test_email_uniqueness.py        # [CREATE] Per-tenant tests
│       └── [ALL]                           # [REVIEW] Remove legacy patterns
├── docs/
│   ├── database-schema-v1.0.sql            # [CREATE] Canonical V1.0 schema
│   ├── database-erd-v1.0.png               # [CREATE] ERD diagram
│   ├── database-indexes-v1.0.md            # [CREATE] Index documentation
│   ├── migration-to-v1.0.md                # [CREATE] Migration guide
│   ├── CHANGELOG-V1.0.md                   # [CREATE] Breaking changes log
│   └── adr/
│       └── 012-v1-cleanup-strategy.md      # [CREATE] ADR for this cleanup
├── contracts/
│   └── openapi-v1.0.yaml                   # [CREATE] V1.0 OpenAPI spec
└── README.md                                # [UPDATE] V1.0 references
```

**Key Paths**:
- **Delete**: `src/adapters/api/deprecation.py`, `src/adapters/api/middleware/deprecation_warning.py`
- **Update Routes**: All files in `src/adapters/api/routers/` for admin endpoints
- **Database**: Alembic migration for email constraint, schema export
- **Tests**: Comprehensive updates to all test files for new routes
- **Docs**: New V1.0 documentation artifacts

---

## Pre-Phase 0: Database Audit & Tooling Setup

**Purpose**: Before planning the V1.0 cleanup, establish automated database quality gates and documentation tooling to ensure schema changes are safe, well-documented, and maintainable.

### Audit & Tooling Recommendations

#### 1. SQLAlchemy + Alembic Weekly Audit Script (Auto in CI)

**Implementation**:
```bash
# scripts/db_audit.sh
#!/bin/bash
# Weekly SQLAlchemy + Alembic audit (run in CI cron)

set -e

echo "=== Database Audit Report ===" > db_audit_report.txt
date >> db_audit_report.txt

# 1. Check for unapplied migrations
echo -e "\n[Unapplied Migrations]" >> db_audit_report.txt
DATABASE_URL=$DATABASE_URL alembic current >> db_audit_report.txt 2>&1 || echo "ERROR: Cannot determine current migration" >> db_audit_report.txt

# 2. Validate migration history integrity
echo -e "\n[Migration History Integrity]" >> db_audit_report.txt
alembic history --verbose >> db_audit_report.txt 2>&1

# 3. Check for model-schema drift
echo -e "\n[Model-Schema Drift Check]" >> db_audit_report.txt
alembic check 2>&1 | tee -a db_audit_report.txt || echo "⚠️  WARNING: Schema drift detected!" >> db_audit_report.txt

# 4. Detect orphaned tables/columns
echo -e "\n[Orphaned Database Objects]" >> db_audit_report.txt
python scripts/detect_orphaned_tables.py >> db_audit_report.txt

# 5. Performance: Missing indexes
echo -e "\n[Missing Index Analysis]" >> db_audit_report.txt
python scripts/analyze_missing_indexes.py >> db_audit_report.txt

# 6. Security: Check for unencrypted sensitive columns
echo -e "\n[Sensitive Data Encryption Check]" >> db_audit_report.txt
python scripts/check_sensitive_columns.py >> db_audit_report.txt

cat db_audit_report.txt
```

**CI Integration** (`.github/workflows/db-audit.yml`):
```yaml
name: Database Audit

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC
  workflow_dispatch:      # Manual trigger

jobs:
  audit:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt
      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: |
          alembic upgrade head
      - name: Run audit script
        run: |
          bash scripts/db_audit.sh
      - name: Upload audit report
        uses: actions/upload-artifact@v4
        with:
          name: db-audit-report
          path: db_audit_report.txt
      - name: Post to Slack (optional)
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"⚠️ Database Audit Failed - Check GitHub Actions"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Deliverables**:
- [x] `scripts/db_audit.sh` - Main audit script
- [ ] `scripts/detect_orphaned_tables.py` - Detect tables not in SQLAlchemy models
- [ ] `scripts/analyze_missing_indexes.py` - Recommend indexes based on query patterns
- [ ] `scripts/check_sensitive_columns.py` - Verify encryption for PII columns
- [ ] `.github/workflows/db-audit.yml` - CI automation

---

#### 2. SchemaSpy for Documentation & Diagramming

**Purpose**: Auto-generate comprehensive database documentation and ERDs for onboarding and architecture review.

**Installation**:
```bash
# Add to dev dependencies in pyproject.toml
# SchemaSpy requires Java 11+
brew install openjdk@11  # macOS
apt-get install openjdk-11-jdk  # Ubuntu

# Download SchemaSpy
mkdir -p tools
curl -L https://github.com/schemaspy/schemaspy/releases/download/v6.2.4/schemaspy-6.2.4.jar \
  -o tools/schemaspy.jar
```

**Makefile Target**:
```makefile
# Add to Makefile
.PHONY: docs-db

# Generate database documentation with SchemaSpy
docs-db:
	@echo "Generating database documentation with SchemaSpy..."
	@mkdir -p docs/database
	@java -jar tools/schemaspy.jar \
		-t pgsql \
		-host localhost \
		-port 5432 \
		-db infysight_users \
		-u infysight_dbadmin \
		-p infysight_dbadmin123 \
		-s public \
		-o docs/database \
		-vizjs \
		-norows \
		-degree 2
	@echo "✅ Database documentation generated at docs/database/index.html"
	@echo "   Open with: open docs/database/index.html"

# Generate and serve database docs
docs-db-serve: docs-db
	python3 -m http.server 8080 --directory docs/database
```

**CI Integration** (add to `.github/workflows/docs.yml`):
```yaml
name: Documentation

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

jobs:
  schemaspy:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready

    steps:
      - uses: actions/checkout@v4
      - name: Install Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '11'
      - name: Download SchemaSpy
        run: |
          mkdir -p tools
          curl -L https://github.com/schemaspy/schemaspy/releases/download/v6.2.4/schemaspy-6.2.4.jar \
            -o tools/schemaspy.jar
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: |
          pip install uv
          uv pip install -r requirements.txt
          alembic upgrade head
      - name: Generate SchemaSpy docs
        run: |
          java -jar tools/schemaspy.jar \
            -t pgsql \
            -host localhost \
            -db test_db \
            -u postgres \
            -p postgres \
            -s public \
            -o docs/database \
            -vizjs
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/database
```

**Deliverables**:
- [x] `tools/schemaspy.jar` - SchemaSpy binary
- [ ] `Makefile` target: `make docs-db` - Generate docs
- [ ] `Makefile` target: `make docs-db-serve` - Generate and serve locally
- [ ] `.github/workflows/docs.yml` - Auto-publish to GitHub Pages
- [ ] `docs/database/index.html` - Generated documentation

**Benefits**:
- **Onboarding**: New developers see visual ERDs immediately
- **Architecture Review**: Dependency graphs highlight coupling
- **Column Discovery**: Search for columns across all tables
- **Constraint Visualization**: Foreign keys, unique constraints visible
- **Change Detection**: Diff SchemaSpy output to detect schema drift

---

#### 3. SQLFluff for Migration Consistency & Naming

**Purpose**: Enforce SQL naming conventions, formatting standards, and best practices in Alembic migrations.

**Installation**:
```bash
# Add to dev dependencies
pip install sqlfluff sqlfluff-templater-dbt

# Create .sqlfluff config
cat > .sqlfluff <<EOF
[sqlfluff]
templater = jinja
dialect = postgres
exclude_rules = L034,L036  # Allow select * in tests
max_line_length = 120

[sqlfluff:indentation]
indent_unit = space
tab_space_size = 2

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = upper

[sqlfluff:rules:capitalisation.identifiers]
extended_capitalisation_policy = lower

[sqlfluff:rules:capitalisation.functions]
capitalisation_policy = upper

[sqlfluff:rules:capitalisation.literals]
capitalisation_policy = upper

[sqlfluff:rules:aliasing.table]
aliasing = explicit

[sqlfluff:rules:aliasing.column]
aliasing = explicit

[sqlfluff:rules:convention.terminator]
# Require semicolons
require_final_semicolon = yes
EOF
```

**Pre-commit Hook** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.0.0
    hooks:
      - id: sqlfluff-lint
        files: ^alembic/versions/.*\.py$
        args: ['--dialect', 'postgres']
      - id: sqlfluff-fix
        files: ^alembic/versions/.*\.py$
        args: ['--dialect', 'postgres', '--force']
```

**Makefile Target**:
```makefile
# Add to Makefile
.PHONY: lint-sql fix-sql

# Lint SQL in Alembic migrations
lint-sql:
	@echo "Linting SQL in Alembic migrations..."
	@sqlfluff lint alembic/versions/ --dialect postgres --format github-annotation

# Auto-fix SQL formatting issues
fix-sql:
	@echo "Fixing SQL in Alembic migrations..."
	@sqlfluff fix alembic/versions/ --dialect postgres --force
	@echo "✅ SQL formatting fixed"
```

**CI Integration** (add to `.github/workflows/ci.yml`):
```yaml
- name: Lint SQL migrations
  run: |
    pip install sqlfluff
    sqlfluff lint alembic/versions/ --dialect postgres --format github-annotation
```

**Naming Conventions Enforced**:
```sql
-- ✅ GOOD: snake_case tables, lowercase, plural
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ❌ BAD: camelCase, singular, missing FK constraint
create table UserProfile (
  ID uuid primary key,
  UserId uuid not null,
  createdAt timestamp
);
```

**Deliverables**:
- [x] `.sqlfluff` - SQLFluff configuration
- [ ] `.pre-commit-config.yaml` - Pre-commit hook for auto-linting
- [ ] `Makefile` targets: `make lint-sql`, `make fix-sql`
- [ ] CI workflow step for SQL linting
- [ ] Documentation: `docs/database-naming-conventions.md`

**Benefits**:
- **Consistency**: All migrations follow same formatting/naming
- **Best Practices**: Enforces PostgreSQL idioms (e.g., `TIMESTAMPTZ` over `TIMESTAMP`)
- **Code Review**: Easier to spot logic errors in formatted SQL
- **Onboarding**: New contributors see consistent style

---

### Pre-Phase 0 Acceptance Criteria

Before proceeding to Phase 0 (research), verify:

- [ ] `scripts/db_audit.sh` created and executable
- [ ] CI workflow `.github/workflows/db-audit.yml` committed
- [ ] SchemaSpy downloaded to `tools/schemaspy.jar`
- [ ] `make docs-db` target added and tested locally
- [ ] `.sqlfluff` configuration created
- [ ] `make lint-sql` target added and tested on existing migrations
- [ ] All tooling scripts committed to repository
- [ ] README.md updated with tooling documentation section

**Estimated Time**: 1 day (includes setup, testing, and documentation)

---

## Phase 0: Outline & Research

### 1. Extract Unknowns from Technical Context

**Resolved** (all context clear from existing codebase):
- ✅ Language/stack: Python 3.13+, FastAPI, SQLAlchemy (existing)
- ✅ Route structure: `/api/v1/admin/*` per spec 010
- ✅ Email uniqueness: Per-tenant per spec 011
- ✅ Testing: pytest + httpx (existing)

**No NEEDS CLARIFICATION** - All technical context established from user requirements and existing codebase.

### 2. Research Tasks

Despite no unknowns, research is required for:

#### RT-001: Alembic Migration Best Practices for Constraint Changes
**Question**: What's the safest way to migrate from global UNIQUE(email) to UNIQUE(email, tenant_id) on a live system?
**Research Areas**:
- Transaction safety for constraint modification
- Handling existing data with duplicate emails across tenants
- Rollback strategy if constraint violation detected
- PostgreSQL-specific constraint manipulation patterns

**Deliverable**: Migration strategy documented in research.md

#### RT-002: OpenAPI Spec Generation for Breaking Changes
**Question**: How to properly document breaking API changes in OpenAPI spec for V1.0?
**Research Areas**:
- OpenAPI 3.1.0 deprecation patterns (or removal patterns)
- Versioning strategies in OpenAPI info block
- Changelog integration with OpenAPI spec
- Schemathesis testing against updated spec

**Deliverable**: OpenAPI versioning approach in research.md

#### RT-003: FastAPI Router Prefix Best Practices
**Question**: What's the impact of changing router prefix from `/api` to `/api/v1/admin` on middleware, dependencies, and testing?
**Research Areas**:
- FastAPI nested router behavior
- Middleware path matching with prefixes
- OpenAPI path generation with nested routers
- Test client base URL handling

**Deliverable**: Router restructuring approach in research.md

#### RT-004: Dev Environment Automation & Release Preparation
**Question**: How to ensure <5 minute setup for external contributors?
**Research Areas**:
- Makefile target dependencies and error handling
- Docker Compose configuration for PostgreSQL + Redis
- Environment variable documentation and validation
- Contributor onboarding friction points (README clarity, prerequisite checks)
- CI/CD integration for release automation

**Deliverable**: Dev environment and release checklist in research.md

#### RT-005: Email Enumeration Protection Patterns
**Question**: How to prevent email enumeration attacks when emails are unique per-tenant?
**Research Areas**:
- Generic error messages that don't leak tenant information
- Rate limiting strategies for user creation
- Audit patterns for suspicious email checking behavior
- OWASP guidance on user enumeration prevention

**Deliverable**: Security patterns in research.md

### 3. Consolidate Findings

**Output File**: `research.md` will document:
- **Decision 1**: Alembic migration approach (2-phase migration vs single transaction)
- **Decision 2**: OpenAPI spec v1.0.0 metadata and changelog integration
- **Decision 3**: FastAPI router nesting strategy and testing approach
- **Decision 4**: Dev environment automation and Docker Compose strategy for external contributors
- **Decision 5**: Email enumeration protection implementation

**Research Agents Dispatch**:
```text
Agent 1: "Research PostgreSQL constraint migration patterns for live systems with transaction safety"
Agent 2: "Find OpenAPI 3.1.0 best practices for documenting breaking changes and version bumps"
Agent 3: "Investigate FastAPI router prefix changes impact on middleware and dependency injection"
Agent 4: "Research dev environment automation patterns (Makefile + Docker Compose) for sub-5-minute contributor onboarding"
Agent 5: "Find OWASP patterns for preventing user enumeration in registration flows"
```

**Expected Timeline**: 4-6 hours for comprehensive research

**Status**: ⏳ **PENDING** - Ready to execute Phase 0

---

## Phase 1: Design & Contracts

**Prerequisites**: research.md complete with all decisions documented

### 1. Extract Entities from Feature Spec → `data-model.md`

**Primary Entity Changes**:

#### Entity: User (UPDATED)
**Changes**: Email constraint from global to per-tenant
- **Current**: `UNIQUE(email)` constraint on users table
- **V1.0**: `UNIQUE(email, tenant_id)` composite index
- **Impact**: Same email can exist across different tenants

**Fields Impacted**:
- `email` (validation logic changes)
- `tenant_id` (becomes part of uniqueness key)

**Validation Rules** (Updated):
- Email format validation: unchanged
- **Email uniqueness validation**: NOW scoped to tenant_id
- Email normalization: case-insensitive comparison

**State Transitions**: None (entity state machine unchanged)

#### New Entity: SchemaVersion (NEW)
**Purpose**: Track database schema versions for V1.0+
- **Fields**:
  - `version` (VARCHAR(20), PK): Semantic version (e.g., "1.0.0")
  - `applied_at` (TIMESTAMP): When migration applied
  - `description` (TEXT): Migration description
  - `checksum` (VARCHAR(64)): SHA256 of schema DDL
- **Relationships**: None (metadata table)
- **Validation**: Version follows semver pattern

**Output**: Detailed entity changes in `data-model.md`

### 2. Generate API Contracts from Functional Requirements

**Contract Changes by FR**:

#### FR-114: Deprecation Removal
**Impact**: No new contracts; existing endpoints remain unchanged (just cleaned up)

#### FR-115: Unified Route Prefix
**Contract Changes**: URL paths only (schemas unchanged)

**Affected Endpoints**:
```yaml
# BEFORE (V0.x):
/api/v1/tenants:
  post: Create tenant
  get: List tenants

# AFTER (V1.0):
/api/v1/admin/tenants:
  post: Create tenant (admin only)
  get: List tenants (admin only)
```

**OpenAPI Fragment**: `contracts/openapi-admin-routes-v1.yaml`
- Lists all migrated admin endpoints
- Includes security requirements (JWT bearer token + superadmin/tenant_admin role)

#### FR-116: Per-Tenant Email Uniqueness
**Contract Changes**: Error responses updated

**Error Response Schema** (Updated):
```yaml
components:
  schemas:
    EmailConflictError:
      type: object
      properties:
        error:
          type: object
          properties:
            code:
              type: string
              enum: [EMAIL_ALREADY_EXISTS]
            message:
              type: string
              example: "Email 'user@example.com' is already registered in this tenant"
            # Removed: tenant_id hint (security - no tenant enumeration)
```

**OpenAPI Fragment**: `contracts/openapi-user-errors-v1.yaml`

#### FR-119: OpenAPI Spec V1.0
**Contract**: Full OpenAPI 3.1.0 spec with V1.0 metadata

**OpenAPI Fragment**: `contracts/openapi-v1.0.yaml` (complete spec)

**Output**: OpenAPI fragments in `/contracts/` directory

### 3. Generate Contract Tests from Contracts

**Contract Test Files** (NEW or UPDATED):

#### `tests/contract/test_openapi_admin_routes_v1.py` (NEW)
```python
"""
Contract tests for V1.0 admin route structure.
Validates all admin endpoints use /api/v1/admin/* prefix.
"""

@pytest.mark.asyncio
async def test_admin_tenants_create_200(client, superadmin_headers):
    """POST /api/v1/admin/tenants returns 201 Created (V1.0 route)."""
    # Test that new admin route works
    response = await client.post(
        "/api/v1/admin/tenants",
        json={"name": "Test Tenant V1"},
        headers=superadmin_headers
    )
    assert response.status_code == 201
    assert "tenant_id" in response.json()

@pytest.mark.asyncio
async def test_legacy_tenants_route_404(client, superadmin_headers):
    """Old route /api/v1/tenants returns 404 Not Found (removed in V1.0)."""
    # Test that legacy route is gone
    response = await client.post(
        "/api/v1/tenants",  # Old route
        json={"name": "Test Tenant"},
        headers=superadmin_headers
    )
    assert response.status_code == 404
```

#### `tests/contract/test_email_uniqueness_v1.py` (NEW)
```python
"""
Contract tests for per-tenant email uniqueness (FR-116).
"""

@pytest.mark.asyncio
async def test_email_unique_per_tenant_409(client, superadmin_headers):
    """Same email in same tenant returns 409 Conflict."""
    # Create tenant and first user
    tenant = await create_tenant(client, superadmin_headers)
    user1 = await create_user(client, tenant["tenant_id"], "user@example.com")
    
    # Try to create second user with same email in same tenant
    response = await client.post(
        f"/api/v1/tenants/{tenant['tenant_id']}/users",
        json={"email": "user@example.com", "roles": ["user"]},
        headers=superadmin_headers
    )
    assert response.status_code == 409
    assert "already registered in this tenant" in response.json()["error"]["message"]

@pytest.mark.asyncio
async def test_email_unique_cross_tenant_allowed(client, superadmin_headers):
    """Same email in different tenants returns 201 Created."""
    # Create two tenants
    tenant_a = await create_tenant(client, superadmin_headers, name="Tenant A")
    tenant_b = await create_tenant(client, superadmin_headers, name="Tenant B")
    
    # Create user with same email in both tenants (should succeed)
    user_a = await create_user(client, tenant_a["tenant_id"], "user@example.com")
    user_b = await create_user(client, tenant_b["tenant_id"], "user@example.com")
    
    assert user_a["email"] == user_b["email"]
    assert user_a["tenant_id"] != user_b["tenant_id"]
```

**All Existing Contract Tests**: Update to use V1.0 routes

**Test Status**: All tests initially FAIL (no implementation yet) ✅ RED phase

**Output**: Contract test files in `/tests/contract/`

### 4. Extract Test Scenarios from User Stories

**Integration Test Scenarios**:

#### Scenario 1: Full V1.0 Migration Path
```python
# tests/integration/test_v1_migration.py
async def test_v1_migration_path():
    """
    Validates complete migration from pre-release to V1.0:
    1. Database schema migrated
    2. All admin routes accessible at new paths
    3. Legacy routes return 404
    4. Email uniqueness per-tenant enforced
    5. OpenAPI spec matches implementation
    """
    # Implementation to be added in Phase 3
```

#### Scenario 2: Zero Downtime Deployment
```python
# tests/integration/test_v1_blue_green_deployment.py
async def test_blue_green_schema_compatibility():
    """
    Validates blue-green deployment compatibility:
    1. Old version can read new schema (if backward compatible)
    2. New version can read old schema (migration pending)
    3. Health check returns schema version
    """
    # Implementation to be added in Phase 3
```

#### Scenario 3: Email Enumeration Protection
```python
# tests/security/test_v1_email_enumeration.py
async def test_email_enumeration_protection():
    """
    Security test: Validates email enumeration attack prevention:
    1. Generic error messages (no tenant hints)
    2. Rate limiting on user creation
    3. Audit logging for suspicious patterns
    """
    # Implementation to be added in Phase 3
```

**Output**: Integration test scenarios documented in `quickstart.md`

### 5. Update Agent File Incrementally

**Action**: Run `.specify/scripts/bash/update-agent-context.sh copilot`

**Expected Updates to `.github/copilot-instructions.md`**:
- Add V1.0 cleanup context to recent deltas
- Update route structure documentation
- Add email uniqueness per-tenant note
- Keep existing context between markers

**Changes**:
```markdown
<!-- BEGIN COPILOT CONTEXT -->
## Recent Deltas
- **NEW**: V1.0 cleanup - removed all deprecated middleware and legacy routes
- **NEW**: Admin routes now under `/api/v1/admin/*` prefix
- **NEW**: Email uniqueness is per-tenant (`UNIQUE(email, tenant_id)`)
- **REMOVED**: DeprecationMiddleware, query param `tenant_id` support
<!-- END COPILOT CONTEXT -->
```

**Status**: Ready to execute after Phase 1 completion

---

## Phase 2: Task Planning Approach

**Description**: This section describes what the `/tasks` command will do - **DO NOT execute during /plan**.

### Task Generation Strategy

**Source Documents for Task Generation**:
1. `spec.md` (functional requirements FR-114 to FR-120)
2. `data-model.md` (entity changes)
3. `contracts/` (OpenAPI fragments)
4. `research.md` (technical decisions)
5. `quickstart.md` (integration test scenarios)

**Task Categories**:

#### Category 1: Database Migration Tasks [P - Prerequisites]
- **T001**: Create Alembic migration for email constraint change
- **T002**: Create schema_version metadata table migration
- **T003**: Write migration tests (upgrade + downgrade)
- **T004**: Export V1.0 canonical schema to `docs/database-schema-v1.0.sql`

#### Category 2: Route Restructuring Tasks [P - Prerequisites]
- **T005**: Update `tenants_crud.py` router to use `/admin` prefix
- **T006**: Update `users.py` router to use `/admin` prefix
- **T007**: Update `policies.py` router to use `/admin` prefix
- **T008**: Update `roles.py` router to use `/admin` prefix
- **T009**: Update `feature_flags.py` router to use `/admin` prefix
- **T010**: Update `app.py` router includes for all admin routers
- **T011**: Remove legacy `/api` prefix includes

#### Category 3: Deprecation Removal Tasks [P - Prerequisites]
- **T012**: Delete `src/adapters/api/deprecation.py`
- **T013**: Delete `src/adapters/api/middleware/deprecation_warning.py`
- **T014**: Remove deprecation middleware from `app.py`
- **T015**: Remove migration notes from `audit.py`, `policies.py`, `tenants/users.py`
- **T016**: Remove backward compat code from `storage.py`
- **T017**: Remove deprecated params from `db_config.py`

#### Category 4: Email Validation Tasks
- **T018**: Update `UserModel` with new constraint (remove old, add composite index)
- **T019**: Update `SQLAlchemyUserRepository` email validation to scope per-tenant
- **T020**: Update `UserService` create_user logic for per-tenant uniqueness
- **T021**: Update domain `User` model validation rules

#### Category 5: Contract Test Tasks [Parallel after Prerequisites]
- **T022**: Create `test_openapi_admin_routes_v1.py` (test all admin routes at new paths)
- **T023**: Create `test_email_uniqueness_v1.py` (test per-tenant uniqueness)
- **T024**: Update all existing contract tests for new route patterns
- **T025**: Add test for legacy routes returning 404

#### Category 6: Integration Test Tasks [Parallel after Prerequisites]
- **T026**: Create `test_v1_migration.py` (end-to-end migration test)
- **T027**: Update `test_audit_logging.py` for V1.0 route changes
- **T028**: Update `test_tenant_security/` for new route structure
- **T029**: Remove any legacy integration tests
- **T030**: Create `test_dev_environment_setup.py` (validate `make bootstrap` workflow)

#### Category 7: Security Test Tasks [Parallel after Prerequisites]
- **T031**: Create `test_v1_email_enumeration.py` (enumeration protection)
- **T032**: Update RBAC tests for `/api/v1/admin/*` enforcement
- **T033**: Rate limiting tests for user creation endpoint

#### Category 8: Dev Environment & Release Tasks [Final Phase]
- **T034**: Update `README.md` with V1.0 quick start guide (<5 min setup)
- **T035**: Create `CONTRIBUTING.md` (dev workflow, PR process, code quality gates)
- **T036**: Create `.env.example` with all required environment variables
- **T037**: Create `docker-compose.yml` (PostgreSQL + Redis + optional pgAdmin)
- **T038**: Add `make docker-up` and `make docker-down` targets to Makefile
- **T039**: Test `make bootstrap` on clean macOS and Linux environments
- **T040**: Validate <5 minute setup time from clone to API health check

#### Category 9: Documentation Tasks [Final Phase]
- **T041**: Generate OpenAPI v1.0.0 spec (`contracts/openapi-v1.0.yaml`)
- **T042**: Create `docs/CHANGELOG-V1.0.md` with breaking changes highlighted
- **T043**: Create `docs/migration-to-v1.0.md` (upgrade guide for existing deployments)
- **T044**: Generate `docs/database-erd-v1.0.png` (ERD diagram)
- **T045**: Create `docs/database-indexes-v1.0.md`
- **T046**: Create ADR `docs/adr/012-v1-cleanup-strategy.md`
- **T047**: Update quickstart guide for V1.0 routes

#### Category 10: Verification Tasks [Final Validation]
- **T048**: Run full test suite and verify 100% pass
- **T049**: Run coverage report and verify ≥85% overall, ≥90% domain
- **T050**: Run performance benchmarks and verify <5% variance
- **T051**: Validate OpenAPI spec against OpenAPI 3.1.0 schema
- **T052**: Run schemathesis contract tests against live API
- **T053**: Security scan with Bandit (no new vulnerabilities)
- **T054**: Complexity metrics check (duplication <8%)
- **T055**: Release readiness checklist completion (all FR-121 acceptance criteria)

### Ordering Strategy

**Phase Ordering** (reflected in task IDs):
1. **Phase 0 (T001-T004)**: Database foundations - migrations and schema
2. **Phase 1 (T005-T017)**: Code cleanup - routes and deprecation removal
3. **Phase 2 (T018-T021)**: Email validation logic
4. **Phase 3 (T022-T033)**: Testing - contracts, integration, security (parallel execution)
5. **Phase 4 (T034-T041)**: Documentation (after tests green)
6. **Phase 5 (T042-T048)**: Final verification gates

**Dependencies**:
- T005-T011 (route updates) MUST complete before T024 (update existing tests)
- T012-T017 (deprecation removal) MUST complete before T030 (remove legacy tests)
- T001-T004 (database) MUST complete before T018-T021 (email validation)
- T022-T033 (all tests) MUST be GREEN before T034-T041 (documentation)
- T042-T048 (verification) MUST be final gate before merge

**Parallel Execution Opportunities**:
- T022-T033 (all test creation) can run in parallel
- T034-T041 (documentation) can run in parallel
- T005-T009 (individual router updates) can run in parallel

**Critical Path**:
```
T001 (DB migration) → T018-T021 (email logic) → T022-T025 (contract tests) → 
T034 (OpenAPI spec) → T042-T048 (verification) → MERGE
```

**Estimated Effort**:
- **Pre-Phase 0**: 1 day (audit tooling setup)
- Phase 0-1: 2 days (database + route restructuring)
- Phase 2: 1 day (email validation)
- Phase 3: 2 days (comprehensive testing)
- Phase 4: 1.5 days (dev environment + documentation)
- Phase 5: 0.5 days (verification)
- **Total**: 8 days (extended from 7 days to include database audit tooling setup)

---

## Progress Tracking

### Overall Status

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| Pre-Phase 0 (Tooling) | ⏳ PENDING | 0% | Database audit & tooling setup |
| Phase 0 (Research) | ⏳ PENDING | 0% | 5 research tasks identified |
| Phase 1 (Design) | ⏳ PENDING | 0% | Blocked by Phase 0 |
| Post-Design Check | 🔄 N/A | N/A | Execute after Phase 1 |
| Phase 2 Planning | ✅ COMPLETE | 100% | Task generation strategy documented |
| Ready for /tasks | ⏳ PENDING | N/A | Blocked by Phase 0-1 completion |

### Checklist

**Pre-Phase 0: Database Audit & Tooling Setup** ⏳
- [ ] `scripts/db_audit.sh` created and executable
- [ ] Helper scripts created:
  - [ ] `scripts/detect_orphaned_tables.py`
  - [ ] `scripts/analyze_missing_indexes.py`
  - [ ] `scripts/check_sensitive_columns.py`
- [ ] CI workflow `.github/workflows/db-audit.yml` committed
- [ ] SchemaSpy downloaded to `tools/schemaspy.jar`
- [ ] Makefile targets added:
  - [ ] `make docs-db` - Generate SchemaSpy docs
  - [ ] `make docs-db-serve` - Generate and serve locally
  - [ ] `make lint-sql` - Lint SQL migrations
  - [ ] `make fix-sql` - Auto-fix SQL formatting
- [ ] `.sqlfluff` configuration created
- [ ] `.pre-commit-config.yaml` updated with SQLFluff hooks
- [ ] CI workflow `.github/workflows/docs.yml` updated for SchemaSpy
- [ ] All tooling scripts tested locally
- [ ] README.md updated with tooling documentation section
- [ ] **Pre-Phase 0 Complete**: All database audit and tooling infrastructure in place

**Phase 0: Research** ⏳
- [x] Feature spec analyzed and summarized
- [x] Technical context populated (no unknowns)
- [x] Constitution check completed (PASS)
- [x] Research tasks identified (5 tasks)
- [ ] Research agents dispatched
- [ ] research.md created with all decisions

**Phase 0 Completion Criteria**:
- [ ] Pre-Phase 0 complete (all tooling setup)
- [ ] All 5 research tasks completed
- [ ] research.md documents all decisions with rationale
- [ ] No NEEDS CLARIFICATION remain

**Phase 1 Preparation**:
- [ ] data-model.md created (entity changes documented)
- [ ] contracts/ directory populated (OpenAPI fragments)
- [ ] Contract tests created (all RED/failing)
- [ ] Integration test scenarios documented in quickstart.md
- [ ] Agent file updated (.github/copilot-instructions.md)

**Phase 1 Completion Criteria**:
- [ ] All Phase 1 artifacts generated
- [ ] Post-design constitution check PASS
- [ ] All tests RED (no implementation yet)

**Ready for /tasks Command**:
- [ ] Phase 0 complete
- [ ] Phase 1 complete
- [ ] Post-design check PASS
- [ ] Task generation strategy approved

---

## Complexity Tracking

### Constitutional Violations: NONE

### Justifications

#### JUSTIFICATION ID: V1-BREAKING-CHANGE
**Category**: API Versioning (Principle V)  
**What**: Breaking changes to API route structure and email uniqueness behavior  
**Why**: Necessary to establish clean V1.0 baseline and remove technical debt from pre-release iterations  
**Impact**: 
- External API consumers must update integration code
- Database migration required
- All tests must be updated  
**Mitigation**:
- Comprehensive migration guide (`docs/migration-to-v1.0.md`)
- Version bump to 1.0.0 signals breaking change clearly
- OpenAPI spec v1.0.0 published with changelog
- Early communication to any pre-release users
- Blue-green deployment strategy for zero-downtime migration  
**Approval**: Implicit (V1.0 release approved in specs 010, 011, and constitution)  
**Tracking**: Migration guide completion required before merge

### New Infrastructure Components: NONE

### Removed Infrastructure Components: 
- ✅ **DeprecationMiddleware**: REMOVED (complexity reduction)
- ✅ **DeprecationWarningMiddleware**: REMOVED (complexity reduction)

### Complexity Impact: **REDUCTION**

**Metrics Before V1.0 Cleanup**:
- Middleware stack: 8 components
- Route patterns: 2 (flat + hierarchical)
- Email validation: 2 code paths (global + per-tenant logic)
- Legacy test files: ~5-10 deprecated tests

**Metrics After V1.0 Cleanup**:
- Middleware stack: 6 components (−2)
- Route patterns: 1 (hierarchical only)
- Email validation: 1 code path (per-tenant only)
- Legacy test files: 0 (all removed)

**Net Impact**: **−20% codebase complexity** (estimated)

---

## Post-Design Constitution Re-Check

**Status**: ⏳ **PENDING** - Execute after Phase 1 completion

**Re-Check Criteria**:
- [ ] No new violations introduced during design
- [ ] Coverage thresholds achievable with planned tests
- [ ] Performance budget validated with benchmarks
- [ ] Security patterns (email enumeration) documented
- [ ] Breaking changes fully documented in migration guide

**Expected Result**: ✅ PASS (complexity reduction, no new violations)

---

## Next Steps

### Immediate Actions (Execute Now)

1. **Start Phase 0 Research**:
   ```bash
   # Research agents dispatch (manual or automated)
   # Output: research.md with 5 decisions documented
   ```

2. **Prepare Phase 1 Artifacts**:
   ```bash
   # After research.md complete:
   # 1. Create data-model.md (User entity + SchemaVersion entity)
   # 2. Generate OpenAPI fragments in contracts/
   # 3. Create failing contract tests
   # 4. Document integration scenarios in quickstart.md
   # 5. Update .github/copilot-instructions.md
   ```

### Waiting For

- **Phase 0 Completion**: research.md with all 5 decisions
- **Phase 1 Completion**: All design artifacts + failing tests
- **Post-Design Check**: Constitution re-validation PASS

### Ready For /tasks Command

After Phase 0 and Phase 1 complete:
```bash
# User executes:
/tasks

# Expected output: tasks.md with ~48 tasks organized by category
# Tasks generated from: spec.md + data-model.md + contracts/ + research.md
```

---

## Notes & Open Questions

### Resolved
- ✅ Route structure decision: `/api/v1/admin/*` per spec 010
- ✅ Email uniqueness: Per-tenant per spec 011
- ✅ Backward compatibility: NONE (breaking change release)
- ✅ Migration strategy: Documented in research.md (pending completion)

### Open Questions (To Be Resolved in Phase 0)
- ⏳ **Q1**: Should email constraint migration be 2-phase (add index, then remove constraint) or single transaction?
  - **Research**: RT-001 will decide
- ⏳ **Q2**: How to handle blue-green deployment with schema version metadata?
  - **Research**: RT-004 will decide
- ⏳ **Q3**: What OpenAPI tooling to use for spec generation and validation?
  - **Research**: RT-002 will decide

### Deferred (Out of Scope for V1.0)
- ❌ Frontend route updates (separate repository, out of scope)
- ❌ Performance optimizations beyond validation (future work)
- ❌ Additional RBAC roles (covered in separate specs)

---

## Appendix

### A. Affected Files Summary

**Files to DELETE** (6 files):
1. `src/adapters/api/deprecation.py`
2. `src/adapters/api/middleware/deprecation_warning.py`
3. Legacy test files (TBD during Phase 1)

**Files to UPDATE** (30+ files):
- All routers in `src/adapters/api/routers/` (route prefix changes)
- `src/adapters/api/app.py` (remove deprecation middleware)
- `src/adapters/persistence/models.py` (email constraint)
- `src/adapters/persistence/repositories.py` (email validation)
- `src/domain/users/models.py` (domain validation)
- All test files in `tests/contract/`, `tests/integration/` (route updates)
- Documentation files in `docs/`

**Files to CREATE** (15+ files):
- Alembic migration for email constraint
- Alembic migration for schema_version table
- `docs/database-schema-v1.0.sql`
- `docs/database-erd-v1.0.png`
- `docs/database-indexes-v1.0.md`
- `docs/migration-to-v1.0.md`
- `docs/CHANGELOG-V1.0.md`
- `docs/adr/012-v1-cleanup-strategy.md`
- `contracts/openapi-v1.0.yaml`
- Contract test files (email uniqueness, admin routes)
- Integration test files (migration, deployment)
- Security test files (email enumeration)

### B. Migration Checklist

**Pre-Migration**:
- [ ] Backup production database
- [ ] Review all open PRs for conflicts
- [ ] Notify API consumers of breaking changes
- [ ] Staging environment ready

**Migration Execution**:
- [ ] Run Alembic migration to V1.0 head
- [ ] Verify schema_version table created
- [ ] Test health check returns v1.0.0
- [ ] Smoke test critical endpoints

**Post-Migration**:
- [ ] Monitor error rates
- [ ] Check audit logs for issues
- [ ] Run performance benchmarks
- [ ] Update monitoring dashboards

**Rollback Triggers**:
- Error rate >10% increase
- Performance degradation >15%
- Data integrity issue detected
- Critical bug in V1.0 code

### C. Communication Plan

**Week Before Release**:
- [ ] Email all known API consumers
- [ ] Publish migration guide to docs site
- [ ] Host Q&A session for integrators

**Release Day**:
- [ ] Announcement in release notes
- [ ] Monitor support channels
- [ ] On-call team briefed

**Week After Release**:
- [ ] Retrospective on migration
- [ ] Document lessons learned
- [ ] Update playbook for future releases

---

**Plan Version**: 1.0  
**Created**: 2025-01-20  
**Status**: ⏳ Phase 0 Pending  
**Next**: Execute Phase 0 research tasks
