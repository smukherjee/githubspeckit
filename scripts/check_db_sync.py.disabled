#!/usr/bin/env python3
"""Database synchronization check script.

Compares SQLite (test.db) and PostgreSQL (githubspeckit_test) databases
to ensure they are in sync with the same migrations and seed data.
"""
import sys
import os
import asyncio
import subprocess
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


SQLITE_URL = "sqlite+aiosqlite:///./test.db"
POSTGRES_URL = "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/githubspeckit_test"


async def get_migration_version(engine):
    """Get current Alembic migration version."""
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        return row[0] if row else None


async def get_table_count(engine, table_name):
    """Get row count for a table."""
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row = result.fetchone()
            return row[0] if row else 0
        except Exception:
            return None  # Table doesn't exist


async def get_users(engine):
    """Get all users from database."""
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT user_id, email, status FROM users ORDER BY email"))
        return result.fetchall()


async def get_user_details(engine):
    """Get all user_details from database."""
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("SELECT user_id, full_name, photo_display_url FROM user_details"))
            return result.fetchall()
        except Exception:
            return []  # Table doesn't exist


async def check_database(db_url, db_name):
    """Check database status."""
    print(f"\n{'='*60}")
    print(f"🔍 Checking {db_name}")
    print(f"{'='*60}")
    
    engine = create_async_engine(db_url, echo=False)
    
    try:
        # Migration version
        version = await get_migration_version(engine)
        print(f"✅ Migration version: {version}")
        
        # Table counts
        tables = ['tenants', 'users', 'user_roles', 'user_details', 'audit_events']
        print(f"\n📊 Table Row Counts:")
        for table in tables:
            count = await get_table_count(engine, table)
            status = "✅" if count is not None else "❌"
            print(f"  {status} {table:20} {count if count is not None else 'N/A':>6}")
        
        # Users
        users = await get_users(engine)
        print(f"\n👥 Users ({len(users)} total):")
        for user_id, email, status in users:
            print(f"  - {email:35} (status={status}, id={user_id})")
        
        # User details
        details = await get_user_details(engine)
        if details:
            print(f"\n📝 User Details ({len(details)} total):")
            for user_id, full_name, photo_url in details:
                photo_status = "📷" if photo_url else "  "
                print(f"  {photo_status} {full_name or '(no name)':30} (id={user_id})")
        else:
            print(f"\n⚠️  User Details: No records or table doesn't exist")
        
        return {
            'version': version,
            'tables': {table: await get_table_count(engine, table) for table in tables},
            'users': len(users),
            'user_details': len(details)
        }
        
    finally:
        await engine.dispose()


async def main():
    """Main function."""
    print("🔄 Database Synchronization Check")
    print("="*60)
    
    # Check both databases
    sqlite_status = await check_database(SQLITE_URL, "SQLite (test.db)")
    postgres_status = await check_database(POSTGRES_URL, "PostgreSQL (githubspeckit_test)")
    
    # Compare
    print(f"\n{'='*60}")
    print(f"🔍 Comparison Summary")
    print(f"{'='*60}")
    
    issues = []
    
    # Migration versions
    if sqlite_status['version'] != postgres_status['version']:
        issues.append(f"⚠️  Migration versions differ: SQLite={sqlite_status['version']}, PostgreSQL={postgres_status['version']}")
    else:
        print(f"✅ Migration versions match: {sqlite_status['version']}")
    
    # User counts
    if sqlite_status['users'] != postgres_status['users']:
        issues.append(f"⚠️  User counts differ: SQLite={sqlite_status['users']}, PostgreSQL={postgres_status['users']}")
    else:
        print(f"✅ User counts match: {sqlite_status['users']} users")
    
    # User details counts
    if sqlite_status['user_details'] != postgres_status['user_details']:
        issues.append(f"⚠️  User details counts differ: SQLite={sqlite_status['user_details']}, PostgreSQL={postgres_status['user_details']}")
    else:
        print(f"✅ User details counts match: {sqlite_status['user_details']} records")
    
    # Table existence
    for table in sqlite_status['tables']:
        sqlite_count = sqlite_status['tables'][table]
        postgres_count = postgres_status['tables'][table]
        
        if (sqlite_count is None) != (postgres_count is None):
            issues.append(f"⚠️  Table '{table}' exists in one DB but not the other")
    
    # Print issues
    if issues:
        print(f"\n❌ Issues Found ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
        return 1
    else:
        print(f"\n✅ All checks passed! Databases are in sync.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
