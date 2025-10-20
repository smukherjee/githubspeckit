#!/usr/bin/env python3
"""
Orphaned Tables Detector
Finds database tables that are not defined in SQLAlchemy ORM models.
"""

import asyncio
from typing import Set
from sqlalchemy import inspect, MetaData
from sqlalchemy.ext.asyncio import create_async_engine

from src.adapters.persistence.db_config import get_database_url


async def get_db_tables() -> Set[str]:
    """Get all tables currently in the database."""
    database_url = get_database_url()
    engine = create_async_engine(database_url)
    
    async with engine.connect() as conn:
        # Run inspection in a sync context
        def _get_tables(connection):
            inspector = inspect(connection.sync_connection)
            return set(inspector.get_table_names())
        
        tables = await conn.run_sync(_get_tables)
    
    await engine.dispose()
    return tables


def get_orm_tables() -> Set[str]:
    """Get all tables defined in SQLAlchemy ORM models."""
    from src.adapters.persistence.models import Base
    
    # Get all table names from the Base metadata
    metadata: MetaData = Base.metadata
    return {table.name for table in metadata.tables.values()}


async def main():
    """Main function to detect orphaned tables."""
    print("=" * 60)
    print("Orphaned Tables Detection")
    print("=" * 60)
    print()
    
    try:
        # Get tables from database
        print("Fetching tables from database...")
        db_tables = await get_db_tables()
        print(f"Found {len(db_tables)} tables in database")
        
        # Get tables from ORM
        print("Scanning SQLAlchemy ORM models...")
        orm_tables = get_orm_tables()
        print(f"Found {len(orm_tables)} tables in ORM models")
        print()
        
        # Find orphaned tables (in DB but not in ORM)
        orphaned = db_tables - orm_tables
        
        # Filter out known system tables
        system_tables = {'alembic_version', 'spatial_ref_sys'}
        orphaned = orphaned - system_tables
        
        if orphaned:
            print(f"⚠️  WARNING: Found {len(orphaned)} orphaned table(s):")
            print()
            for table in sorted(orphaned):
                print(f"  - {table}")
            print()
            print("These tables exist in the database but are not defined in ORM models.")
            print("Consider:")
            print("  1. Adding ORM model if the table is needed")
            print("  2. Dropping the table if it's unused")
            print("  3. Creating migration to remove orphaned tables")
            return 1
        else:
            print("✓ No orphaned tables found")
            print("  All database tables have corresponding ORM models")
            return 0
    
    except Exception as e:
        print(f"✗ Error during orphaned tables detection: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
