"""
TEST-DB-12: Token replay persistent store tests.

Validates:
- Database-backed replay detection (IMPL-DB-11, FR-SEC-020)
- Atomic check-and-set operations
- Expiration handling
- Multi-tenant support
- Cleanup operations

Status: Phase 3 Lane DB-E
Dependencies: IMPL-DB-11 (DatabaseReplayStore), in-memory store for parity
"""
from __future__ import annotations

import pytest
import uuid
import time
from unittest.mock import AsyncMock

from adapters.persistence.replay_store import (
    DatabaseReplayStore,
    TokenReplayRecordModel,
)
from quality.replay_store import InMemoryReplayStore


@pytest.mark.db
@pytest.mark.asyncio
class TestDatabaseReplayStoreParity:
    """
    TEST-DB-12: Database replay store parity with in-memory implementation.
    
    Validates behavior matches InMemoryReplayStore (FR-SEC-020).
    """
    
    async def test_first_registration_succeeds(self, db_session):
        """Test first token registration succeeds."""
        store = DatabaseReplayStore(db_session)
        
        jti = "jti-first-test"
        result = await store.register(jti, ttl_seconds=3600)
        
        assert result is True, "First registration should succeed"
    
    async def test_second_registration_fails_replay(self, db_session):
        """Test second registration of same token fails (replay detected)."""
        store = DatabaseReplayStore(db_session)
        
        jti = "jti-replay-test"
        
        # First registration
        result1 = await store.register(jti, ttl_seconds=3600)
        assert result1 is True
        
        # Second registration (replay)
        result2 = await store.register(jti, ttl_seconds=3600)
        assert result2 is False, "Second registration should fail (replay)"
    
    async def test_expired_token_can_be_reregistered(self, db_session):
        """Test expired token can be registered again (not a replay)."""
        store = DatabaseReplayStore(db_session)
        
        jti = "jti-expired-test"
        
        # Register with very short TTL
        result1 = await store.register(jti, ttl_seconds=1)
        assert result1 is True
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Re-register after expiration (should succeed)
        result2 = await store.register(jti, ttl_seconds=3600)
        assert result2 is True, "Re-registration after expiration should succeed"
    
    async def test_is_replayed_check_without_registration(self, db_session):
        """Test is_replayed check without modifying state."""
        store = DatabaseReplayStore(db_session)
        
        jti = "jti-check-test"
        
        # Check before registration
        is_replayed_before = await store.is_replayed(jti)
        assert is_replayed_before is False
        
        # Register
        await store.register(jti, ttl_seconds=3600)
        
        # Check after registration
        is_replayed_after = await store.is_replayed(jti)
        assert is_replayed_after is True
    
    async def test_multi_tenant_isolation(self, db_session):
        """
        Test replay detection works globally across tenants (FR-002, FR-SEC-020).
        
        Validates JTI is globally unique (required for superadmin token security).
        Once a JTI is registered, it cannot be reused for any tenant.
        """
        store = DatabaseReplayStore(db_session)
        
        jti_shared = "jti-must-be-globally-unique"
        jti_a = "jti-tenant-a-unique"
        jti_b = "jti-tenant-b-unique"
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        
        # Register unique JTI for tenant A
        result_a = await store.register(jti_a, ttl_seconds=3600, tenant_id=tenant_a)
        assert result_a is True, "First registration should succeed"
        
        # Register different unique JTI for tenant B (should succeed - different JTI)
        result_b = await store.register(jti_b, ttl_seconds=3600, tenant_id=tenant_b)
        assert result_b is True, "Different JTI for different tenant should succeed"
        
        # Try to register already-used JTI for different tenant (should fail - replay protection)
        result_replay = await store.register(jti_a, ttl_seconds=3600, tenant_id=tenant_b)
        assert result_replay is False, "Same JTI cannot be reused across tenants (protects superadmin tokens)"
        
        # Verify tenant A's JTI is still marked as replayed
        is_replayed = await store.is_replayed(jti_a)
        assert is_replayed is True, "JTI should remain in replay store"


