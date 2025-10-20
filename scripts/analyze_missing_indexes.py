#!/usr/bin/env python3
"""
Missing Indexes Analyzer
Scans for columns frequently used in WHERE/JOIN clauses without indexes.
Uses static analysis of SQLAlchemy queries and model definitions.
"""

import asyncio
from typing import Dict, List, Set, Tuple
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from src.adapters.persistence.db_config import get_database_url


async def get_table_indexes() -> Dict[str, List[Dict]]:
    """Get all indexes currently defined in the database."""
    database_url = get_database_url()
    engine = create_async_engine(database_url)
    
    async with engine.connect() as conn:
        def _get_indexes(connection):
            inspector = inspect(connection.sync_connection)
            tables = inspector.get_table_names()
            
            indexes_by_table = {}
            for table in tables:
                indexes = inspector.get_indexes(table)
                indexes_by_table[table] = indexes
            
            return indexes_by_table
        
        result = await conn.run_sync(_get_indexes)
    
    await engine.dispose()
    return result


def analyze_orm_models() -> Dict[str, Set[str]]:
    """
    Analyze ORM models to identify columns that should have indexes.
    Returns dict of {table_name: {column_names_needing_indexes}}
    """
    from src.adapters.persistence.models import Base
    
    recommendations = {}
    
    for table_name, table in Base.metadata.tables.items():
        columns_needing_indexes = set()
        
        # Check for foreign key columns (should always be indexed)
        for fk in table.foreign_keys:
            col_name = fk.parent.name
            columns_needing_indexes.add(col_name)
        
        # Common filtering columns (heuristic based on naming patterns)
        for column in table.columns:
            col_name = column.name
            
            # Skip primary keys (always indexed)
            if column.primary_key:
                continue
            
            # Common patterns that benefit from indexes
            if any(pattern in col_name for pattern in [
                'tenant_id',  # Multi-tenant filtering
                'user_id',    # User-scoped queries
                'created_at', # Time-based queries
                'updated_at', # Time-based queries
                'status',     # Status filtering
                'type',       # Type filtering
                'slug',       # URL lookups
                'email',      # User lookups
                'deleted_at', # Soft delete queries
            ]):
                columns_needing_indexes.add(col_name)
        
        if columns_needing_indexes:
            recommendations[table_name] = columns_needing_indexes
    
    return recommendations


def check_existing_indexes(
    table_indexes: Dict[str, List[Dict]],
    table: str,
    column: str
) -> bool:
    """Check if a column already has an index."""
    if table not in table_indexes:
        return False
    
    for index in table_indexes[table]:
        # Check if column is in index (could be composite index)
        if column in index.get('column_names', []):
            return True
    
    return False


async def main():
    """Main function to analyze missing indexes."""
    print("=" * 60)
    print("Missing Indexes Analysis")
    print("=" * 60)
    print()
    
    try:
        # Get existing indexes from database
        print("Fetching existing indexes from database...")
        table_indexes = await get_table_indexes()
        total_indexes = sum(len(indexes) for indexes in table_indexes.values())
        print(f"Found {total_indexes} indexes across {len(table_indexes)} tables")
        print()
        
        # Analyze ORM models for recommended indexes
        print("Analyzing ORM models for index recommendations...")
        recommendations = analyze_orm_models()
        print(f"Analyzed {len(recommendations)} tables")
        print()
        
        # Find missing indexes
        missing_indexes: List[Tuple[str, str]] = []
        
        for table, columns in recommendations.items():
            for column in columns:
                if not check_existing_indexes(table_indexes, table, column):
                    missing_indexes.append((table, column))
        
        if missing_indexes:
            print(f"⚠️  WARNING: Found {len(missing_indexes)} potentially missing index(es):")
            print()
            
            # Group by table for better readability
            by_table: Dict[str, List[str]] = {}
            for table, column in missing_indexes:
                if table not in by_table:
                    by_table[table] = []
                by_table[table].append(column)
            
            for table in sorted(by_table.keys()):
                print(f"  Table: {table}")
                for column in sorted(by_table[table]):
                    print(f"    - {column}")
                print()
            
            print("Recommendations:")
            print("  1. Review query patterns to confirm these columns are used in WHERE/JOIN clauses")
            print("  2. Add indexes via Alembic migration if confirmed")
            print("  3. Consider composite indexes for common query combinations")
            print("  4. Monitor query performance before and after adding indexes")
            return 1
        else:
            print("✓ No missing indexes detected")
            print("  All recommended columns have indexes")
            return 0
    
    except Exception as e:
        print(f"✗ Error during missing indexes analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
