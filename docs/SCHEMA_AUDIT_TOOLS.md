# Database Schema Audit Tools Comparison

**Date**: 2025-10-21  
**Purpose**: Evaluate tools for comprehensive schema auditing and documentation

---

## Quick Summary

| Tool | Type | Best For | Setup Complexity | Output |
|------|------|----------|------------------|--------|
| **Custom Script** ✅ | Python | Project-specific checks | Low (done) | JSON, MD, DOT |
| **SchemaSpy** | Java | Visual ERD + HTML docs | Medium | HTML, SVG, PNG |
| **tbls** | Go | Markdown docs + CI/CD | Low | Markdown, PlantUML |
| **PostgreSQL Inspector** | SQL | Quick checks | Minimal | SQL results |
| **DBeaver** | GUI | Manual exploration | Low | Interactive |

---

## 1. Custom Python Script (✅ IMPLEMENTED)

**Location**: `scripts/audit_schema.py`

### Features
- ✅ Table inventory with row counts
- ✅ Column details (type, nullable, defaults)
- ✅ Primary key naming analysis
- ✅ Foreign key relationship mapping
- ✅ Index coverage analysis
- ✅ Enum type documentation
- ✅ **Inconsistency detection** (PK/FK naming, missing indexes, audit field nullability)
- ✅ Multiple output formats (JSON, Markdown, DOT)

### Usage
```bash
# Activate venv
source .venv/bin/activate

# Run audit
python scripts/audit_schema.py

# Output files in reports/schema_audit/
# - schema_audit_YYYYMMDD_HHMMSS.json
# - schema_audit_YYYYMMDD_HHMMSS.md
# - schema_erd_YYYYMMDD_HHMMSS.dot

# Generate ERD diagram (requires GraphViz)
dot -Tpng reports/schema_audit/schema_erd_*.dot -o reports/schema_audit/schema_erd.png
```

### Pros
- Project-specific validation rules
- No external dependencies beyond SQLAlchemy
- Customizable for our naming conventions
- Detects issues like:
  - `pk_user_details` vs `user_details_pkey` inconsistency
  - Missing FK indexes
  - Audit field nullability mismatches
  - Tables without PKs

### Cons
- Manual maintenance required
- ERD visualization requires GraphViz

---

## 2. SchemaSpy

**Website**: https://schemaspy.org/  
**Language**: Java  
**License**: MIT

### Features
- Beautiful HTML documentation
- Interactive ERD diagrams
- Orphaned table detection
- Anomaly detection (missing indexes, circular dependencies)
- Column usage statistics
- Relationship visualization

### Setup
```bash
# Install Java (if not present)
brew install openjdk@17

# Download SchemaSpy JAR
wget https://github.com/schemaspy/schemaspy/releases/download/v6.2.4/schemaspy-6.2.4.jar

# Download PostgreSQL JDBC driver
wget https://jdbc.postgresql.org/download/postgresql-42.7.1.jar

# Run SchemaSpy
java -jar schemaspy-6.2.4.jar \
  -t pgsql \
  -dp postgresql-42.7.1.jar \
  -host localhost \
  -port 5432 \
  -db infysight_users \
  -u infysight_dbadmin \
  -p infysight_dbadmin123 \
  -s public \
  -o reports/schemaspy

# Open in browser
open reports/schemaspy/index.html
```

### Pros
- Professional-looking HTML documentation
- Interactive diagrams (zoom, filter, search)
- Anomaly detection
- Column usage statistics
- No code changes required

### Cons
- Java dependency
- Large output directory (10-50 MB)
- Not easily integrated into CI/CD
- Overkill for quick checks

### When to Use
- Before major refactoring
- For stakeholder presentations
- Team onboarding documentation
- Comprehensive schema reviews

---

## 3. tbls (Table Documentation)

**Website**: https://github.com/k1LoW/tbls  
**Language**: Go  
**License**: MIT

### Features
- Lightweight Markdown documentation
- PlantUML ERD diagrams
- Schema diffing (compare before/after)
- CI/CD friendly
- Supports multiple databases

### Setup
```bash
# Install via Homebrew
brew install k1LoW/tap/tbls

# Create config file
cat > .tbls.yml <<EOF
dsn: postgres://infysight_dbadmin:infysight_dbadmin123@localhost:5432/infysight_users?sslmode=disable
docPath: reports/tbls
er:
  format: svg
  distance: 1
EOF

# Generate documentation
tbls doc

# View output
open reports/tbls/README.md
```

### Pros
- Fast and lightweight
- Git-friendly output (Markdown)
- Schema diffing built-in
- Great for CI/CD pipelines
- Active development

### Cons
- Less visually impressive than SchemaSpy
- Requires Go binary

### When to Use
- CI/CD schema validation
- Pull request documentation
- Schema change tracking
- Lightweight team docs

---

## 4. PostgreSQL Information Schema Queries

**Direct SQL queries for quick checks**

### Key Queries

#### List All FK Constraints
```sql
SELECT 
    tc.table_name AS from_table,
    kcu.column_name AS from_column,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column,
    rc.delete_rule AS on_delete,
    tc.constraint_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public'
ORDER BY from_table, from_column;
```

