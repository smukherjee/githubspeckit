#!/usr/bin/env python3
"""
Comprehensive Database Schema Audit Script

Generates detailed reports on:
- Tables, columns, data types
- Primary keys and their naming
- Foreign keys and relationships
- Indexes and their usage
- Constraints and their naming conventions
- Enum types
- Schema inconsistencies

Output formats:
- JSON (machine-readable)
- Markdown (human-readable)
- ERD DOT format (for GraphViz visualization)
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict

import asyncpg
from sqlalchemy import inspect, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine


# Configuration
DATABASE_URL = "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
OUTPUT_DIR = Path("reports/schema_audit")


class SchemaAuditor:
    """Comprehensive database schema auditor."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.metadata = MetaData()
        self.report = {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {},
            "tables": {},
            "foreign_keys": [],
            "indexes": [],
            "enums": [],
            "inconsistencies": [],
            "statistics": {}
        }
    
    async def connect(self):
        """Establish database connection."""
        self.engine = create_async_engine(self.database_url, echo=False)
        
    async def disconnect(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
    
    async def audit(self):
        """Run comprehensive schema audit."""
        await self.connect()
        
        try:
            # Get database metadata
            await self._audit_database_info()
            
            # Audit tables and columns
            await self._audit_tables()
            
            # Audit foreign keys
            await self._audit_foreign_keys()
            
            # Audit indexes
            await self._audit_indexes()
            
            # Audit enum types
            await self._audit_enums()
            
            # Check for inconsistencies
            await self._check_inconsistencies()
            
            # Calculate statistics
            self._calculate_statistics()
            
        finally:
            await self.disconnect()
    
    async def _audit_database_info(self):
        """Collect database-level information."""
        async with self.engine.connect() as conn:
            def _get_info(sync_conn):
                result = {}
                # Get PostgreSQL version
                version_result = sync_conn.execute(text("SELECT version()")).fetchone()
                result["version"] = version_result[0] if version_result else "Unknown"
                
                # Get database size
                size_result = sync_conn.execute(
                    text("SELECT pg_size_pretty(pg_database_size(current_database()))")
                ).fetchone()
                result["size"] = size_result[0] if size_result else "Unknown"
                
                # Get current schema revision (Alembic)
                try:
                    revision_result = sync_conn.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).fetchone()
                    result["alembic_revision"] = revision_result[0] if revision_result else None
                except Exception:
                    result["alembic_revision"] = None
                
                return result
            
            self.report["database"] = await conn.run_sync(_get_info)
    
    async def _audit_tables(self):
        """Audit all tables and their columns."""
        async with self.engine.connect() as conn:
            def _get_tables(sync_conn):
                inspector = inspect(sync_conn)
                tables = {}
                
                for table_name in inspector.get_table_names():
                    columns = []
                    pk_columns = []
                    
                    # Get primary key
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    if pk_constraint:
                        pk_columns = pk_constraint.get('constrained_columns', [])
                    
                    # Get columns
                    for col in inspector.get_columns(table_name):
                        columns.append({
                            "name": col['name'],
                            "type": str(col['type']),
                            "nullable": col['nullable'],
                            "default": str(col['default']) if col['default'] else None,
                            "is_primary_key": col['name'] in pk_columns,
                            "autoincrement": col.get('autoincrement', False)
                        })
                    
                    tables[table_name] = {
                        "columns": columns,
                        "primary_key": {
                            "constraint_name": pk_constraint.get('name') if pk_constraint else None,
                            "columns": pk_columns
                        },
                        "row_count": None  # Will be populated separately
                    }
                
                return tables
            
            self.report["tables"] = await conn.run_sync(_get_tables)
        
        # Get row counts (async for performance)
        await self._get_row_counts()
    
    async def _get_row_counts(self):
        """Get approximate row counts for all tables."""
        async with self.engine.connect() as conn:
            def _count_rows(sync_conn):
                counts = {}
                for table_name in self.report["tables"].keys():
                    try:
                        # Use pg_class for fast approximate counts
                        result = sync_conn.execute(text(f"""
                            SELECT n_live_tup 
                            FROM pg_stat_user_tables 
                            WHERE relname = '{table_name}'
                        """)).fetchone()
                        counts[table_name] = result[0] if result else 0
                    except Exception:
                        counts[table_name] = None
                return counts
            
            counts = await conn.run_sync(_count_rows)
            for table_name, count in counts.items():
                if table_name in self.report["tables"]:
                    self.report["tables"][table_name]["row_count"] = count
    
    async def _audit_foreign_keys(self):
        """Audit all foreign key relationships."""
        async with self.engine.connect() as conn:
            def _get_fks(sync_conn):
                inspector = inspect(sync_conn)
                fks = []
                
                for table_name in inspector.get_table_names():
                    for fk in inspector.get_foreign_keys(table_name):
                        fks.append({
                            "from_table": table_name,
                            "from_columns": fk['constrained_columns'],
                            "to_table": fk['referred_table'],
                            "to_columns": fk['referred_columns'],
                            "constraint_name": fk['name'],
                            "on_delete": fk.get('ondelete', 'NO ACTION'),
                            "on_update": fk.get('onupdate', 'NO ACTION')
                        })
                
                return fks
            
            self.report["foreign_keys"] = await conn.run_sync(_get_fks)
    
    async def _audit_indexes(self):
        """Audit all indexes."""
        async with self.engine.connect() as conn:
            def _get_indexes(sync_conn):
                inspector = inspect(sync_conn)
                indexes = []
                
                for table_name in inspector.get_table_names():
                    for idx in inspector.get_indexes(table_name):
                        indexes.append({
                            "table": table_name,
                            "name": idx['name'],
                            "columns": idx['column_names'],
                            "unique": idx['unique']
                        })
                
                return indexes
            
            self.report["indexes"] = await conn.run_sync(_get_indexes)
    
    async def _audit_enums(self):
        """Audit PostgreSQL enum types."""
        async with self.engine.connect() as conn:
            def _get_enums(sync_conn):
                result = sync_conn.execute(text("""
                    SELECT t.typname AS enum_name, 
                           array_agg(e.enumlabel ORDER BY e.enumsortorder) AS enum_values
                    FROM pg_type t 
                    JOIN pg_enum e ON t.oid = e.enumtypid  
                    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public'
                    GROUP BY t.typname
                    ORDER BY t.typname
                """)).fetchall()
                
                return [
                    {"name": row[0], "values": row[1]}
                    for row in result
                ]
            
            self.report["enums"] = await conn.run_sync(_get_enums)
    
    async def _check_inconsistencies(self):
        """Check for naming and structural inconsistencies."""
        inconsistencies = []
        
        # Check PK naming consistency
        pk_patterns = defaultdict(list)
        for table_name, table_info in self.report["tables"].items():
            pk_name = table_info["primary_key"]["constraint_name"]
            if pk_name:
                if pk_name.endswith("_pkey"):
                    pk_patterns["standard"].append(table_name)
                elif pk_name.startswith("pk_"):
                    pk_patterns["prefixed"].append(table_name)
                else:
                    pk_patterns["other"].append(table_name)
        
        if len(pk_patterns) > 1:
            inconsistencies.append({
                "type": "pk_naming",
                "severity": "warning",
                "message": f"Inconsistent PK naming: {dict(pk_patterns)}",
                "details": pk_patterns
            })
        
        # Check FK naming consistency
        fk_patterns = defaultdict(list)
        for fk in self.report["foreign_keys"]:
            fk_name = fk["constraint_name"]
            if fk_name:
                if fk_name.endswith("_fkey"):
                    fk_patterns["standard"].append(fk_name)
                elif fk_name.startswith("fk_"):
                    fk_patterns["prefixed"].append(fk_name)
                else:
                    fk_patterns["other"].append(fk_name)
        
        if len(fk_patterns) > 1:
            inconsistencies.append({
                "type": "fk_naming",
                "severity": "warning",
                "message": f"Inconsistent FK naming patterns: {len(fk_patterns['standard'])} standard, {len(fk_patterns['prefixed'])} prefixed",
                "details": {k: len(v) for k, v in fk_patterns.items()}
            })
        
        # Check for missing indexes on FK columns
        fk_columns = set()
        for fk in self.report["foreign_keys"]:
            for col in fk["from_columns"]:
                fk_columns.add((fk["from_table"], col))
        
        indexed_columns = set()
        for idx in self.report["indexes"]:
            for col in idx["columns"]:
                indexed_columns.add((idx["table"], col))
        
        missing_fk_indexes = fk_columns - indexed_columns
        if missing_fk_indexes:
            inconsistencies.append({
                "type": "missing_fk_indexes",
                "severity": "info",
                "message": f"{len(missing_fk_indexes)} FK columns without indexes",
                "details": [f"{table}.{col}" for table, col in missing_fk_indexes]
            })
        
        # Check for tables without PKs
        tables_without_pk = [
            table_name for table_name, table_info in self.report["tables"].items()
            if not table_info["primary_key"]["columns"]
        ]
        if tables_without_pk:
            inconsistencies.append({
                "type": "missing_primary_keys",
                "severity": "error",
                "message": f"Tables without primary keys: {tables_without_pk}",
                "details": tables_without_pk
            })
        
        # Check for nullable audit fields inconsistency
        audit_field_nullability = defaultdict(list)
        for table_name, table_info in self.report["tables"].items():
            for col in table_info["columns"]:
                if col["name"] in ["created_by", "updated_by"]:
                    key = f"{col['name']}_{'nullable' if col['nullable'] else 'not_null'}"
                    audit_field_nullability[key].append(table_name)
        
        if len(audit_field_nullability) > 2:  # Should be consistent across all tables
            inconsistencies.append({
                "type": "audit_field_nullability",
                "severity": "warning",
                "message": "Inconsistent nullability for audit fields",
                "details": audit_field_nullability
            })
        
        self.report["inconsistencies"] = inconsistencies
    
    def _calculate_statistics(self):
        """Calculate schema statistics."""
        self.report["statistics"] = {
            "total_tables": len(self.report["tables"]),
            "total_columns": sum(len(t["columns"]) for t in self.report["tables"].values()),
            "total_foreign_keys": len(self.report["foreign_keys"]),
            "total_indexes": len(self.report["indexes"]),
            "total_unique_indexes": sum(1 for idx in self.report["indexes"] if idx["unique"]),
            "total_enums": len(self.report["enums"]),
            "total_inconsistencies": len(self.report["inconsistencies"]),
            "tables_with_data": sum(
                1 for t in self.report["tables"].values() 
                if t["row_count"] and t["row_count"] > 0
            )
        }
    
    def generate_markdown_report(self) -> str:
        """Generate human-readable markdown report."""
        lines = [
            "# Database Schema Audit Report",
            "",
            f"**Generated**: {self.report['audit_timestamp']}",
            "",
            "---",
            "",
            "## Database Information",
            "",
            f"- **Version**: {self.report['database'].get('version', 'Unknown')}",
            f"- **Size**: {self.report['database'].get('size', 'Unknown')}",
            f"- **Alembic Revision**: `{self.report['database'].get('alembic_revision', 'Unknown')}`",
            "",
            "## Statistics",
            "",
            f"- **Tables**: {self.report['statistics']['total_tables']}",
            f"- **Columns**: {self.report['statistics']['total_columns']}",
            f"- **Foreign Keys**: {self.report['statistics']['total_foreign_keys']}",
            f"- **Indexes**: {self.report['statistics']['total_indexes']} ({self.report['statistics']['total_unique_indexes']} unique)",
            f"- **Enum Types**: {self.report['statistics']['total_enums']}",
            f"- **Tables with Data**: {self.report['statistics']['tables_with_data']}",
            f"- **Inconsistencies Found**: {self.report['statistics']['total_inconsistencies']}",
            "",
        ]
        
        # Tables
        lines.extend([
            "---",
            "",
            "## Tables",
            "",
            "| Table | Columns | PK | Rows | PK Constraint |",
            "|-------|---------|----|----- |---------------|"
        ])
        
        for table_name in sorted(self.report["tables"].keys()):
            table = self.report["tables"][table_name]
            pk_cols = ", ".join(table["primary_key"]["columns"]) if table["primary_key"]["columns"] else "❌ NONE"
            pk_name = table["primary_key"]["constraint_name"] or "N/A"
            row_count = table["row_count"] if table["row_count"] is not None else "?"
            lines.append(f"| {table_name} | {len(table['columns'])} | {pk_cols} | {row_count} | {pk_name} |")
        
        lines.append("")
        
        # Foreign Keys
        lines.extend([
            "---",
            "",
            "## Foreign Key Relationships",
            "",
            "| From | Column(s) | To | Column(s) | ON DELETE | Constraint |",
            "|------|-----------|----|-----------|-----------|-----------"
        ])
        
        for fk in sorted(self.report["foreign_keys"], key=lambda x: (x["from_table"], x["to_table"])):
            from_cols = ", ".join(fk["from_columns"])
            to_cols = ", ".join(fk["to_columns"])
            lines.append(
                f"| {fk['from_table']} | {from_cols} | {fk['to_table']} | {to_cols} | "
                f"{fk['on_delete']} | {fk['constraint_name']} |"
            )
        
        lines.append("")
        
        # Inconsistencies
        if self.report["inconsistencies"]:
            lines.extend([
                "---",
                "",
                "## ⚠️ Inconsistencies Detected",
                ""
            ])
            
            for issue in self.report["inconsistencies"]:
                severity_emoji = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(issue["severity"], "⚠️")
                lines.append(f"### {severity_emoji} {issue['type'].replace('_', ' ').title()}")
                lines.append("")
                lines.append(f"**Severity**: {issue['severity'].upper()}")
                lines.append(f"**Message**: {issue['message']}")
                lines.append("")
                if isinstance(issue["details"], dict):
                    for key, value in issue["details"].items():
                        lines.append(f"- **{key}**: {value}")
                elif isinstance(issue["details"], list):
                    for item in issue["details"]:
                        lines.append(f"- {item}")
                lines.append("")
        
        # Enum Types
        if self.report["enums"]:
            lines.extend([
                "---",
                "",
                "## Enum Types",
                ""
            ])
            
            for enum in self.report["enums"]:
                lines.append(f"### `{enum['name']}`")
                lines.append("")
                for value in enum["values"]:
                    lines.append(f"- `{value}`")
                lines.append("")
        
        return "\n".join(lines)
    
    def generate_erd_dot(self) -> str:
        """Generate ERD in DOT format for GraphViz."""
        lines = [
            "digraph schema {",
            "  rankdir=LR;",
            "  node [shape=record];",
            ""
        ]
        
        # Define tables
        for table_name, table_info in self.report["tables"].items():
            pk_cols = set(table_info["primary_key"]["columns"])
            col_defs = []
            
            for col in table_info["columns"]:
                col_name = col["name"]
                col_type = col["type"]
                
                if col_name in pk_cols:
                    col_defs.append(f"<{col_name}> ⚷ {col_name} : {col_type}")
                else:
                    col_defs.append(f"<{col_name}> {col_name} : {col_type}")
            
            lines.append(f'  {table_name} [label="{{<table> {table_name}|{"|".join(col_defs)}}}"];')
        
        lines.append("")
        
        # Define relationships
        for fk in self.report["foreign_keys"]:
            from_table = fk["from_table"]
            to_table = fk["to_table"]
            from_col = fk["from_columns"][0] if fk["from_columns"] else ""
            to_col = fk["to_columns"][0] if fk["to_columns"] else ""
            
            lines.append(
                f'  {from_table}:{from_col} -> {to_table}:{to_col} '
                f'[label="{fk["on_delete"]}"];'
            )
        
        lines.extend([
            "}",
            ""
        ])
        
        return "\n".join(lines)


