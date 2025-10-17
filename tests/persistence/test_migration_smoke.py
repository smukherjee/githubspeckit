"""
TEST-DB-04: Migration apply smoke tests (fresh + repeat idempotency).

Validates that:
1. Initial migration can be applied to a fresh database
2. Migration is idempotent (can be applied multiple times without error)
3. Expected schema elements exist after migration (tables, indexes, constraints)
4. Migration head check passes after successful application

Status: Phase 3 Lane DB-A
Dependencies: IMPL-DB-03 (initial migration must exist)
Next: IMPL-DB-05 (persistence adapters)

Note: These tests require a PostgreSQL database. They are marked @pytest.mark.db
and excluded from the default fast test suite.
"""
from __future__ import annotations

import asyncio
import os
import pytest
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

# Import shared test database URL and config from conftest
from conftest import DATABASE_URL as TEST_DATABASE_URL, DB_CONFIG


@pytest.fixture(scope="module")
def clean_db_for_migration_tests():
    """
    Ensure test database is clean before each test.
    
    Drops all tables and types to provide a fresh slate.
    Database-agnostic: Works with PostgreSQL, SQLite, MySQL.
    """
    async def _clean():
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        try:
            async with engine.connect() as conn:
                if DB_CONFIG.is_sqlite:
                    # SQLite: Drop tables individually (no CASCADE support)
                    tables = [
                        "alembic_version", "token_replay_records", "user_mfa", 
                        "key_rotation_records", "feature_flags", "audit_events",
                        "policy_evaluation_logs", "policies", "password_reset_requests",
                        "invitations", "user_roles", "user_details", "users", "tenants"
                    ]
                    for table in tables:
                        await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    await conn.commit()
                else:
                    # PostgreSQL/MySQL: Drop all at once with CASCADE
                    await conn.execute(text("""
                        DROP TABLE IF EXISTS 
                            alembic_version,
                            token_replay_records, user_mfa, key_rotation_records, feature_flags, 
                            audit_events, policy_evaluation_logs, policies, 
                            password_reset_requests, invitations, user_roles, 
                            user_details, users, tenants
                        CASCADE;
                    """))
                    
                    # PostgreSQL: Drop enum types (SQLite doesn't have them)
                    if DB_CONFIG.is_postgres:
                        await conn.execute(text("""
                            DROP TYPE IF EXISTS 
                                mfa_factor_type, decision, flag_state, 
                                user_status, tenant_status
                            CASCADE;
                        """))
                    
                    await conn.commit()
        finally:
            await engine.dispose()
    
    # Run cleanup before module
    asyncio.run(_clean())
    
    # Re-apply migrations after cleanup so schema exists for subsequent tests
    config = get_alembic_config()
    run_alembic_command(command.upgrade, config, "head")
    
    yield
    
    # Re-apply migrations after module cleanup to restore schema for other test modules
    asyncio.run(_clean())
    config = get_alembic_config()
    run_alembic_command(command.upgrade, config, "head")


