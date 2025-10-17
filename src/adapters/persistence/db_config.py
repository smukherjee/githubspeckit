"""
Database configuration and abstraction layer.

Provides centralized database configuration with support for multiple backends:
- PostgreSQL (primary, production)
- SQLite (local dev, testing)
- MySQL (future support)

Constitution Section IV: "Swappable implementations: SQLAlchemy (PostgreSQL primary),
optional in-memory (tests), SQLite (local dev), and future cloud variants."

This module handles:
- Database URL parsing and validation
- Dialect detection and feature detection
- Type mapping across databases (UUID, JSON, etc.)
- Connection pool configuration per database type
- Migration compatibility checks

Architecture:
- Single source of configuration truth
- Automatic dialect detection from URL
- Portable type definitions
- Future-proof for additional databases
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional, TYPE_CHECKING
from urllib.parse import urlparse

from sqlalchemy import String, TypeDecorator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

if TYPE_CHECKING:
    from sqlalchemy.engine import URL


class DatabaseDialect(str, Enum):
    """Supported database dialects."""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"


class DatabaseConfig:
    """
    Centralized database configuration.
    
    Auto-detects dialect from DATABASE_URL and provides dialect-specific settings.
    
    Usage:
        config = DatabaseConfig.from_env()
        engine = config.create_engine()
        if config.supports_uuid:
            # Use native UUID type
        else:
            # Use string-based UUID
    """
    
    def __init__(
        self,
        url: str,
        dialect: DatabaseDialect,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        self.url = url
        self.dialect = dialect
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
    
    @classmethod
    def from_env(cls, env_var: str = "DATABASE_URL") -> DatabaseConfig:
        """
        Create configuration from DATABASE_URL (via config settings).
        
        Constitution VII Compliance: Uses domain.config.settings instead of direct os.getenv.
        
        Args:
            env_var: Environment variable name (default: DATABASE_URL, ignored - always uses settings)
        
        Returns:
            DatabaseConfig instance with auto-detected dialect
        
        Raises:
            ValueError: If DATABASE_URL is not set in configuration
        """
        from domain.config.settings import get_database_settings
        settings = get_database_settings()
        return cls.from_url(settings.database_url)
    
    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> DatabaseConfig:
        """
        Create configuration from database URL.
        
        Args:
            url: Database connection URL
            **kwargs: Additional configuration options
        
        Returns:
            DatabaseConfig instance with auto-detected dialect
        """
        dialect = cls._detect_dialect(url)
        
        # Set dialect-specific defaults
        defaults = cls._get_dialect_defaults(dialect)
        defaults.update(kwargs)
        
        return cls(url=url, dialect=dialect, **defaults)
    
    @staticmethod
    def _detect_dialect(url: str) -> DatabaseDialect:
        """
        Detect database dialect from URL scheme.
        
        Supported URL patterns:
        - postgresql:// or postgresql+asyncpg:// → PostgreSQL
        - sqlite:// or sqlite+aiosqlite:// → SQLite
        - mysql:// or mysql+aiomysql:// → MySQL
        """
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        # Handle driver-specific schemes (e.g., postgresql+asyncpg)
        base_scheme = scheme.split('+')[0]
        
        if base_scheme == 'postgresql':
            return DatabaseDialect.POSTGRESQL
        elif base_scheme == 'sqlite':
            return DatabaseDialect.SQLITE
        elif base_scheme == 'mysql':
            return DatabaseDialect.MYSQL
        else:
            raise ValueError(
                f"Unsupported database scheme: {scheme}. "
                f"Supported: postgresql, sqlite, mysql"
            )
    
    @staticmethod
    def _get_dialect_defaults(dialect: DatabaseDialect) -> dict[str, Any]:
        """Get default configuration for dialect."""
        if dialect == DatabaseDialect.POSTGRESQL:
            return {
                "echo": False,
                "pool_size": 5,
                "max_overflow": 10,
            }
        elif dialect == DatabaseDialect.SQLITE:
            return {
                "echo": False,
                "pool_size": 1,  # SQLite doesn't benefit from connection pooling
                "max_overflow": 0,
            }
        elif dialect == DatabaseDialect.MYSQL:
            return {
                "echo": False,
                "pool_size": 5,
                "max_overflow": 10,
            }
        
        return {}
    
    def create_engine(self, **override_kwargs: Any) -> AsyncEngine:
        """
        Create async SQLAlchemy engine with dialect-specific settings.
        
        Args:
            **override_kwargs: Override default engine settings
        
        Returns:
            Configured AsyncEngine instance
        """
        kwargs: dict[str, Any] = {
            "echo": self.echo,
            "pool_pre_ping": True,  # Verify connections before use
        }
        
        # Add dialect-specific options
        if self.dialect == DatabaseDialect.POSTGRESQL:
            kwargs["pool_size"] = self.pool_size
            kwargs["max_overflow"] = self.max_overflow
        elif self.dialect == DatabaseDialect.SQLITE:
            # SQLite-specific: enable foreign keys, shared cache
            kwargs["connect_args"] = {
                "check_same_thread": False,  # Allow multi-threaded access
            }
            # Note: pool_size=1 is implicit for SQLite in SQLAlchemy
        elif self.dialect == DatabaseDialect.MYSQL:
            kwargs["pool_size"] = self.pool_size
            kwargs["max_overflow"] = self.max_overflow
        
        # Apply overrides
        kwargs.update(override_kwargs)
        
        return create_async_engine(self.url, **kwargs)
    
    @property
    def supports_uuid(self) -> bool:
        """Check if database has native UUID support."""
        return self.dialect == DatabaseDialect.POSTGRESQL
    
    @property
    def supports_json(self) -> bool:
        """Check if database has native JSON support."""
        return self.dialect in (
            DatabaseDialect.POSTGRESQL,
            DatabaseDialect.MYSQL,
            DatabaseDialect.SQLITE,  # SQLite 3.38+
        )
    
    @property
    def supports_arrays(self) -> bool:
        """Check if database has native array support."""
        return self.dialect == DatabaseDialect.POSTGRESQL
    
    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return self.dialect == DatabaseDialect.POSTGRESQL
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return self.dialect == DatabaseDialect.SQLITE
    
    @property
    def is_mysql(self) -> bool:
        """Check if using MySQL."""
        return self.dialect == DatabaseDialect.MYSQL
    
    def get_alembic_script_location(self) -> str:
        """Get Alembic script location for this dialect."""
        return "alembic"  # Same location for all dialects
    
    def get_migration_table_name(self) -> str:
        """Get Alembic version table name."""
        return "alembic_version"


class PortableUUID(TypeDecorator[Any]):
    """
    Portable UUID type that works across databases.
    
    - PostgreSQL: Uses native UUID type
    - SQLite/MySQL: Uses CHAR(36) with string conversion
    
    This ensures UUIDs work consistently across all supported databases
    without requiring schema changes when switching backends.
    """
    impl = String(36)
    cache_ok = True
    
    def load_dialect_impl(self, dialect: Any) -> Any:
        """Choose appropriate type based on dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """Convert UUID to string for non-PostgreSQL databases."""
        if value is None:
            return None
        
        if dialect.name == 'postgresql':
            return value  # PostgreSQL handles UUID objects natively
        else:
            # Convert UUID to string for SQLite/MySQL
            return str(value) if hasattr(value, 'hex') else value
    
    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Convert string back to UUID for non-PostgreSQL databases."""
        if value is None:
            return None
        
        if dialect.name == 'postgresql':
            return value  # Already a UUID object
        else:
            # Parse string to UUID for SQLite/MySQL
            from uuid import UUID
            return UUID(value) if isinstance(value, str) else value


# Global configuration instance (lazy initialization)
_db_config: Optional[DatabaseConfig] = None


def get_db_config(reload: bool = False) -> DatabaseConfig:
    """
    Get global database configuration instance.
    
    Args:
        reload: Force reload from environment
    
    Returns:
        DatabaseConfig instance
    
    Example:
        config = get_db_config()
        engine = config.create_engine()
    """
    global _db_config
    
    if _db_config is None or reload:
        _db_config = DatabaseConfig.from_env()
    
    return _db_config


def get_database_url(default: Optional[str] = None) -> str:
    """
    Get database URL from configuration settings.
    
    Constitution VII Compliance: Uses domain.config.settings which respects:
    1. DATABASE_URL environment variable (highest priority)
    2. config/descriptor.toml default (SQLite for local dev)
    
    Args:
        default: Deprecated parameter (kept for backwards compatibility, ignored)
    
    Returns:
        Database connection URL (from env var or descriptor default)
    
    Note:
        The descriptor.toml default is SQLite for developer-friendly local testing.
        For production/PostgreSQL, set DATABASE_URL environment variable.
    """
    from src.domain.config.settings import get_database_settings
    settings = get_database_settings()
    return settings.database_url


__all__ = [
    "DatabaseConfig",
    "DatabaseDialect",
    "PortableUUID",
    "get_db_config",
    "get_database_url",
]
