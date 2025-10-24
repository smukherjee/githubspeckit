"""
Test database abstraction layer.

Validates constitution Section IV compliance:
"Swappable implementations: SQLAlchemy (PostgreSQL primary),
optional in-memory (tests), SQLite (local dev), and future cloud variants."

This test suite verifies:
- DatabaseConfig correctly detects dialect from URL
- PortableUUID works across PostgreSQL and SQLite
- Engine creation succeeds for all supported databases
- Dialect-specific features are correctly detected
- Future MySQL support can be added seamlessly

Status: Constitution validation
"""
from __future__ import annotations

import pytest
from uuid import uuid4
import sys

from adapters.persistence.db_config import (
    DatabaseConfig,
    DatabaseDialect,
    PortableUUID,
    get_database_url,
)


class TestDatabaseConfigDetection:
    """Test database dialect detection from URLs."""
    
    def test_detect_postgresql_url(self):
        """PostgreSQL URLs should be detected correctly."""
        urls = [
            "postgresql://user:pass@localhost/db",
            "postgresql+asyncpg://user:pass@localhost/db",
        ]
        
        for url in urls:
            config = DatabaseConfig.from_url(url)
            assert config.dialect == DatabaseDialect.POSTGRESQL
            assert config.is_postgres
            # V1.0: SQLite support removed, is_sqlite property no longer exists
            assert not config.is_mysql
    
    @pytest.mark.skip(reason="V1.0: SQLite support disabled - PostgreSQL only")
    def test_detect_sqlite_url(self):
        """SQLite URLs should be detected correctly."""
        urls = [
            "sqlite:///./test.db",
            "sqlite+aiosqlite:///./test.db",
        ]
        
        for url in urls:
            config = DatabaseConfig.from_url(url)
            assert config.dialect == DatabaseDialect.SQLITE
            assert config.is_sqlite
            assert not config.is_postgres
            assert not config.is_mysql
    
    def test_detect_mysql_url(self):
        """MySQL URLs should be detected correctly (future support)."""
        urls = [
            "mysql://user:pass@localhost/db",
            "mysql+aiomysql://user:pass@localhost/db",
        ]
        
        for url in urls:
            config = DatabaseConfig.from_url(url)
            assert config.dialect == DatabaseDialect.MYSQL
            assert config.is_mysql
            assert not config.is_postgres
            # V1.0: SQLite support removed, is_sqlite property no longer exists
    
    def test_unsupported_database_raises_error(self):
        """Unsupported database schemes should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported database scheme"):
            DatabaseConfig.from_url("oracle://user:pass@localhost/db")


class TestDatabaseFeatureDetection:
    """Test dialect-specific feature detection."""
    
    def test_postgresql_features(self):
        """PostgreSQL supports UUID, JSON, and arrays."""
        config = DatabaseConfig.from_url("postgresql://localhost/db")
        
        assert config.supports_uuid is True
        assert config.supports_json is True
        assert config.supports_arrays is True
    
    @pytest.mark.skip(reason="V1.0: SQLite support disabled - PostgreSQL only")
    def test_sqlite_features(self):
        """SQLite supports JSON but not native UUID or arrays."""
        config = DatabaseConfig.from_url("sqlite:///./test.db")
        
        assert config.supports_uuid is False
        assert config.supports_json is True  # SQLite 3.38+
        assert config.supports_arrays is False
    
    def test_mysql_features(self):
        """MySQL supports JSON but not native UUID or arrays."""
        config = DatabaseConfig.from_url("mysql://localhost/db")
        
        assert config.supports_uuid is False
        assert config.supports_json is True
        assert config.supports_arrays is False


class TestEngineCreation:
    """Test engine creation with dialect-specific settings."""
    
    def test_postgresql_engine_settings(self):
        """PostgreSQL engine should have connection pooling."""
        config = DatabaseConfig.from_url(
            "postgresql+asyncpg://user:pass@localhost/db",
            pool_size=10,
            max_overflow=20,
        )
        
        engine = config.create_engine()
        assert engine is not None
        # Connection pooling should be configured (can't easily test without connecting)
    
    @pytest.mark.skip(reason="V1.0: SQLite support disabled - PostgreSQL only")
    def test_sqlite_engine_settings(self):
        """SQLite engine should have minimal pooling."""
        config = DatabaseConfig.from_url("sqlite+aiosqlite:///./test.db")
        
        engine = config.create_engine()
        assert engine is not None
        # SQLite uses single connection (can't easily test without connecting)
    
    @pytest.mark.skipif(
        "psycopg2" not in sys.modules and "asyncpg" not in sys.modules,
        reason="Requires psycopg2 or asyncpg for PostgreSQL"
    )
    def test_engine_override_settings(self):
        """Engine creation should respect override kwargs."""
        config = DatabaseConfig.from_url("postgresql://localhost/db")
        
        # Override echo setting
        engine = config.create_engine(echo=True)
        assert engine is not None


class TestPortableUUID:
    """Test PortableUUID type converter."""
    
    def test_portable_uuid_initialization(self):
        """PortableUUID should initialize correctly."""
        uuid_type = PortableUUID()
        assert uuid_type is not None
        assert uuid_type.cache_ok is True
    
    def test_uuid_string_conversion(self):
        """UUID should convert to string for non-PostgreSQL databases."""
        uuid_type = PortableUUID()
        test_uuid = uuid4()
        
        # Mock SQLite dialect
        class MockDialect:
            name = "sqlite"
        
        dialect = MockDialect()
        result = uuid_type.process_bind_param(test_uuid, dialect)
        
        assert isinstance(result, str)
        assert result == str(test_uuid)
    
    def test_uuid_postgresql_passthrough(self):
        """UUID should pass through unchanged for PostgreSQL."""
        uuid_type = PortableUUID()
        test_uuid = uuid4()
        
        # Mock PostgreSQL dialect
        class MockDialect:
            name = "postgresql"
        
        dialect = MockDialect()
        result = uuid_type.process_bind_param(test_uuid, dialect)
        
        # PostgreSQL handles UUID objects natively
        assert result == test_uuid
    
    def test_uuid_none_handling(self):
        """None values should pass through unchanged."""
        uuid_type = PortableUUID()
        
        class MockDialect:
            name = "sqlite"
        
        dialect = MockDialect()
        result = uuid_type.process_bind_param(None, dialect)
        
        assert result is None


class TestDatabaseURLHelper:
    """Test database URL retrieval helper."""
    
    def test_get_database_url_with_default(self):
        """Should return default when DATABASE_URL not set."""
        default_url = "sqlite:///./test.db"
        url = get_database_url(default=default_url)
        
        # Will use environment variable or fallback to default
        assert url is not None
        assert isinstance(url, str)
    
    def test_get_database_url_no_default_raises_error(self):
        """
        Should return database URL from configuration (env var or descriptor.toml default).
        
        Constitution VII compliance: get_database_url() uses centralized config:
        1. DATABASE_URL env var (if set)
        2. descriptor.toml default (PostgreSQL for V1.0)
        3. Never raises error (always has a default)
        """
        import os
        
        # Test respects env var when set
        if "DATABASE_URL" in os.environ:
            url = get_database_url(default=None)
            assert url == os.environ["DATABASE_URL"]
        else:
            # V1.0: PostgreSQL required, no SQLite fallback
            url = get_database_url(default=None)
            assert url is not None
            assert "postgresql" in url.lower(), f"Expected PostgreSQL URL from config, got: {url}"


class TestConstitutionCompliance:
    """Validate constitution Section IV requirements."""
    
    def test_supports_postgresql_primary(self):
        """PostgreSQL must be supported as primary database."""
        config = DatabaseConfig.from_url("postgresql+asyncpg://localhost/db")
        assert config.is_postgres
        
        # Should create engine successfully
        engine = config.create_engine()
        assert engine is not None
    
    @pytest.mark.skip(reason="V1.0: SQLite support disabled - PostgreSQL only for production readiness")
    def test_supports_sqlite_local_dev(self):
        """SQLite must be supported for local development."""
        config = DatabaseConfig.from_url("sqlite+aiosqlite:///./dev.db")
        assert config.is_sqlite
        
        # Should create engine successfully
        engine = config.create_engine()
        assert engine is not None
    
    @pytest.mark.skipif(
        "aiomysql" not in sys.modules,
        reason="Requires aiomysql for MySQL support"
    )
    def test_future_mysql_support_ready(self):
        """MySQL detection should work (implementation pending)."""
        config = DatabaseConfig.from_url("mysql+aiomysql://localhost/db")
        assert config.is_mysql
        
        # Engine creation should not fail
        engine = config.create_engine()
        assert engine is not None
    
    def test_portable_uuid_works_across_databases(self):
        """PortableUUID should work with all supported databases."""
        uuid_type = PortableUUID()
        test_uuid = uuid4()
        
        # Test with each dialect
        for dialect_name in ["postgresql", "sqlite", "mysql"]:
            class MockDialect:
                name = dialect_name
            
            dialect = MockDialect()
            
            # Bind parameter should not raise
            bound = uuid_type.process_bind_param(test_uuid, dialect)
            assert bound is not None
            
            # Result value should not raise
            if dialect_name == "postgresql":
                result = uuid_type.process_result_value(test_uuid, dialect)
            else:
                result = uuid_type.process_result_value(str(test_uuid), dialect)
            
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