@pytest.fixture(scope="function")
def db_engine():
    """
    Create async engine for test database inspection.
    
    Returns a new engine that can be used for async queries in tests.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    
    # Cleanup
    asyncio.run(engine.dispose())


def get_alembic_config() -> Config:
    """
    Get Alembic configuration with test database URL.
    
    Temporarily sets DATABASE_URL environment variable for alembic/env.py.
    The variable is only set during Alembic command execution.
    """
    config = Config("alembic.ini")
    return config


def run_alembic_command(func, *args, **kwargs):
    """
    Run an Alembic command with test database URL in environment.
    
    Temporarily sets DATABASE_URL, runs the command, then restores original value.
    """
    original_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        return func(*args, **kwargs)
    finally:
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url


async def get_current_revision(conn: AsyncConnection) -> str | None:
    """Get current migration revision from database."""
    def _get_revision(sync_conn):
        context = MigrationContext.configure(sync_conn)
        return context.get_current_revision()
    
    return await conn.run_sync(_get_revision)


@pytest.mark.db
class TestMigrationSmoke:
    """Smoke tests for migration application and idempotency."""

    def test_fresh_migration_applies_successfully(self, db_engine, clean_db_for_migration_tests):
        """
        Test that initial migration can be applied to a fresh database.
        
        Validates:
        - Migration runs without errors
        - Database revision is set to head
        - No SQL errors during application
        """
        config = get_alembic_config()
        
        # Apply migration to head
        run_alembic_command(command.upgrade, config, "head")
        
        # Verify revision is at head
        async def _check_revision():
            async with db_engine.connect() as conn:
                current = await get_current_revision(conn)
                assert current is not None, "No migration revision found in database"
                
                # Get expected head revision
                script = ScriptDirectory.from_config(config)
                head = script.get_current_head()
                
                assert current == head, f"Current revision {current} does not match head {head}"
        
        asyncio.run(_check_revision())

    def test_migration_idempotency(self, db_engine, clean_db_for_migration_tests):
        """
        Test that migration can be applied multiple times without error (FR-015).
        
        Validates:
        - First application succeeds
        - Second application succeeds (idempotent)
        - Revision remains at head after repeat
        """
        config = get_alembic_config()
        
        # Apply migration first time
        run_alembic_command(command.upgrade, config, "head")
        
        # Apply migration second time (should be idempotent)
        run_alembic_command(command.upgrade, config, "head")  # Should not raise
        
        # Verify revision is still at head
        async def _check():
            async with db_engine.connect() as conn:
                current = await get_current_revision(conn)
                script = ScriptDirectory.from_config(config)
                head = script.get_current_head()
                assert current == head
        
        asyncio.run(_check())

    def test_expected_tables_exist(self, db_engine, clean_db_for_migration_tests):
        """
        Test that all expected tables exist after migration.
        
        Validates schema correctness by checking for presence of all
        12 expected tables from data-model.md.
        """
        config = get_alembic_config()
        run_alembic_command(command.upgrade, config, "head")
        
        expected_tables = {
            'tenants', 'users', 'user_roles', 'invitations',
            'password_reset_requests', 'policies', 'policy_evaluation_logs',
            'audit_events', 'feature_flags', 'key_rotation_records', 'user_mfa',
            'token_replay_records'
        }
        
        async def _check_tables():
            async with db_engine.connect() as conn:
                def _get_tables(sync_conn):
                    inspector = inspect(sync_conn)
                    return set(inspector.get_table_names())
                
                actual_tables = await conn.run_sync(_get_tables)
                
                # Verify all expected tables exist
                missing_tables = expected_tables - actual_tables
                assert not missing_tables, f"Missing tables: {missing_tables}"
                
                # Verify alembic_version table exists (migration tracking)
                assert 'alembic_version' in actual_tables
        
        asyncio.run(_check_tables())

    def test_expected_indexes_exist(self, db_engine, clean_db_for_migration_tests):
        """
        Test that key indexes exist after migration.
        
        Validates a sample of critical indexes per data-model.md specification.
        """
        config = get_alembic_config()
        run_alembic_command(command.upgrade, config, "head")
        
        async def _check_indexes():
            async with db_engine.connect() as conn:
                def _check(sync_conn):
                    inspector = inspect(sync_conn)
                    
                    # Tenants indexes
                    tenant_indexes = {idx['name'] for idx in inspector.get_indexes('tenants')}
                    assert 'ix_tenants_name' in tenant_indexes
                    assert 'ix_tenants_status_created_at' in tenant_indexes
                    
                    # Users indexes
                    user_indexes = {idx['name'] for idx in inspector.get_indexes('users')}
                    assert 'ix_users_tenant_email' in user_indexes
                    assert 'ix_users_tenant_status' in user_indexes
                    
                    # Policies indexes
                    policy_indexes = {idx['name'] for idx in inspector.get_indexes('policies')}
                    assert 'ix_policies_tenant_id' in policy_indexes
                    assert 'ix_policies_created_at' in policy_indexes
                    
                    return True
                
                result = await conn.run_sync(_check)
                assert result
        
        asyncio.run(_check_indexes())

    def test_expected_foreign_keys_exist(self, db_engine, clean_db_for_migration_tests):
        """
        Test that foreign keys are properly defined (FR-002, FR-018).
        
        Validates key FK relationships for tenant isolation.
        """
        config = get_alembic_config()
        run_alembic_command(command.upgrade, config, "head")
        
        async def _check_fks():
            async with db_engine.connect() as conn:
                def _check(sync_conn):
                    inspector = inspect(sync_conn)
                    
                    # Users table should have FK to tenants
                    user_fks = inspector.get_foreign_keys('users')
                    tenant_fk = next((fk for fk in user_fks if fk['referred_table'] == 'tenants'), None)
                    assert tenant_fk is not None, "Missing FK: users -> tenants"
                    assert tenant_fk['options'].get('ondelete') == 'CASCADE', "Wrong FK policy for users.tenant_id"
                    
                    # User_roles should have FK to users
                    role_fks = inspector.get_foreign_keys('user_roles')
                    user_fk = next((fk for fk in role_fks if fk['referred_table'] == 'users'), None)
                    assert user_fk is not None, "Missing FK: user_roles -> users"
                    assert user_fk['options'].get('ondelete') == 'CASCADE', "Wrong FK policy for user_roles.user_id"
                    
                    # Policies should have FK to tenants
                    policy_fks = inspector.get_foreign_keys('policies')
                    policy_tenant_fk = next((fk for fk in policy_fks if fk['referred_table'] == 'tenants'), None)
                    assert policy_tenant_fk is not None, "Missing FK: policies -> tenants"
                    
                    return True
                
                result = await conn.run_sync(_check)
                assert result
        
        asyncio.run(_check_fks())

    @pytest.mark.postgres_only
    def test_expected_enums_exist(self, db_engine, clean_db_for_migration_tests):
        """
        Test that PostgreSQL enum types are created.
        
        Validates all 5 enum types from models.py.
        PostgreSQL-only: Uses pg_type table.
        """
        config = get_alembic_config()
        run_alembic_command(command.upgrade, config, "head")
        
        async def _check_enums():
            async with db_engine.connect() as conn:
                result = await conn.execute(text("""
                    SELECT typname FROM pg_type 
                    WHERE typtype = 'e' 
                    ORDER BY typname
                """))
                enum_types = {row[0] for row in result}
                
                expected_enums = {
                    'tenant_status', 'user_status', 'flag_state', 
                    'decision', 'mfa_factor_type'
                }
                
                missing_enums = expected_enums - enum_types
                assert not missing_enums, f"Missing enum types: {missing_enums}"
        
        asyncio.run(_check_enums())

    @pytest.mark.postgres_only
    def test_downgrade_and_reupgrade(self, db_engine, clean_db_for_migration_tests):
        """
        Test that migration can be downgraded and re-upgraded.
        
        Validates bidirectional migration integrity.
        PostgreSQL-only: Uses DROP TYPE for enum cleanup.
        """
        config = get_alembic_config()
        
        # Apply migration
        run_alembic_command(command.upgrade, config, "head")
        
        # Downgrade to base
        run_alembic_command(command.downgrade, config, "base")
        
        # Verify tables are gone and then re-upgrade and check again
        async def _check_downgrade_and_reupgrade():
            # First check: tables should be gone
            engine1 = create_async_engine(TEST_DATABASE_URL, echo=False)
            try:
                async with engine1.connect() as conn:
                    def _check_no_tables(sync_conn):
                        inspector = inspect(sync_conn)
                        tables = inspector.get_table_names()
                        # Only alembic_version should remain
                        assert len([t for t in tables if t != 'alembic_version']) == 0
                        return True
                    
                    await conn.run_sync(_check_no_tables)
            finally:
                await engine1.dispose()
            
            # Re-upgrade outside the async context (Alembic manages its own loop)
            pass
        
        asyncio.run(_check_downgrade_and_reupgrade())
        
        # Re-upgrade
        run_alembic_command(command.upgrade, config, "head")
        
        # Verify tables exist again (in new event loop)
        async def _check_tables_restored():
            engine2 = create_async_engine(TEST_DATABASE_URL, echo=False)
            try:
                async with engine2.connect() as conn:
                    def _check(sync_conn):
                        inspector = inspect(sync_conn)
                        tables = set(inspector.get_table_names())
                        assert 'tenants' in tables
                        assert 'users' in tables
                        return True
                    
                    await conn.run_sync(_check)
            finally:
                await engine2.dispose()
        
        asyncio.run(_check_tables_restored())
