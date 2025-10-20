# Pre-Phase 0: Database Audit & Tooling Setup - Summary

**Created**: 2025-01-20  
**Feature**: 012-v1-cleanup-legacy-removal  
**Purpose**: Establish database quality gates and documentation tooling before V1.0 cleanup

---

## Overview

Before proceeding with V1.0 cleanup and legacy code removal, we've added a **Pre-Phase 0** to establish automated database audit tooling, documentation generation, and SQL linting infrastructure. This ensures all schema changes during V1.0 cleanup are safe, well-documented, and maintainable.

---

## Three Key Tooling Additions

### 1. ✅ SQLAlchemy + Alembic Weekly Audit Script (Auto in CI)

**Purpose**: Detect schema drift, missing indexes, orphaned tables, and security issues automatically.

**Deliverables**:
- `scripts/db_audit.sh` - Main audit orchestration script
- `scripts/detect_orphaned_tables.py` - Find tables not mapped in SQLAlchemy models
- `scripts/analyze_missing_indexes.py` - Recommend indexes based on query patterns
- `scripts/check_sensitive_columns.py` - Verify encryption for PII columns
- `.github/workflows/db-audit.yml` - Weekly CI cron job (every Monday 9 AM UTC)

**Benefits**:
- **Proactive Detection**: Catch schema issues before they reach production
- **Performance Monitoring**: Identify missing indexes that slow queries
- **Security Auditing**: Ensure sensitive data is properly encrypted
- **Model-Schema Sync**: Detect when models drift from actual database schema

**CI Integration**: Runs weekly via GitHub Actions cron, uploads audit report as artifact, posts to Slack on failure.

---

### 2. ✅ SchemaSpy for Documentation & Diagramming

**Purpose**: Auto-generate comprehensive database documentation and ERDs for onboarding and architecture review.

**Deliverables**:
- `tools/schemaspy.jar` - SchemaSpy binary (downloaded)
- Makefile targets:
  - `make docs-db` - Generate SchemaSpy documentation
  - `make docs-db-serve` - Generate and serve locally on port 8080
- `.github/workflows/docs.yml` - Auto-publish to GitHub Pages on push to main/develop
- `docs/database/index.html` - Generated documentation (visualized ERDs, table relationships, constraints)

**Benefits**:
- **Onboarding**: New developers see visual ERDs immediately
- **Architecture Review**: Dependency graphs highlight coupling between tables
- **Column Discovery**: Search for columns across all tables (e.g., "find all tables with `tenant_id`")
- **Constraint Visualization**: Foreign keys, unique constraints, indexes visible
- **Change Detection**: Diff SchemaSpy output to detect schema drift over time

**Usage**:
```bash
# Generate database docs locally
make docs-db

# Serve and view in browser
make docs-db-serve
# Then open http://localhost:8080 in browser
```

**CI Integration**: Automatically regenerated on every push to main/develop, published to GitHub Pages.

---

### 3. ✅ SQLFluff for Migration Consistency & Naming

**Purpose**: Enforce SQL naming conventions, formatting standards, and best practices in Alembic migrations.

**Deliverables**:
- `.sqlfluff` - SQLFluff configuration (PostgreSQL dialect, naming conventions, formatting rules)
- `.pre-commit-config.yaml` - Pre-commit hook for auto-linting SQL in migrations
- Makefile targets:
  - `make lint-sql` - Lint SQL in `alembic/versions/`
  - `make fix-sql` - Auto-fix SQL formatting issues
- CI workflow step in `.github/workflows/ci.yml` - Lint SQL on every PR

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

**Benefits**:
- **Consistency**: All migrations follow same formatting/naming (enforced in pre-commit)
- **Best Practices**: Enforces PostgreSQL idioms (e.g., `TIMESTAMPTZ` over `TIMESTAMP`)
- **Code Review**: Easier to spot logic errors in well-formatted SQL
- **Onboarding**: New contributors see consistent style, learn conventions quickly

