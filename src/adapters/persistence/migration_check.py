"""
IMPL-DB-15: Startup migration head check and health endpoint integration.

Provides:
- Alembic migration head validation on startup (FR-015)
- Health endpoint exposing current database revision
- Migration mismatch detection and startup abort logic
- Integration with observability for drift alerts

Status: Phase 3 Lane DB-G
Dependencies: Alembic, health endpoint infrastructure
"""
from __future__ import annotations

import logging
from typing import Optional
from alembic import command, script
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("infra.persistence.migration_check")


class MigrationHeadMismatchError(Exception):
    """
    Raised when database revision does not match Alembic head.
    
    Indicates migrations are pending or database is ahead of code.
    """
    pass


async def get_current_revision(engine: AsyncEngine) -> Optional[str]:
    """
    Get current database migration revision from alembic_version table.
    
    Args:
        engine: SQLAlchemy async engine
    
    Returns:
        Current revision hash, or None if alembic_version table doesn't exist
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            if row:
                return row[0]
            return None
    except Exception as e:
        logger.warning(f"Failed to query alembic_version: {e}")
        return None


def get_head_revision(alembic_config_path: str = "alembic.ini") -> str:
    """
    Get head revision from Alembic configuration.
    
    Args:
        alembic_config_path: Path to alembic.ini
    
    Returns:
        Head revision hash
    """
    config = Config(alembic_config_path)
    script_dir = script.ScriptDirectory.from_config(config)
    head = script_dir.get_current_head()
    return head


async def check_migration_head(
    engine: AsyncEngine,
    alembic_config_path: str = "alembic.ini",
    abort_on_mismatch: bool = True,
) -> dict[str, str | bool]:
    """
    Check if database revision matches Alembic head (FR-015).
    
    Validates:
    - Current database revision retrieved successfully
    - Head revision from Alembic configuration
    - Revisions match (database is up-to-date)
    
    Args:
        engine: SQLAlchemy async engine
        alembic_config_path: Path to alembic.ini (default: "alembic.ini")
        abort_on_mismatch: If True, raise exception on mismatch (default: True)
    
    Returns:
        Dictionary with:
        - current_revision: Current database revision
        - head_revision: Expected head revision
        - is_up_to_date: Boolean indicating match
    
    Raises:
        MigrationHeadMismatchError: If revisions don't match and abort_on_mismatch=True
    """
    current = await get_current_revision(engine)
    head = get_head_revision(alembic_config_path)
    
    is_up_to_date = current == head
    
    result = {
        "current_revision": current or "NONE",
        "head_revision": head,
        "is_up_to_date": is_up_to_date,
    }
    
    if not is_up_to_date:
        logger.error(
            f"Migration head mismatch detected! Current: {current}, Head: {head}",
            extra={
                "category": "infra.persistence.migration_mismatch",
                "current_revision": current,
                "head_revision": head,
            },
        )
        
        if abort_on_mismatch:
            raise MigrationHeadMismatchError(
                f"Database revision ({current}) does not match head ({head}). "
                f"Run 'alembic upgrade head' before starting the application."
            )
    else:
        logger.info(
            f"Migration head check passed. Revision: {current}",
            extra={
                "category": "infra.persistence.migration_check",
                "revision": current,
            },
        )
    
    return result


async def startup_migration_check(engine: AsyncEngine) -> None:
    """
    Perform migration head check during application startup (FR-015).
    
    Aborts startup if database is not up-to-date.
    
    Args:
        engine: SQLAlchemy async engine
    
    Raises:
        MigrationHeadMismatchError: If migrations are pending
    
    Usage:
        # In main.py or startup event
        from adapters.persistence.migration_check import startup_migration_check
        
        @app.on_event("startup")
        async def check_migrations():
            await startup_migration_check(engine)
    """
    await check_migration_head(engine, abort_on_mismatch=True)


def health_check_migration_status(engine: AsyncEngine) -> dict[str, str | bool]:
    """
    Get migration status for health endpoint (FR-015).
    
    Non-async wrapper for health endpoint integration.
    
    Args:
        engine: SQLAlchemy async engine
    
    Returns:
        Migration status dictionary
    
    Usage:
        # In health endpoint
        @app.get("/health")
        def health():
            migration_status = health_check_migration_status(engine)
            return {
                "status": "healthy" if migration_status["is_up_to_date"] else "degraded",
                "database": migration_status,
            }
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            check_migration_head(engine, abort_on_mismatch=False)
        )
        return result
    except Exception as e:
        logger.exception("Failed to check migration status")
        return {
            "current_revision": "ERROR",
            "head_revision": "ERROR",
            "is_up_to_date": False,
            "error": str(e),
        }


# TODO (Phase 4): Add Prometheus metric for migration drift
# TODO (Phase 4): Add alerting for migration mismatch in production
# TODO (Phase 4): Add automatic migration on startup (opt-in, for dev environments only)
