#!/usr/bin/env python3
"""Test script to verify audit events for login/logout."""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Database URL
DATABASE_URL = "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"

async def check_audit_events():
    """Check recent audit events in the database."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        # Query recent audit events
        query = text("""
            SELECT 
                event_id,
                action_type,
                actor_user_id,
                tenant_id,
                metadata,
                created_at
            FROM audit_events
            WHERE action_type IN ('auth.login.success', 'auth.login.failed', 'auth.logout')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        result = await session.execute(query)
        events = result.fetchall()
        
        if not events:
            print("❌ No audit events found for login/logout")
            return False
        
        print(f"✅ Found {len(events)} audit event(s):\n")
        for event in events:
            print(f"Event ID: {event.event_id}")
            print(f"Action: {event.action_type}")
            print(f"Actor: {event.actor_user_id}")
            print(f"Tenant: {event.tenant_id}")
            print(f"Metadata: {event.metadata}")
            print(f"Created: {event.created_at}")
            print("-" * 80)
        
        return True

if __name__ == "__main__":
    result = asyncio.run(check_audit_events())
    sys.exit(0 if result else 1)