**Usage**:
```bash
# Lint SQL migrations
make lint-sql

# Auto-fix formatting issues
make fix-sql
```

**CI Integration**: Runs on every PR, fails build if SQL doesn't meet standards.

---

## Pre-Phase 0 Acceptance Criteria

Before proceeding to Phase 0 (research), verify:

- [ ] `scripts/db_audit.sh` created and executable
- [ ] Helper scripts created (detect_orphaned_tables.py, analyze_missing_indexes.py, check_sensitive_columns.py)
- [ ] CI workflow `.github/workflows/db-audit.yml` committed and tested
- [ ] SchemaSpy downloaded to `tools/schemaspy.jar`
- [ ] `make docs-db` target added and tested locally (generates docs)
- [ ] `make docs-db-serve` target added and tested locally (serves on port 8080)
- [ ] `.sqlfluff` configuration created with PostgreSQL rules
- [ ] `make lint-sql` and `make fix-sql` targets added and tested
- [ ] `.pre-commit-config.yaml` updated with SQLFluff hooks
- [ ] CI workflow `.github/workflows/docs.yml` updated for SchemaSpy auto-publish
- [ ] All tooling scripts committed to repository
- [ ] README.md updated with "Database Tooling" section documenting all three tools

---

## Timeline Impact

**Original Timeline**: 7 days (Phase 0-5)  
**Updated Timeline**: 8 days (Pre-Phase 0 + Phase 0-5)

- **Pre-Phase 0**: 1 day (audit tooling setup)
- Phase 0-1: 2 days (database + route restructuring)
- Phase 2: 1 day (email validation)
- Phase 3: 2 days (comprehensive testing)
- Phase 4: 1.5 days (dev environment + documentation)
- Phase 5: 0.5 days (verification)

**Justification**: Adding 1 day upfront for database audit tooling pays dividends throughout V1.0 cleanup by catching schema issues early, improving documentation quality, and enforcing best practices.

---

## Integration with V1.0 Cleanup

These tools will be used during V1.0 cleanup as follows:

1. **Before Alembic Migration (FR-117)**:
   - Run `make lint-sql` to ensure migration SQL meets standards
   - Run `scripts/db_audit.sh` to establish baseline before changes

2. **After Email Constraint Migration (FR-116)**:
   - Run `scripts/analyze_missing_indexes.py` to verify indexes on `(email, tenant_id)` composite key
   - Run `make docs-db` to regenerate ERD showing new constraint

3. **After Route Restructuring (FR-115)**:
   - No database changes, but SchemaSpy docs ensure no accidental schema drift

4. **Final V1.0 Verification (Phase 5)**:
   - Run full `scripts/db_audit.sh` to verify clean state
   - Generate final SchemaSpy docs for V1.0 release
   - Confirm all SQL migrations pass `make lint-sql`

---

## References

- **Plan**: `/Users/sujoymukherjee/code/githubspeckit/specs/012-v1-cleanup-legacy-removal/plan.md` (lines 193-552)
- **Spec**: `/Users/sujoymukherjee/code/githubspeckit/specs/012-v1-cleanup-legacy-removal/spec.md`
- **SchemaSpy**: https://schemaspy.org/
- **SQLFluff**: https://www.sqlfluff.com/
- **Alembic**: https://alembic.sqlalchemy.org/

---

## Next Steps

1. ✅ **Pre-Phase 0 Complete**: All tooling setup (current status: planned, not yet implemented)
2. ⏳ **Phase 0**: Execute 5 research tasks, create `research.md`
3. ⏳ **Phase 1**: Design artifacts (data-model.md, contracts/, quickstart.md)
4. ⏳ **Phase 2-5**: Implementation and verification (via `/tasks` command)

**Status**: Pre-Phase 0 acceptance criteria documented in plan.md, ready for implementation.
