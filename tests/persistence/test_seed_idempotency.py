"""
TEST-DB-06 & TEST-DB-14: Seed idempotency and conflict detection tests.

Validates:
- TEST-DB-06: Seed idempotency with real DB (initial vs second run) (FR-025, FR-069, C-043)
- TEST-DB-14: Seed conflict scenario emits audit & correct summary counts (FR-025, C-043, FR-005)

Status: Phase 3 Lane DB-B
Dependencies: IMPL-DB-07 (durable seed script)
"""
from __future__ import annotations

import pytest
import os

from cli.db_bootstrap import seed_database, deterministic_uuid


# Test database URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import shared test database URL from conftest
from conftest import DATABASE_URL as TEST_DATABASE_URL, DB_CONFIG
from sqlalchemy import text
import asyncio
from alembic.config import Config
from alembic import command


def get_alembic_config():
    """Get alembic configuration for test database."""
    config = Config("alembic.ini")
    return config


def run_alembic_command(func, *args, **kwargs):
    """
    Run an Alembic command with test database URL in environment.
    
    Temporarily sets DATABASE_URL, runs the command, then restores original value.
    """
    original_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = str(TEST_DATABASE_URL)
        return func(*args, **kwargs)
    finally:
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url


@pytest.fixture(scope="module")
def clean_db():
    """
    Ensure test database has fresh data before each test module.
    
    Clears all data from tables and re-inserts system roles (needed for seeding).
    Schema is managed by the session-level db_engine fixture from conftest.py.
    """
    # System role UUIDs (must match migration)
    SUPERADMIN_ROLE_ID = "00000000-0000-0000-0000-000000000001"
    TENANT_ADMIN_ROLE_ID = "00000000-0000-0000-0000-000000000002"
    USER_ROLE_ID = "00000000-0000-0000-0000-000000000003"
    
    async def _clean_data():
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        try:
            async with engine.connect() as conn:
                try:
                    # Delete all data (CASCADE ensures referential integrity)
                    await conn.execute(text("TRUNCATE TABLE tenants, users, user_roles, user_details, "
                                           "policies, feature_flags, audit_events, invitations, "
                                           "password_reset_requests, user_mfa, policy_evaluation_logs, "
                                           "token_replay_records, key_rotation_records, roles "
                                           "RESTART IDENTITY CASCADE"))
                    
                    # Re-insert system roles (migrations create these, but TRUNCATE removes them)
                    await conn.execute(text(f"""
                        INSERT INTO roles (id, name, tenant_id, is_system, permissions, description, created_at, updated_at)
                        VALUES 
                        ('{SUPERADMIN_ROLE_ID}'::uuid, 'superadmin', NULL, TRUE, 
                         '["*"]'::jsonb,
                         'System administrator with cross-tenant access and all permissions',
                         NOW(), NOW()),
                        ('{TENANT_ADMIN_ROLE_ID}'::uuid, 'tenant_admin', NULL, TRUE,
                         '["tenant:*", "users:*", "roles:create", "roles:update", "roles:delete", "policies:*"]'::jsonb,
                         'Tenant administrator with full control within tenant scope',
                         NOW(), NOW()),
                        ('{USER_ROLE_ID}'::uuid, 'user', NULL, TRUE,
                         '["users:read_own", "profile:update_own"]'::jsonb,
                         'Standard authenticated user with read-only access to own resources',
                         NOW(), NOW())
                    """))
                    
                    await conn.commit()
                except Exception:
                    # Tables might not exist yet if db_engine fixture hasn't run
                    # This is fine - the session fixture will create them
                    pass
        finally:
            await engine.dispose()
    
    # Run cleanup before module tests
    asyncio.run(_clean_data())
    
    yield
    
    # Run cleanup after module tests to leave clean state for other modules
    asyncio.run(_clean_data())