async def main():
    """Run schema audit and generate reports."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🔍 Starting comprehensive schema audit...")
    
    auditor = SchemaAuditor(DATABASE_URL)
    await auditor.audit()
    
    print("✅ Audit complete!")
    print(f"\n📊 Statistics:")
    print(f"  - Tables: {auditor.report['statistics']['total_tables']}")
    print(f"  - Foreign Keys: {auditor.report['statistics']['total_foreign_keys']}")
    print(f"  - Indexes: {auditor.report['statistics']['total_indexes']}")
    print(f"  - Inconsistencies: {auditor.report['statistics']['total_inconsistencies']}")
    
    # Save JSON report
    json_path = OUTPUT_DIR / f"schema_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w") as f:
        json.dump(auditor.report, f, indent=2, default=str)
    print(f"\n💾 JSON report: {json_path}")
    
    # Save Markdown report
    md_path = OUTPUT_DIR / f"schema_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_path, "w") as f:
        f.write(auditor.generate_markdown_report())
    print(f"📝 Markdown report: {md_path}")
    
    # Save ERD DOT file
    dot_path = OUTPUT_DIR / f"schema_erd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dot"
    with open(dot_path, "w") as f:
        f.write(auditor.generate_erd_dot())
    print(f"🔗 ERD DOT file: {dot_path}")
    print(f"   Generate PNG: dot -Tpng {dot_path} -o schema_erd.png")
    
    # Print inconsistencies
    if auditor.report["inconsistencies"]:
        print(f"\n⚠️  Found {len(auditor.report['inconsistencies'])} inconsistencies:")
        for issue in auditor.report["inconsistencies"]:
            severity_emoji = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(issue["severity"], "⚠️")
            print(f"  {severity_emoji} [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    asyncio.run(main())
