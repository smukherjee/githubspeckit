"""Unit tests for domain/audit/models.py

Tests cover InMemoryAuditAppender to achieve >90% domain coverage.
"""
import pytest
from domain.audit.models import (
    AuditEvent,
    AuditAppender,
    InMemoryAuditAppender
)


class TestInMemoryAuditAppender:
    """Tests for in-memory audit appender."""
    
    def test_append_stores_event(self):
        """Should store audit event in memory."""
        appender = InMemoryAuditAppender()
        event = AuditEvent(
            event_id="evt-1",
            tenant_id="tenant-1",
            category="auth",
            action="user.login",
            actor_user_id="user-1",
            target_type="user",
            target_id="user-1"
        )
        
        appender.append(event)
        
        events = appender.list()
        assert len(events) == 1
        assert events[0] == event
    
    def test_list_returns_all_events_when_no_filter(self):
        """Should return all events when tenant_id not specified."""
        appender = InMemoryAuditAppender()
        event1 = AuditEvent(
            event_id="evt-1",
            tenant_id="tenant-1",
            category="auth",
            action="user.login",
            actor_user_id="user-1",
            target_type="user",
            target_id="user-1"
        )
        event2 = AuditEvent(
            event_id="evt-2",
            tenant_id="tenant-2",
            category="auth",
            action="user.logout",
            actor_user_id="user-2",
            target_type="user",
            target_id="user-2"
        )
        appender.append(event1)
        appender.append(event2)
        
        events = appender.list(tenant_id=None)
        
        assert len(events) == 2
        assert event1 in events
        assert event2 in events
    
    def test_list_filters_by_tenant_id(self):
        """Should return only events for specified tenant."""
        appender = InMemoryAuditAppender()
        event1 = AuditEvent(
            event_id="evt-1",
            tenant_id="tenant-1",
            category="auth",
            action="user.login",
            actor_user_id="user-1",
            target_type="user",
            target_id="user-1"
        )
        event2 = AuditEvent(
            event_id="evt-2",
            tenant_id="tenant-2",
            category="auth",
            action="user.logout",
            actor_user_id="user-2",
            target_type="user",
            target_id="user-2"
        )
        event3 = AuditEvent(
            event_id="evt-3",
            tenant_id="tenant-1",
            category="user",
            action="user.created",
            actor_user_id="user-3",
            target_type="user",
            target_id="user-3"
        )
        appender.append(event1)
        appender.append(event2)
        appender.append(event3)
        
        events = appender.list(tenant_id="tenant-1")
        
        assert len(events) == 2
        assert event1 in events
        assert event3 in events
        assert event2 not in events
    
    def test_list_returns_empty_for_no_matches(self):
        """Should return empty list when no events match filter."""
        appender = InMemoryAuditAppender()
        event = AuditEvent(
            event_id="evt-1",
            tenant_id="tenant-1",
            category="auth",
            action="user.login",
            actor_user_id="user-1",
            target_type="user",
            target_id="user-1"
        )
        appender.append(event)
        
        events = appender.list(tenant_id="tenant-2")
        
        assert events == []


class TestAuditAppenderInterface:
    """Tests for AuditAppender abstract interface."""
    
    def test_append_not_implemented(self):
        """Base class append should raise NotImplementedError."""
        appender = AuditAppender()
        event = AuditEvent(
            event_id="evt-1",
            tenant_id="tenant-1",
            category="test",
            action="test",
            actor_user_id="user-1",
            target_type="test",
            target_id="test-1"
        )
        
        with pytest.raises(NotImplementedError):
            appender.append(event)