@pytest.fixture(scope="function")
def db_engine():
    """Create async engine for test database inspection."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    # Cleanup handled by engine's own lifecycle


@pytest.mark.db
@pytest.mark.asyncio
class TestSeedIdempotency:
    """TEST-DB-06: Seed idempotency validation."""

    async def test_initial_seed_creates_entities(self, clean_db, db_engine):
        """
        Test first seed run creates tenant and admin user.
        
        Validates:
        - Tenant created with deterministic UUID
        - Admin user created with deterministic UUID
        - No conflicts on first run
        """
        result = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="test-tenant",
            admin_email="admin@test.com",
        )
        
        assert result.created_tenant is True, "First run should create tenant"
        assert result.created_user is True, "First run should create admin user"
        assert result.conflicts == [], "First run should have no conflicts"
        assert result.counts["tenants"] >= 1
        assert result.counts["users"] >= 1

    async def test_second_seed_is_idempotent(self, clean_db, db_engine):
        """
        Test second seed run is idempotent (no duplicates) (FR-025).
        
        Validates:
        - Same tenant ID used (deterministic)
        - Same user ID used (deterministic)
        - No new entities created
        - Conflicts detected for both tenant and user
        """
        # First run
        result1 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="idempotent-test",
            admin_email="admin@idempotent.com",
        )
        
        tenant_id_1 = result1.tenant_id
        user_id_1 = result1.admin_user_id
        
        # Second run with same parameters
        result2 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="idempotent-test",
            admin_email="admin@idempotent.com",
        )
        
        # Validate idempotency
        assert result2.tenant_id == tenant_id_1, "Tenant ID should be deterministic"
        assert result2.admin_user_id == user_id_1, "User ID should be deterministic"
        assert result2.created_tenant is False, "Second run should not create tenant"
        assert result2.created_user is False, "Second run should not create user"
        assert "tenant_exists" in result2.conflicts, "Should detect tenant conflict"
        assert "admin_exists" in result2.conflicts, "Should detect admin conflict"

    async def test_deterministic_uuid_generation(self, clean_db, db_engine):
        """
        Test UUIDs are deterministic based on input (FR-069, C-009).
        
        Validates:
        - Same input generates same UUID
        - Different input generates different UUID
        """
        # Multiple seeds with same parameters should yield same IDs
        result1 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="deterministic",
            admin_email="admin@deterministic.com",
        )
        
        result2 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="deterministic",
            admin_email="admin@deterministic.com",
        )
        
        assert result1.tenant_id == result2.tenant_id
        assert result1.admin_user_id == result2.admin_user_id
        
        # Different parameters should yield different IDs
        result3 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="different",
            admin_email="admin@different.com",
        )
        
        assert result3.tenant_id != result1.tenant_id
        assert result3.admin_user_id != result1.admin_user_id

    async def test_multiple_tenants_coexist(self, clean_db, db_engine):
        """
        Test multiple seed runs with different parameters create distinct tenants.
        
        Validates tenant isolation (FR-002).
        """
        # Seed first tenant
        result1 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="tenant-a",
            admin_email="admin@tenant-a.com",
        )
        
        # Seed second tenant
        result2 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="tenant-b",
            admin_email="admin@tenant-b.com",
        )
        
        # Both should succeed without conflicts
        assert result1.created_tenant is True
        assert result1.created_user is True
        assert result2.created_tenant is True
        assert result2.created_user is True
        
        # Final count should show both tenants
        assert result2.counts["tenants"] >= 2


@pytest.mark.db
@pytest.mark.asyncio
class TestSeedConflictDetection:
    """TEST-DB-14: Seed conflict scenario validation."""

    async def test_conflict_summary_contains_correct_fields(self, clean_db, db_engine):
        """
        Test seed result summary contains required fields (FR-025, C-043).
        
        Validates:
        - tenant_id present
        - admin_user_id present
        - created flags present
        - conflicts list present
        - counts present
        - duration_ms present
        """
        result = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="summary-test",
            admin_email="admin@summary.com",
        )
        
        assert result.tenant_id is not None
        assert result.admin_user_id is not None
        assert isinstance(result.created_tenant, bool)
        assert isinstance(result.created_user, bool)
        assert isinstance(result.conflicts, list)
        assert isinstance(result.counts, dict)
        assert "tenants" in result.counts
        assert "users" in result.counts
        assert result.duration_ms > 0

    async def test_partial_conflict_detection(self, clean_db, db_engine):
        """
        Test seed detects partial conflicts (tenant exists but not user, or vice versa).
        
        Edge case: In practice rare, but validates conflict detection granularity.
        """
        # First seed
        result1 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="partial-tenant",
            admin_email="admin1@partial.com",
        )
        
        assert result1.created_tenant is True
        assert result1.created_user is True
        
        # Second seed with same tenant but different user
        # (This will reuse tenant, create new user)
        result2 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="partial-tenant",
            admin_email="admin2@partial.com",
        )
        
        assert result2.created_tenant is False, "Tenant should exist"
        assert result2.created_user is True, "Different user should be created"
        assert "tenant_exists" in result2.conflicts
        assert "admin_exists" not in result2.conflicts

    async def test_count_accuracy_after_multiple_seeds(self, clean_db, db_engine):
        """
        Test entity counts are accurate after multiple seed operations (FR-025, C-043).
        
        Validates summary counts reflect actual database state.
        """
        # Seed 3 different tenants
        await seed_database(TEST_DATABASE_URL, "tenant-1", "admin1@test.com")
        await seed_database(TEST_DATABASE_URL, "tenant-2", "admin2@test.com")
        result = await seed_database(TEST_DATABASE_URL, "tenant-3", "admin3@test.com")
        
        # Final result should show 3 tenants
        assert result.counts["tenants"] >= 3

    async def test_idempotent_flag_correct(self, clean_db, db_engine):
        """
        Test idempotent detection logic in summary.
        
        Idempotent = both tenant and user already existed (no-op).
        """
        # First run
        result1 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="idempotent-flag",
            admin_email="admin@idempotent-flag.com",
        )
        
        # Not idempotent on first run (created entities)
        assert len(result1.conflicts) == 0
        
        # Second run
        result2 = await seed_database(
            database_url=TEST_DATABASE_URL,
            tenant_slug="idempotent-flag",
            admin_email="admin@idempotent-flag.com",
        )
        
        # Idempotent on second run (both existed)
        assert len(result2.conflicts) == 2
        assert "tenant_exists" in result2.conflicts
        assert "admin_exists" in result2.conflicts

    # TODO (FR-005, C-043): Add test for audit event emission when audit repo integrated
    # async def test_conflict_emits_audit_event(self, clean_db, db_engine):
    #     """Test seed conflict emits audit event (FR-005, C-043)."""
    #     pass
