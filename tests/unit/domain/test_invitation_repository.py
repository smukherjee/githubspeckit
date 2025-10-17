"""Unit tests for domain/invitations/models.py

Tests cover InvitationRepository methods to achieve >90% coverage.
"""
import pytest
from datetime import datetime, timezone, timedelta
from domain.invitations.models import (
    Invitation,
    InvitationRepository,
    InvitationStatus
)


class TestInvitationRepository:
    """Tests for in-memory InvitationRepository."""
    
    def test_upsert_stores_invitation(self):
        """Should store invitation and return it."""
        repo = InvitationRepository()
        inv = Invitation(
            invitation_id="inv-123",
            tenant_id="tenant-1",
            email="test@example.com",
            created_by="admin",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        result = repo.upsert(inv)
        
        assert result == inv
        assert repo.get("inv-123") == inv
    
    def test_get_returns_none_for_missing_invitation(self):
        """Should return None for non-existent invitation."""
        repo = InvitationRepository()
        
        result = repo.get("nonexistent")
        
        assert result is None
    
    def test_get_marks_expired_invitation(self):
        """Should auto-expire pending invitations past expiration."""
        repo = InvitationRepository()
        # Create invitation that expired 1 hour ago
        inv = Invitation(
            invitation_id="inv-expired",
            tenant_id="tenant-1",
            email="expired@example.com",
            created_by="admin",
            status=InvitationStatus.pending,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        repo.upsert(inv)
        
        result = repo.get("inv-expired")
        
        assert result is not None
        assert result.status == InvitationStatus.expired
    
    def test_get_does_not_mark_non_pending_as_expired(self):
        """Should not change status of non-pending invitations."""
        repo = InvitationRepository()
        # Create accepted invitation that's past expiration
        inv = Invitation(
            invitation_id="inv-accepted",
            tenant_id="tenant-1",
            email="accepted@example.com",
            created_by="admin",
            status=InvitationStatus.accepted,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        repo.upsert(inv)
        
        result = repo.get("inv-accepted")
        
        assert result is not None
        assert result.status == InvitationStatus.accepted  # Unchanged
    
    def test_list_by_tenant_filters_correctly(self):
        """Should return only invitations for specified tenant."""
        repo = InvitationRepository()
        inv1 = Invitation(
            invitation_id="inv-1",
            tenant_id="tenant-1",
            email="user1@example.com",
            created_by="admin",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        inv2 = Invitation(
            invitation_id="inv-2",
            tenant_id="tenant-2",
            email="user2@example.com",
            created_by="admin",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        inv3 = Invitation(
            invitation_id="inv-3",
            tenant_id="tenant-1",
            email="user3@example.com",
            created_by="admin",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        repo.upsert(inv1)
        repo.upsert(inv2)
        repo.upsert(inv3)
        
        result = repo.list_by_tenant("tenant-1")
        
        assert len(result) == 2
        assert inv1 in result
        assert inv3 in result
        assert inv2 not in result
    
    def test_list_by_tenant_marks_expired_pending_invitations(self):
        """Should auto-expire pending invitations in list results."""
        repo = InvitationRepository()
        inv_valid = Invitation(
            invitation_id="inv-valid",
            tenant_id="tenant-1",
            email="valid@example.com",
            created_by="admin",
            status=InvitationStatus.pending,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        inv_expired = Invitation(
            invitation_id="inv-expired",
            tenant_id="tenant-1",
            email="expired@example.com",
            created_by="admin",
            status=InvitationStatus.pending,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        repo.upsert(inv_valid)
        repo.upsert(inv_expired)
        
        result = repo.list_by_tenant("tenant-1")
        
        assert len(result) == 2
        # Find the expired invitation in results
        expired_result = next(i for i in result if i.invitation_id == "inv-expired")
        assert expired_result.status == InvitationStatus.expired
        
        # Valid invitation should remain pending
        valid_result = next(i for i in result if i.invitation_id == "inv-valid")
        assert valid_result.status == InvitationStatus.pending
    
    def test_list_by_tenant_returns_empty_for_no_matches(self):
        """Should return empty list when tenant has no invitations."""
        repo = InvitationRepository()
        inv = Invitation(
            invitation_id="inv-1",
            tenant_id="tenant-1",
            email="user@example.com",
            created_by="admin",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        repo.upsert(inv)
        
        result = repo.list_by_tenant("tenant-2")
        
        assert result == []