@pytest.mark.db
@pytest.mark.asyncio
class TestDatabaseReplayStoreCleanup:
    """TEST-DB-12: Replay store cleanup and maintenance."""
    
    async def test_cleanup_expired_removes_old_entries(self, db_session):
        """Test cleanup_expired removes expired tokens."""
        store = DatabaseReplayStore(db_session)
        
        # Register multiple tokens with varying TTLs
        await store.register("jti-short-1", ttl_seconds=1)
        await store.register("jti-short-2", ttl_seconds=1)
        await store.register("jti-long-1", ttl_seconds=3600)
        await store.register("jti-long-2", ttl_seconds=3600)
        
        # Wait for short TTL tokens to expire
        time.sleep(1.1)
        
        # Run cleanup
        deleted_count = await store.cleanup_expired()
        
        # Should delete 2 expired tokens
        assert deleted_count == 2
        
        # Verify long TTL tokens still exist
        assert await store.is_replayed("jti-long-1") is True
        assert await store.is_replayed("jti-long-2") is True
        
        # Verify short TTL tokens removed
        assert await store.is_replayed("jti-short-1") is False
        assert await store.is_replayed("jti-short-2") is False
    
    async def test_cleanup_expired_no_entries(self, db_session):
        """Test cleanup with no expired entries returns 0."""
        store = DatabaseReplayStore(db_session)
        
        # Register only long-lived tokens
        await store.register("jti-active-1", ttl_seconds=3600)
        await store.register("jti-active-2", ttl_seconds=3600)
        
        # Run cleanup
        deleted_count = await store.cleanup_expired()
        
        # No tokens should be deleted
        assert deleted_count == 0
    
    async def test_count_active_records(self, db_session):
        """Test count_active returns correct count of non-expired tokens."""
        # Clean up any residual data for test isolation
        from sqlalchemy import delete
        await db_session.execute(delete(TokenReplayRecordModel))
        await db_session.commit()
        
        store = DatabaseReplayStore(db_session)
        
        # Register mixed tokens
        await store.register("jti-expire-1", ttl_seconds=1)
        await store.register("jti-active-1", ttl_seconds=3600)
        await store.register("jti-active-2", ttl_seconds=3600)
        
        # Count active (all 3 should be active initially)
        count_before = await store.count_active()
        assert count_before == 3
        
        # Wait for one to expire
        time.sleep(1.1)
        
        # Count active (should be 2 now)
        count_after = await store.count_active()
        assert count_after == 2
    
    async def test_count_active_by_tenant(self, db_session):
        """Test count_active filters by tenant."""
        # Clean up any residual data for test isolation
        from sqlalchemy import delete
        await db_session.execute(delete(TokenReplayRecordModel))
        await db_session.commit()
        
        store = DatabaseReplayStore(db_session)
        
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        
        # Register tokens for different tenants
        await store.register("jti-a-1", ttl_seconds=3600, tenant_id=tenant_a)
        await store.register("jti-a-2", ttl_seconds=3600, tenant_id=tenant_a)
        await store.register("jti-b-1", ttl_seconds=3600, tenant_id=tenant_b)
        await store.register("jti-none-1", ttl_seconds=3600, tenant_id=None)
        
        # Count for tenant A
        count_a = await store.count_active(tenant_id=tenant_a)
        assert count_a == 2
        
        # Count for tenant B
        count_b = await store.count_active(tenant_id=tenant_b)
        assert count_b == 1
        
        # Count all (no tenant filter)
        count_all = await store.count_active()
        assert count_all == 4


@pytest.mark.db
@pytest.mark.asyncio
class TestDatabaseReplayStoreEdgeCases:
    """TEST-DB-12: Edge cases and race conditions."""
    
    async def test_concurrent_registration_same_jti(self, db_session):
        """
        Test concurrent registration attempts for same JTI.
        
        Validates atomicity - only one should succeed (FR-SEC-020).
        
        Note: This is a simplified test. In production, use concurrent asyncio tasks.
        """
        store = DatabaseReplayStore(db_session)
        
        jti = "jti-concurrent-test"
        
        # First registration
        result1 = await store.register(jti, ttl_seconds=3600)
        assert result1 is True
        
        # Immediate second attempt (should fail due to existing entry)
        result2 = await store.register(jti, ttl_seconds=3600)
        assert result2 is False
    
    async def test_very_short_ttl(self, db_session):
        """Test tokens with very short TTL (edge case)."""
        store = DatabaseReplayStore(db_session)
        
        jti = "jti-short-ttl"
        
        # Register with 0.1 second TTL
        result1 = await store.register(jti, ttl_seconds=0.1)
        assert result1 is True
        
        # Immediate check (should be replay)
        result2 = await store.register(jti, ttl_seconds=3600)
        assert result2 is False
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be able to register again
        result3 = await store.register(jti, ttl_seconds=3600)
        assert result3 is True
    
    async def test_empty_jti_handled(self, db_session):
        """Test empty JTI string handled gracefully."""
        store = DatabaseReplayStore(db_session)
        
        # Empty JTI should be treated as valid (edge case)
        result = await store.register("", ttl_seconds=3600)
        assert result is True
        
        # Second empty JTI should be replay
        result2 = await store.register("", ttl_seconds=3600)
        assert result2 is False


class TestInMemoryReplayStoreParity:
    """
    Validate in-memory store behavior matches expected replay semantics.
    
    Ensures consistency between implementations.
    """
    
    def test_in_memory_first_registration_succeeds(self):
        """Test in-memory first registration succeeds."""
        store = InMemoryReplayStore()
        
        result = store.register("jti-test", ttl_seconds=3600)
        assert result is True
    
    def test_in_memory_second_registration_fails(self):
        """Test in-memory second registration fails (replay)."""
        store = InMemoryReplayStore()
        
        jti = "jti-replay"
        
        result1 = store.register(jti, ttl_seconds=3600)
        assert result1 is True
        
        result2 = store.register(jti, ttl_seconds=3600)
        assert result2 is False
    
    def test_in_memory_expired_can_reregister(self):
        """Test in-memory expired token can be re-registered."""
        store = InMemoryReplayStore()
        
        jti = "jti-expire"
        
        result1 = store.register(jti, ttl_seconds=1)
        assert result1 is True
        
        time.sleep(1.1)
        
        result2 = store.register(jti, ttl_seconds=3600)
        assert result2 is True


# TODO (Phase 4): Add concurrent registration test with asyncio.gather
# TODO (Phase 4): Add load test with 10,000+ tokens
# TODO (Phase 4): Add migration test for token_replay_records table
