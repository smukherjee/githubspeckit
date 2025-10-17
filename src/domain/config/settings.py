"""
Typed configuration settings (Constitution VII: Unified Configuration).

This module provides typed configuration classes that are populated from
the descriptor.toml via descriptor_parser. All environment variable access
MUST go through this module or descriptor_parser only.

Usage:
    from domain.config.settings import get_observability_settings
    settings = get_observability_settings()
    if settings.otel_endpoint:
        # Use endpoint
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from .descriptor_parser import parse_descriptor


@dataclass(frozen=True)
class ObservabilitySettings:
    """Observability and tracing configuration (FR-034, FR-071)."""
    
    otel_exporter_otlp_endpoint: Optional[str] = None
    log_level: str = "INFO"
    log_format: str = "json"
    
    @classmethod
    def from_descriptor(cls, descriptor_path: str | Path = "config/descriptor.toml") -> ObservabilitySettings:
        """Load settings from descriptor."""
        raw_config = parse_descriptor(descriptor_path)
        return cls(
            otel_exporter_otlp_endpoint=raw_config.get("OTEL_EXPORTER_OTLP_ENDPOINT", (None, False))[0],
            log_level=raw_config.get("LOG_LEVEL", ("INFO", False))[0],
            log_format=raw_config.get("LOG_FORMAT", ("json", False))[0],
        )


@dataclass(frozen=True)
class DatabaseSettings:
    """Database configuration (FR-039, Phase 3)."""
    
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_slow_query_threshold_ms: int = 100
    
    @classmethod
    def from_descriptor(cls, descriptor_path: str | Path = "config/descriptor.toml") -> DatabaseSettings:
        """Load settings from descriptor."""
        raw_config = parse_descriptor(descriptor_path)
        
        db_url_tuple = raw_config.get("DATABASE_URL")
        if not db_url_tuple:
            raise ValueError("DATABASE_URL is required but not set")
        
        return cls(
            database_url=db_url_tuple[0],
            db_pool_size=raw_config.get("DB_POOL_SIZE", (10, False))[0],
            db_max_overflow=raw_config.get("DB_MAX_OVERFLOW", (20, False))[0],
            db_pool_timeout=raw_config.get("DB_POOL_TIMEOUT", (30, False))[0],
            db_slow_query_threshold_ms=raw_config.get("DB_SLOW_QUERY_THRESHOLD_MS", (100, False))[0],
        )


# Singleton instances (lazy-loaded)
_observability_settings: Optional[ObservabilitySettings] = None
_database_settings: Optional[DatabaseSettings] = None


def get_observability_settings(descriptor_path: str | Path = "config/descriptor.toml") -> ObservabilitySettings:
    """
    Get observability settings singleton.
    
    Args:
        descriptor_path: Path to descriptor.toml (default: config/descriptor.toml)
    
    Returns:
        ObservabilitySettings instance
    """
    global _observability_settings
    if _observability_settings is None:
        _observability_settings = ObservabilitySettings.from_descriptor(descriptor_path)
    return _observability_settings


def get_database_settings(descriptor_path: str | Path = "config/descriptor.toml") -> DatabaseSettings:
    """
    Get database settings singleton.
    
    Args:
        descriptor_path: Path to descriptor.toml (default: config/descriptor.toml)
    
    Returns:
        DatabaseSettings instance
    
    Raises:
        ValueError: If DATABASE_URL not configured
    """
    global _database_settings
    if _database_settings is None:
        _database_settings = DatabaseSettings.from_descriptor(descriptor_path)
    return _database_settings


__all__ = [
    "ObservabilitySettings",
    "DatabaseSettings",
    "get_observability_settings",
    "get_database_settings",
]
