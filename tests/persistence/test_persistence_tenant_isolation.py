"""
TEST-DB-08: Tenant isolation and soft delete enforcement tests.

Validates:
- list_by_tenant() enforces WHERE tenant_id = ? (FR-002, FR-018)
- Soft-deleted entities excluded from default queries
- Cross-tenant data access prevented

Status: Phase 3 Lane DB-C
Dependencies: IMPL-DB-05 (repository implementations)
"""
from __future__ import annotations

import pytest
import os
import uuid
from datetime import datetime, UTC

from adapters.persistence.repositories import (
    SQLAlchemyTenantRepository,
    SQLAlchemyUserRepository,
    SQLAlchemyPolicyRepository,
    SQLAlchemyFeatureFlagRepository,
)
from domain.tenants.models import Tenant, TenantStatus
from domain.users.models import User, UserStatus
from domain.policy.models import Policy, Decision, PolicyRule
from domain.featureflags.models import FeatureFlag, FlagState
from domain.roles.entities import SYSTEM_ROLE_IDS


@pytest.mark.db
@pytest.mark.asyncio
class TestTenantIsolation:
    """TEST-DB-08: Tenant isolation enforcement at query layer."""

    async def test_user_list_by_tenant_filters_correctly(self, db_session):
        """
        Test list_by_tenant() only returns users for specified tenant (FR-002).
        
        Validates cross-tenant isolation.
        """
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Create two tenants
        tenant_a_id = str(uuid.uuid4())
        tenant_b_id = str(uuid.uuid4())
        
        tenant_a = Tenant(
            tenant_id=tenant_a_id,
            name="Tenant A",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        tenant_b = Tenant(
            tenant_id=tenant_b_id,
            name="Tenant B",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        
        await tenant_repo.upsert(tenant_a)
        await tenant_repo.upsert(tenant_b)
        await db_session.flush()
        
        # Create users in each tenant
        user_a1_id = str(uuid.uuid4())
        user_a2_id = str(uuid.uuid4())
        user_b1_id = str(uuid.uuid4())
        
        user_a1 = User(
            user_id=user_a1_id,
            tenant_id=tenant_a_id,
            email="user1@tenant-a.com",
            password_hash="hash",
            roles=[str(SYSTEM_ROLE_IDS["tenant_admin"])],
            status=UserStatus.active,
            created_at=datetime.now(UTC),
        )
        user_a2 = User(
            user_id=user_a2_id,
            tenant_id=tenant_a_id,
            email="user2@tenant-a.com",
            password_hash="hash",
            roles=[str(SYSTEM_ROLE_IDS["user"])],
            status=UserStatus.active,
            created_at=datetime.now(UTC),
        )
        user_b1 = User(
            user_id=user_b1_id,
            tenant_id=tenant_b_id,
            email="user1@tenant-b.com",
            password_hash="hash",
            roles=[str(SYSTEM_ROLE_IDS["tenant_admin"])],
            status=UserStatus.active,
            created_at=datetime.now(UTC),
        )
        
        await user_repo.upsert(user_a1)
        await user_repo.upsert(user_a2)
        await user_repo.upsert(user_b1)
        await db_session.flush()
        
        # List users for tenant A
        users_a = await user_repo.list_by_tenant(tenant_a_id)
        
        # Should only return 2 users from tenant A
        assert len(users_a) == 2
        assert all(u.tenant_id == tenant_a_id for u in users_a)
        assert {u.user_id for u in users_a} == {user_a1_id, user_a2_id}
        
        # List users for tenant B
        users_b = await user_repo.list_by_tenant(tenant_b_id)
        
        # Should only return 1 user from tenant B
        assert len(users_b) == 1
        assert users_b[0].tenant_id == tenant_b_id
        assert users_b[0].user_id == user_b1_id

    async def test_policy_list_by_tenant_filters_correctly(self, db_session):
        """
        Test policy list_by_tenant() enforces isolation (FR-002, FR-018).
        """
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        policy_repo = SQLAlchemyPolicyRepository(db_session)
        
        # Create two tenants
        tenant_x_id = str(uuid.uuid4())
        tenant_y_id = str(uuid.uuid4())
        
        tenant_x = Tenant(
            tenant_id=tenant_x_id,
            name="Tenant X",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        tenant_y = Tenant(
            tenant_id=tenant_y_id,
            name="Tenant Y",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        
        await tenant_repo.upsert(tenant_x)
        await tenant_repo.upsert(tenant_y)
        await db_session.flush()
        
        # Create policies in each tenant
        policy_x1_id = str(uuid.uuid4())
        policy_y1_id = str(uuid.uuid4())
        
        rule_x1 = PolicyRule(
            rule_id=str(uuid.uuid4()),
            version=1,
            resource="users",
            action="read",
            effect=Decision.allow,
        )
        rule_y1 = PolicyRule(
            rule_id=str(uuid.uuid4()),
            version=1,
            resource="tenants",
            action="delete",
            effect=Decision.deny,
        )
        
        policy_x1 = Policy(
            policy_id=policy_x1_id,
            tenant_id=tenant_x_id,
            name="X Policy 1",
            rules=[rule_x1],
            created_at=datetime.now(UTC),
        )
        policy_y1 = Policy(
            policy_id=policy_y1_id,
            tenant_id=tenant_y_id,
            name="Y Policy 1",
            rules=[rule_y1],
            created_at=datetime.now(UTC),
        )
        
        await policy_repo.upsert(policy_x1)
        await policy_repo.upsert(policy_y1)
        await db_session.flush()
        
        # List policies for tenant X
        policies_x = await policy_repo.list_by_tenant(tenant_x_id)
        
        # Should only return policy from tenant X
        assert len(policies_x) == 1
        assert policies_x[0].tenant_id == tenant_x_id
        assert policies_x[0].policy_id == policy_x1_id
        
        # List policies for tenant Y
        policies_y = await policy_repo.list_by_tenant(tenant_y_id)
        
        # Should only return policy from tenant Y
        assert len(policies_y) == 1
        assert policies_y[0].tenant_id == tenant_y_id
        assert policies_y[0].policy_id == policy_y1_id

    async def test_feature_flag_list_by_tenant_filters_correctly(self, db_session):
        """
        Test feature flag list_by_tenant() enforces isolation (FR-002).
        """
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        flag_repo = SQLAlchemyFeatureFlagRepository(db_session)
        
        # Create two tenants
        tenant_p_id = str(uuid.uuid4())
        tenant_q_id = str(uuid.uuid4())
        
        tenant_p = Tenant(
            tenant_id=tenant_p_id,
            name="Tenant P",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        tenant_q = Tenant(
            tenant_id=tenant_q_id,
            name="Tenant Q",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        
        await tenant_repo.upsert(tenant_p)
        await tenant_repo.upsert(tenant_q)
        await db_session.flush()
        
        # Create flags in each tenant
        flag_p1_id = str(uuid.uuid4())
        flag_p2_id = str(uuid.uuid4())
        flag_q1_id = str(uuid.uuid4())
        
        flag_p1 = FeatureFlag(
            flag_id=flag_p1_id,
            tenant_id=tenant_p_id,
            key="feature-p1",
            state=FlagState.enabled,
            created_at=datetime.now(UTC),
        )
        flag_p2 = FeatureFlag(
            flag_id=flag_p2_id,
            tenant_id=tenant_p_id,
            key="feature-p2",
            state=FlagState.disabled,
            created_at=datetime.now(UTC),
        )
        flag_q1 = FeatureFlag(
            flag_id=flag_q1_id,
            tenant_id=tenant_q_id,
            key="feature-q1",
            state=FlagState.enabled,
            created_at=datetime.now(UTC),
        )
        
        await flag_repo.upsert(flag_p1)
        await flag_repo.upsert(flag_p2)
        await flag_repo.upsert(flag_q1)
        await db_session.flush()
        
        # List flags for tenant P
        flags_p = await flag_repo.list_by_tenant(tenant_p_id)
        
        # Should return 2 flags from tenant P
        assert len(flags_p) == 2
        assert all(f.tenant_id == tenant_p_id for f in flags_p)
        assert {f.flag_id for f in flags_p} == {flag_p1_id, flag_p2_id}
        
        # List flags for tenant Q
        flags_q = await flag_repo.list_by_tenant(tenant_q_id)
        
        # Should return 1 flag from tenant Q
        assert len(flags_q) == 1
        assert flags_q[0].tenant_id == tenant_q_id
        assert flags_q[0].flag_id == flag_q1_id


@pytest.mark.db
@pytest.mark.asyncio
class TestSoftDeleteEnforcement:
    """TEST-DB-08: Soft delete enforcement validation."""

    async def test_soft_deleted_tenant_excluded_from_list(self, db_session):
        """
        Test soft-deleted tenants not returned by list() (FR-018).
        """
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        
        # Create two tenants
        tenant_active_id = str(uuid.uuid4())
        tenant_deleted_id = str(uuid.uuid4())
        
        tenant_active = Tenant(
            tenant_id=tenant_active_id,
            name="Active Tenant",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        tenant_deleted = Tenant(
            tenant_id=tenant_deleted_id,
            name="Deleted Tenant",
            status=TenantStatus.active,  # Initially active
            created_at=datetime.now(UTC),
        )
        
        await tenant_repo.upsert(tenant_active)
        await tenant_repo.upsert(tenant_deleted)
        await db_session.flush()
        
        # Soft delete second tenant
        await tenant_repo.soft_delete(tenant_deleted_id)
        await db_session.flush()
        
        # List all tenants (should exclude soft-deleted)
        all_tenants = await tenant_repo.list()
        
        # Verify our test tenants: deleted one should not be in list, active one should be
        tenant_ids = {t.tenant_id for t in all_tenants}
        assert tenant_active_id in tenant_ids, "Active tenant should be in list"
        assert tenant_deleted_id not in tenant_ids, "Soft-deleted tenant should not be in list"
        
        # Verify active tenant has correct status
        active_tenant = next(t for t in all_tenants if t.tenant_id == tenant_active_id)
        assert active_tenant.status == TenantStatus.active

    async def test_soft_deleted_user_excluded_from_list_by_tenant(self, db_session):
        """
        Test soft-deleted users not returned by list_by_tenant() (FR-018).
        """
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        user_repo = SQLAlchemyUserRepository(db_session)
        
        # Create tenant
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            tenant_id=tenant_id,
            name="Soft Delete Test",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        
        await tenant_repo.upsert(tenant)
        await db_session.flush()
        
        # Create two users
        user_active_id = str(uuid.uuid4())
        user_deleted_id = str(uuid.uuid4())
        
        user_active = User(
            user_id=user_active_id,
            tenant_id=tenant_id,
            email="active@test.com",
            password_hash="hash",
            roles=[str(SYSTEM_ROLE_IDS["user"])],
            status=UserStatus.active,
            created_at=datetime.now(UTC),
        )
        user_deleted = User(
            user_id=user_deleted_id,
            tenant_id=tenant_id,
            email="deleted@test.com",
            password_hash="hash",
            roles=[str(SYSTEM_ROLE_IDS["user"])],
            status=UserStatus.active,  # Initially active
            created_at=datetime.now(UTC),
        )
        
        await user_repo.upsert(user_active)
        await user_repo.upsert(user_deleted)
        await db_session.flush()
        
        # Soft delete second user
        await user_repo.soft_delete(user_deleted_id)
        await db_session.flush()
        
        # List users by tenant (should exclude soft-deleted)
        users = await user_repo.list_by_tenant(tenant_id)
        
        # Verify soft-deleted user is not in list, active user is present
        user_ids = {u.user_id for u in users}
        assert user_active_id in user_ids, "Active user should be in list"
        assert user_deleted_id not in user_ids, "Soft-deleted user should not be in list"
        
        # Verify active user has correct status
        active_user = next(u for u in users if u.user_id == user_active_id)
        assert active_user.status == UserStatus.active

    async def test_soft_deleted_entity_can_be_restored(self, db_session):
        """
        Test soft-deleted entities can be restored (FR-018).
        """
        tenant_repo = SQLAlchemyTenantRepository(db_session)
        
        # Create tenant
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            tenant_id=tenant_id,
            name="Restore Test",
            status=TenantStatus.active,
            created_at=datetime.now(UTC),
        )
        
        await tenant_repo.upsert(tenant)
        await db_session.flush()
        
        # Soft delete
        await tenant_repo.soft_delete(tenant_id)
        await db_session.flush()
        
        # Verify excluded from list
        all_tenants = await tenant_repo.list()
        tenant_ids = {t.tenant_id for t in all_tenants}
        assert tenant_id not in tenant_ids, "Soft-deleted tenant should not be in list"
        
        # Restore
        await tenant_repo.restore(tenant_id)
        await db_session.flush()
        
        # Verify included in list again
        all_tenants_after_restore = await tenant_repo.list()
        tenant_ids_after = {t.tenant_id for t in all_tenants_after_restore}
        assert tenant_id in tenant_ids_after, "Restored tenant should be in list"
        
        # Verify restored tenant has active status
        restored_tenant = next(t for t in all_tenants_after_restore if t.tenant_id == tenant_id)
        assert restored_tenant.status == TenantStatus.active