#### Find Missing FK Indexes
```sql
SELECT 
    c.conrelid::regclass AS table_name,
    string_agg(a.attname, ', ' ORDER BY x.n) AS columns,
    'Missing index on FK: ' || c.conname AS issue
FROM pg_constraint c
CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS x(attnum, n)
JOIN pg_attribute a ON a.attnum = x.attnum AND a.attrelid = c.conrelid
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid
    AND (
      c.conkey::int[] <@ i.indkey::int[] OR
      c.conkey::int[] @> i.indkey::int[]
    )
  )
GROUP BY c.conrelid, c.conname;
```

#### Check PK Naming Consistency
```sql
SELECT 
    table_name,
    constraint_name,
    CASE 
        WHEN constraint_name LIKE '%_pkey' THEN 'standard'
        WHEN constraint_name LIKE 'pk_%' THEN 'prefixed'
        ELSE 'other'
    END AS naming_pattern
FROM information_schema.table_constraints
WHERE constraint_type = 'PRIMARY KEY'
  AND table_schema = 'public'
ORDER BY naming_pattern, table_name;
```

### Pros
- No installation required
- Instant results
- Customizable queries

### Cons
- Manual execution
- No visualization
- Repetitive for comprehensive checks

---

## 5. DBeaver (GUI Tool)

**Website**: https://dbeaver.io/  
**Type**: Desktop Application  
**License**: Apache 2.0 (Community Edition)

### Features
- Visual ER diagrams
- Database explorer
- SQL editor with autocomplete
- Data export/import
- Schema comparison

### Setup
```bash
# Install via Homebrew
brew install --cask dbeaver-community

# Open and connect to localhost:5432/infysight_users
```

### Pros
- User-friendly GUI
- Visual schema exploration
- Built-in SQL editor
- Free community edition

### Cons
- Manual operation (not scriptable)
- Not suitable for CI/CD
- Large application

### When to Use
- Ad-hoc schema exploration
- Visual relationship checking
- Quick data browsing

---

## Recommendation for This Project

### Immediate Use (✅ Done)
**Custom Python Script** (`scripts/audit_schema.py`)
- Tailored to our specific checks
- Detects naming inconsistencies
- Validates audit field patterns
- Generates reports for documentation

### Before Consolidated Migration
**Run all three**:
1. Custom script for validation
2. Generate ERD with GraphViz for visual review
3. Save reports for before/after comparison

### After Consolidated Migration
**Validation suite**:
```bash
# 1. Run custom audit
python scripts/audit_schema.py

# 2. Generate ERD diagram
dot -Tpng reports/schema_audit/schema_erd_*.dot -o reports/schema_audit/schema_erd.png

# 3. Compare with backup schema
diff backup_schema_before_consolidation.sql <(pg_dump -s ...)
```

### For Team Documentation (Optional)
**SchemaSpy** - Generate once for wiki/onboarding:
```bash
make schema-docs  # Could add to Makefile
```

### For CI/CD (Future)
**tbls** - Add schema validation to PR checks:
```yaml
# .github/workflows/schema-check.yml
- name: Check schema changes
  run: tbls diff
```

---

## Running the Custom Audit Now

```bash
# Ensure PostgreSQL is running
brew services list | grep postgresql

# Activate venv
source .venv/bin/activate

# Run comprehensive audit
python scripts/audit_schema.py

# View markdown report
cat reports/schema_audit/schema_audit_*.md | less

# Generate ERD (requires GraphViz)
brew install graphviz
dot -Tpng reports/schema_audit/schema_erd_*.dot -o schema_current.png
open schema_current.png
```

### Expected Output
- JSON report with full schema details
- Markdown report highlighting:
  - ✅ 14 tables (missing `roles`)
  - 🟡 PK naming: `pk_user_details` vs standard `*_pkey`
  - 🟡 FK naming: `fk_*` vs standard `*_fkey`
  - ℹ️ Missing FK indexes
  - 🟡 Audit field nullability (user_details)
- DOT file for ERD visualization

---

## Next Steps

1. ✅ **Run custom audit script** - Get baseline before consolidation
2. 📊 **Review inconsistencies** - Validate against PK_FK_ANALYSIS.md
3. 🔧 **Create consolidated migration** - Incorporate all fixes
4. ✅ **Re-run audit** - Verify all issues resolved
5. 📝 **Document changes** - Add to MIGRATION-CONSOLIDATION-V1.0.md

---

## Additional Tools (Reference)

### Database Diagram Tools
- **dbdiagram.io** - Web-based ERD design
- **draw.io** - Manual diagram creation
- **PlantUML** - Text-based diagrams

### Schema Migration Validators
- **Alembic autogenerate** - Detect drift between models and DB
- **SQLAlchemy-Utils** - Additional schema utilities
- **pg_prove** - PostgreSQL unit testing

### Performance Analysis
- **pg_stat_statements** - Query performance tracking
- **pgBadger** - PostgreSQL log analyzer
- **EXPLAIN ANALYZE** - Query execution plans
