#!/usr/bin/env python3
"""
Pre-Migration Validation Script for V1.0 Email Uniqueness Change

Validates that no duplicate (email, tenant_id) combinations exist before
applying the per-tenant email uniqueness migration.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.persistence.db_config import get_database_url


async def check_email_conflicts(conn: AsyncConnection) -> List[Tuple[str, str, int]]:
    """
    Query for duplicate (email, tenant_id) pairs.
    
    Returns:
        List of (tenant_id, email, count) tuples for conflicts
    """
    query = text("""
        SELECT tenant_id, email, COUNT(*) as cnt
        FROM users
        GROUP BY tenant_id, email
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, tenant_id, email
    """)
    
    result = await conn.execute(query)
    conflicts = [(str(row.tenant_id), row.email, row.cnt) for row in result]
    
    return conflicts


async def check_global_email_duplicates(conn: AsyncConnection) -> List[Tuple[str, int]]:
    """
    Query for emails that exist in multiple tenants.
    This is ALLOWED in V1.0 but worth reporting for awareness.
    
    Returns:
        List of (email, tenant_count) tuples
    """
    query = text("""
        SELECT email, COUNT(DISTINCT tenant_id) as tenant_count
        FROM users
        GROUP BY email
        HAVING COUNT(DISTINCT tenant_id) > 1
        ORDER BY tenant_count DESC, email
    """)
    
    result = await conn.execute(query)
    duplicates = [(row.email, row.tenant_count) for row in result]
    
    return duplicates


async def main():
    """Main validation function."""
    print("=" * 70)
    print("V1.0 Email Uniqueness Migration - Pre-Migration Validation")
    print("=" * 70)
    print()
    
    try:
        # Connect to database
        database_url = get_database_url()
        print(f"Connecting to database...")
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Check 1: Per-tenant email conflicts (BLOCKER)
            print("Checking for duplicate (email, tenant_id) combinations...")
            conflicts = await check_email_conflicts(conn)
            
            if conflicts:
                print()
                print("❌ VALIDATION FAILED: Duplicate (email, tenant_id) pairs found")
                print()
                print(f"Found {len(conflicts)} conflict(s):")
                print()
                for tenant_id, email, count in conflicts[:10]:  # Show first 10
                    print(f"  - Tenant: {tenant_id}, Email: {email}, Count: {count}")
                
                if len(conflicts) > 10:
                    print(f"  ... and {len(conflicts) - 10} more")
                
                print()
                print("Action Required:")
                print("  1. Manually resolve duplicate emails within each tenant")
                print("  2. Either delete duplicate users or update their emails")
                print("  3. Re-run this validation script before migration")
                print()
                print("Migration CANNOT proceed until conflicts are resolved.")
                return 1
            else:
                print("✓ No duplicate (email, tenant_id) combinations found")
            
            print()
            
            # Check 2: Cross-tenant email sharing (INFORMATIONAL)
            print("Checking for emails shared across multiple tenants...")
            cross_tenant = await check_global_email_duplicates(conn)
            
            if cross_tenant:
                print(f"ℹ️  Found {len(cross_tenant)} email(s) used in multiple tenants")
                print()
                print("This is ALLOWED in V1.0 (per-tenant email uniqueness).")
                print("First 5 examples:")
                print()
                for email, tenant_count in cross_tenant[:5]:
                    print(f"  - {email}: used in {tenant_count} tenant(s)")
                
                if len(cross_tenant) > 5:
                    print(f"  ... and {len(cross_tenant) - 5} more")
                
                print()
                print("Note: This is expected behavior in multi-tenant systems.")
            else:
                print("✓ No emails shared across multiple tenants")
            
            print()
            print("=" * 70)
            print("✅ VALIDATION PASSED")
            print("=" * 70)
            print()
            print("Migration can proceed safely:")
            print("  1. Run: alembic upgrade head")
            print("  2. The per-tenant email uniqueness constraint will be enforced")
            print("  3. Cross-tenant email duplicates will remain allowed")
            print()
            
            return 0
    
    except Exception as e:
        print()
        print(f"❌ ERROR: Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
