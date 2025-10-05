"""
TEST-DB-15A: Startup migration head check tests.

Validates:
- Migration head mismatch detection (IMPL-DB-15, FR-015)
- Startup abort on mismatch
- Health endpoint integration
- Revision exposure

Status: Phase 3 Lane DB-G
Dependencies: IMPL-DB-15 (migration_check module)
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from adapters.persistence.migration_check import (
    check_migration_head,
    MigrationHeadMismatchError,
    get_head_revision,
    startup_migration_check,
)


class TestMigrationHeadCheck:
    """TEST-DB-15A: Migration head check validation."""
    
    @pytest.mark.asyncio
    async def test_matching_revisions_success(self):
        """Test matching revisions pass check (FR-015)."""
        mock_engine = AsyncMock()
        
        # Mock database returning same revision as head
        with patch("adapters.persistence.migration_check.get_current_revision") as mock_current, \
             patch("adapters.persistence.migration_check.get_head_revision") as mock_head:
            
            mock_current.return_value = "abc123"
            mock_head.return_value = "abc123"
            
            result = await check_migration_head(mock_engine, abort_on_mismatch=False)
            
            assert result["current_revision"] == "abc123"
            assert result["head_revision"] == "abc123"
            assert result["is_up_to_date"] is True
    
    @pytest.mark.asyncio
    async def test_mismatched_revisions_detected(self):
        """Test mismatched revisions detected (FR-015)."""
        mock_engine = AsyncMock()
        
        # Mock database behind head
        with patch("adapters.persistence.migration_check.get_current_revision") as mock_current, \
             patch("adapters.persistence.migration_check.get_head_revision") as mock_head:
            
            mock_current.return_value = "old123"
            mock_head.return_value = "new456"
            
            result = await check_migration_head(mock_engine, abort_on_mismatch=False)
            
            assert result["current_revision"] == "old123"
            assert result["head_revision"] == "new456"
            assert result["is_up_to_date"] is False
    
    @pytest.mark.asyncio
    async def test_mismatch_aborts_startup_by_default(self):
        """Test startup aborts on mismatch when abort_on_mismatch=True (FR-015)."""
        mock_engine = AsyncMock()
        
        # Mock database behind head
        with patch("adapters.persistence.migration_check.get_current_revision") as mock_current, \
             patch("adapters.persistence.migration_check.get_head_revision") as mock_head:
            
            mock_current.return_value = "old123"
            mock_head.return_value = "new456"
            
            # Should raise exception
            with pytest.raises(MigrationHeadMismatchError) as exc_info:
                await check_migration_head(mock_engine, abort_on_mismatch=True)
            
            assert "old123" in str(exc_info.value)
            assert "new456" in str(exc_info.value)
            assert "alembic upgrade head" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_no_revision_in_database(self):
        """Test handling of fresh database with no alembic_version table."""
        mock_engine = AsyncMock()
        
        # Mock database with no revision (fresh DB)
        with patch("adapters.persistence.migration_check.get_current_revision") as mock_current, \
             patch("adapters.persistence.migration_check.get_head_revision") as mock_head:
            
            mock_current.return_value = None
            mock_head.return_value = "abc123"
            
            result = await check_migration_head(mock_engine, abort_on_mismatch=False)
            
            assert result["current_revision"] == "NONE"
            assert result["head_revision"] == "abc123"
            assert result["is_up_to_date"] is False


class TestStartupMigrationCheck:
    """TEST-DB-15A: Startup integration tests."""
    
    @pytest.mark.asyncio
    async def test_startup_check_passes_when_up_to_date(self):
        """Test startup check passes when database is up-to-date."""
        mock_engine = AsyncMock()
        
        with patch("adapters.persistence.migration_check.get_current_revision") as mock_current, \
             patch("adapters.persistence.migration_check.get_head_revision") as mock_head:
            
            mock_current.return_value = "abc123"
            mock_head.return_value = "abc123"
            
            # Should not raise
            await startup_migration_check(mock_engine)
    
    @pytest.mark.asyncio
    async def test_startup_check_fails_when_behind(self):
        """Test startup check fails when database is behind head (FR-015)."""
        mock_engine = AsyncMock()
        
        with patch("adapters.persistence.migration_check.get_current_revision") as mock_current, \
             patch("adapters.persistence.migration_check.get_head_revision") as mock_head:
            
            mock_current.return_value = "old123"
            mock_head.return_value = "new456"
            
            # Should raise and abort startup
            with pytest.raises(MigrationHeadMismatchError):
                await startup_migration_check(mock_engine)


class TestHealthEndpointIntegration:
    """TEST-DB-15A: Health endpoint migration status exposure."""
    
    def test_health_check_returns_status(self):
        """Test health check returns migration status (FR-015)."""
        mock_engine = MagicMock()
        
        with patch("adapters.persistence.migration_check.check_migration_head") as mock_check:
            # Mock async result
            future = AsyncMock()
            future.return_value = {
                "current_revision": "abc123",
                "head_revision": "abc123",
                "is_up_to_date": True,
            }
            
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_until_complete = lambda x: {
                    "current_revision": "abc123",
                    "head_revision": "abc123",
                    "is_up_to_date": True,
                }
                
                from adapters.persistence.migration_check import health_check_migration_status
                result = health_check_migration_status(mock_engine)
                
                assert result["current_revision"] == "abc123"
                assert result["head_revision"] == "abc123"
                assert result["is_up_to_date"] is True
    
    def test_health_check_handles_errors(self):
        """Test health check handles errors gracefully."""
        mock_engine = MagicMock()
        
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = Exception("Database error")
            
            from adapters.persistence.migration_check import health_check_migration_status
            result = health_check_migration_status(mock_engine)
            
            assert result["current_revision"] == "ERROR"
            assert result["head_revision"] == "ERROR"
            assert result["is_up_to_date"] is False
            assert "error" in result


class TestRevisionRetrieval:
    """TEST-DB-15A: Revision retrieval validation."""
    
    def test_get_head_revision_from_config(self):
        """Test head revision retrieved from Alembic config."""
        with patch("adapters.persistence.migration_check.Config") as mock_config, \
             patch("adapters.persistence.migration_check.script.ScriptDirectory") as mock_script_dir:
            
            mock_script = MagicMock()
            mock_script.get_current_head.return_value = "head_abc123"
            mock_script_dir.from_config.return_value = mock_script
            
            result = get_head_revision("alembic.ini")
            
            assert result == "head_abc123"
    
    @pytest.mark.asyncio
    async def test_get_current_revision_queries_database(self):
        """Test current revision queries alembic_version table."""
        from adapters.persistence.migration_check import get_current_revision
        from unittest.mock import MagicMock
        from contextlib import asynccontextmanager
        
        # Create properly structured async mocks
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("current_abc123",)
        
        @asynccontextmanager
        async def mock_connect():
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock(return_value=mock_result)
            yield mock_conn
        
        mock_engine = MagicMock()
        mock_engine.connect = mock_connect
        
        result = await get_current_revision(mock_engine)
        
        assert result == "current_abc123"
    
    @pytest.mark.asyncio
    async def test_get_current_revision_handles_missing_table(self):
        """Test current revision returns None if alembic_version missing."""
        from adapters.persistence.migration_check import get_current_revision
        from unittest.mock import MagicMock
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def mock_connect():
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("relation does not exist"))
            yield mock_conn
        
        mock_engine = MagicMock()
        mock_engine.connect = mock_connect
        
        result = await get_current_revision(mock_engine)
        
        assert result is None


# TODO (Phase 4): Add integration test with real Alembic migrations
# @pytest.mark.db
# @pytest.mark.asyncio
# async def test_migration_check_with_real_database(db_engine):
#     """Test migration check with real database and Alembic."""
#     result = await check_migration_head(db_engine, abort_on_mismatch=False)
#     assert result["is_up_to_date"] is True
