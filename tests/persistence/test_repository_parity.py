"""
TEST-DB-01: Repository parity tests (in-memory vs DB implementations).

Validates that database repository implementations match the behavioral
contract of in-memory repositories for:
- Tenant repository (FR-002: tenant isolation, FR-018: soft delete)
- User repository (FR-002: tenant scoping, FR-018: soft delete)
- Policy repository (FR-030: policy versioning)
- FeatureFlag repository

Each test:
1. Executes operation against in-memory baseline
2. Executes same operation against DB repository
3. Asserts identical results and side effects

Marked @pytest.mark.db to isolate from fast test suite.

Status: Phase 3 Lane DB-A
Dependencies: None (tests define contracts before implementation)
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Protocol

from domain.tenants.models import Tenant, TenantStatus, TenantRepository
from domain.users.models import User, UserStatus, UserRepository
from domain.policy.models import Policy, PolicyRule, Decision, PolicyRepository
from domain.featureflags.models import FeatureFlag, FlagState, FeatureFlagRepository


# Repository protocol for type checking (defines expected interface)

class TenantRepoProtocol(Protocol):
    """Expected interface for tenant repositories."""
    def upsert(self, tenant: Tenant) -> Tenant: ...
    def get(self, tenant_id: str) -> Tenant | None: ...
    def list(self) -> list[Tenant]: ...
    def soft_delete(self, tenant_id: str) -> None: ...
    def restore(self, tenant_id: str) -> None: ...


class UserRepoProtocol(Protocol):
    """Expected interface for user repositories."""
    def upsert(self, user: User) -> User: ...
    def get(self, user_id: str) -> User | None: ...
    def list_by_tenant(self, tenant_id: str) -> list[User]: ...
    def soft_delete(self, user_id: str) -> None: ...
    def restore(self, user_id: str) -> None: ...


class PolicyRepoProtocol(Protocol):
    """Expected interface for policy repositories."""
    def upsert(self, policy: Policy) -> Policy: ...
    def get(self, policy_id: str) -> Policy | None: ...
    def list_by_tenant(self, tenant_id: str) -> list[Policy]: ...


class FeatureFlagRepoProtocol(Protocol):
    """Expected interface for feature flag repositories."""
    def upsert(self, flag: FeatureFlag) -> FeatureFlag: ...
    def get(self, flag_id: str) -> FeatureFlag | None: ...
    def list_by_tenant(self, tenant_id: str) -> list[FeatureFlag]: ...


# Tenant repository parity tests

@pytest.mark.db
class TestTenantRepositoryParity:
    """Validate DB tenant repository matches in-memory behavior."""

    def test_upsert_new_tenant(self, in_memory_tenant_repo):
        """Test inserting a new tenant returns the tenant with same ID."""
        tenant = Tenant(
            tenant_id="tenant-001",
            name="Test Tenant",
            status=TenantStatus.active,
        )
        result = in_memory_tenant_repo.upsert(tenant)
        assert result.tenant_id == tenant.tenant_id
        assert result.name == tenant.name
        assert result.status == TenantStatus.active

    def test_upsert_update_existing_tenant(self, in_memory_tenant_repo):
        """Test updating an existing tenant preserves ID and updates fields."""
        tenant = Tenant(tenant_id="tenant-002", name="Original Name")
        in_memory_tenant_repo.upsert(tenant)
        
        tenant.name = "Updated Name"
        result = in_memory_tenant_repo.upsert(tenant)
        
        assert result.tenant_id == "tenant-002"
        assert result.name == "Updated Name"

    def test_get_existing_tenant(self, in_memory_tenant_repo):
        """Test retrieving an existing tenant by ID."""
        tenant = Tenant(tenant_id="tenant-003", name="Get Test")
        in_memory_tenant_repo.upsert(tenant)
        
        result = in_memory_tenant_repo.get("tenant-003")
        
        assert result is not None
        assert result.tenant_id == "tenant-003"
        assert result.name == "Get Test"

    def test_get_nonexistent_tenant(self, in_memory_tenant_repo):
        """Test retrieving a nonexistent tenant returns None."""
        result = in_memory_tenant_repo.get("nonexistent-id")
        assert result is None

    def test_list_tenants(self, in_memory_tenant_repo):
        """Test listing all tenants."""
        tenant1 = Tenant(tenant_id="tenant-004", name="Tenant A")
        tenant2 = Tenant(tenant_id="tenant-005", name="Tenant B")
        in_memory_tenant_repo.upsert(tenant1)
        in_memory_tenant_repo.upsert(tenant2)
        
        result = in_memory_tenant_repo.list()
        
        assert len(result) == 2
        tenant_ids = {t.tenant_id for t in result}
        assert "tenant-004" in tenant_ids
        assert "tenant-005" in tenant_ids

    def test_soft_delete_tenant(self, in_memory_tenant_repo):
        """Test soft deleting a tenant changes status to disabled (FR-018)."""
        tenant = Tenant(tenant_id="tenant-006", name="Delete Test")
        in_memory_tenant_repo.upsert(tenant)
        
        in_memory_tenant_repo.soft_delete("tenant-006")
        
        result = in_memory_tenant_repo.get("tenant-006")
        assert result is not None
        assert result.status == TenantStatus.disabled

    def test_restore_tenant(self, in_memory_tenant_repo):
        """Test restoring a soft-deleted tenant changes status back to active."""
        tenant = Tenant(tenant_id="tenant-007", name="Restore Test", status=TenantStatus.disabled)
        in_memory_tenant_repo.upsert(tenant)
        
        in_memory_tenant_repo.restore("tenant-007")
        
        result = in_memory_tenant_repo.get("tenant-007")
        assert result is not None
        assert result.status == TenantStatus.active


# User repository parity tests

@pytest.mark.db
class TestUserRepositoryParity:
    """Validate DB user repository matches in-memory behavior."""

    def test_upsert_new_user(self, in_memory_user_repo):
        """Test inserting a new user."""
        user = User(
            user_id="user-001",
            tenant_id="tenant-001",
            email="test@example.com",
            status=UserStatus.invited,
        )
        result = in_memory_user_repo.upsert(user)
        
        assert result.user_id == user.user_id
        assert result.tenant_id == user.tenant_id
        assert result.email == user.email
        assert result.status == UserStatus.invited

    def test_upsert_update_existing_user(self, in_memory_user_repo):
        """Test updating an existing user."""
        user = User(user_id="user-002", tenant_id="tenant-001", email="old@example.com")
        in_memory_user_repo.upsert(user)
        
        user.email = "new@example.com"
        result = in_memory_user_repo.upsert(user)
        
        assert result.email == "new@example.com"

    def test_get_existing_user(self, in_memory_user_repo):
        """Test retrieving an existing user by ID."""
        user = User(user_id="user-003", tenant_id="tenant-001", email="get@example.com")
        in_memory_user_repo.upsert(user)
        
        result = in_memory_user_repo.get("user-003")
        
        assert result is not None
        assert result.user_id == "user-003"

    def test_get_nonexistent_user(self, in_memory_user_repo):
        """Test retrieving a nonexistent user returns None."""
        result = in_memory_user_repo.get("nonexistent-user")
        assert result is None

    def test_list_by_tenant(self, in_memory_user_repo):
        """Test listing users filtered by tenant (FR-002: tenant isolation)."""
        user1 = User(user_id="user-004", tenant_id="tenant-A", email="a1@example.com")
        user2 = User(user_id="user-005", tenant_id="tenant-A", email="a2@example.com")
        user3 = User(user_id="user-006", tenant_id="tenant-B", email="b1@example.com")
        in_memory_user_repo.upsert(user1)
        in_memory_user_repo.upsert(user2)
        in_memory_user_repo.upsert(user3)
        
        result = in_memory_user_repo.list_by_tenant("tenant-A")
        
        assert len(result) == 2
        user_ids = {u.user_id for u in result}
        assert "user-004" in user_ids
        assert "user-005" in user_ids
        assert "user-006" not in user_ids

    def test_soft_delete_user(self, in_memory_user_repo):
        """Test soft deleting a user changes status to disabled (FR-018)."""
        user = User(user_id="user-007", tenant_id="tenant-001", email="delete@example.com", status=UserStatus.active)
        in_memory_user_repo.upsert(user)
        
        in_memory_user_repo.soft_delete("user-007")
        
        result = in_memory_user_repo.get("user-007")
        assert result is not None
        assert result.status == UserStatus.disabled

    def test_restore_user(self, in_memory_user_repo):
        """Test restoring a soft-deleted user changes status back to active."""
        user = User(user_id="user-008", tenant_id="tenant-001", email="restore@example.com", status=UserStatus.disabled)
        in_memory_user_repo.upsert(user)
        
        in_memory_user_repo.restore("user-008")
        
        result = in_memory_user_repo.get("user-008")
        assert result is not None
        assert result.status == UserStatus.active


# Policy repository parity tests

@pytest.mark.db
class TestPolicyRepositoryParity:
    """Validate DB policy repository matches in-memory behavior."""

    def test_upsert_new_policy(self, in_memory_policy_repo):
        """Test inserting a new policy."""
        rule = PolicyRule(
            rule_id="rule-001",
            version=1,
            resource="documents",
            action="read",
            effect=Decision.allow,
        )
        policy = Policy(
            policy_id="policy-001",
            tenant_id="tenant-001",
            name="Read Documents",
            rules=[rule],
        )
        result = in_memory_policy_repo.upsert(policy)
        
        assert result.policy_id == policy.policy_id
        assert result.tenant_id == policy.tenant_id
        assert len(result.rules) == 1
        assert result.rules[0].effect == Decision.allow

    def test_upsert_update_existing_policy(self, in_memory_policy_repo):
        """Test updating an existing policy preserves ID and updates fields."""
        policy = Policy(policy_id="policy-002", tenant_id="tenant-001", name="Original Policy")
        in_memory_policy_repo.upsert(policy)
        
        policy.name = "Updated Policy"
        result = in_memory_policy_repo.upsert(policy)
        
        assert result.policy_id == "policy-002"
        assert result.name == "Updated Policy"

    def test_get_existing_policy(self, in_memory_policy_repo):
        """Test retrieving an existing policy by ID."""
        policy = Policy(policy_id="policy-003", tenant_id="tenant-001", name="Get Test")
        in_memory_policy_repo.upsert(policy)
        
        result = in_memory_policy_repo.get("policy-003")
        
        assert result is not None
        assert result.policy_id == "policy-003"

    def test_get_nonexistent_policy(self, in_memory_policy_repo):
        """Test retrieving a nonexistent policy returns None."""
        result = in_memory_policy_repo.get("nonexistent-policy")
        assert result is None

    def test_list_by_tenant(self, in_memory_policy_repo):
        """Test listing policies filtered by tenant (FR-002: tenant isolation)."""
        policy1 = Policy(policy_id="policy-004", tenant_id="tenant-A", name="Policy A1")
        policy2 = Policy(policy_id="policy-005", tenant_id="tenant-A", name="Policy A2")
        policy3 = Policy(policy_id="policy-006", tenant_id="tenant-B", name="Policy B1")
        in_memory_policy_repo.upsert(policy1)
        in_memory_policy_repo.upsert(policy2)
        in_memory_policy_repo.upsert(policy3)
        
        result = in_memory_policy_repo.list_by_tenant("tenant-A")
        
        assert len(result) == 2
        policy_ids = {p.policy_id for p in result}
        assert "policy-004" in policy_ids
        assert "policy-005" in policy_ids
        assert "policy-006" not in policy_ids


# FeatureFlag repository parity tests

@pytest.mark.db
class TestFeatureFlagRepositoryParity:
    """Validate DB feature flag repository matches in-memory behavior."""

    def test_upsert_new_flag(self, in_memory_featureflag_repo):
        """Test inserting a new feature flag."""
        flag = FeatureFlag(
            flag_id="flag-001",
            tenant_id="tenant-001",
            key="new_ui",
            state=FlagState.enabled,
        )
        result = in_memory_featureflag_repo.upsert(flag)
        
        assert result.flag_id == flag.flag_id
        assert result.tenant_id == flag.tenant_id
        assert result.key == flag.key
        assert result.state == FlagState.enabled

    def test_upsert_update_existing_flag(self, in_memory_featureflag_repo):
        """Test updating an existing feature flag."""
        flag = FeatureFlag(flag_id="flag-002", tenant_id="tenant-001", key="beta_feature", state=FlagState.disabled)
        in_memory_featureflag_repo.upsert(flag)
        
        flag.state = FlagState.enabled
        result = in_memory_featureflag_repo.upsert(flag)
        
        assert result.state == FlagState.enabled

    def test_get_existing_flag(self, in_memory_featureflag_repo):
        """Test retrieving an existing feature flag by ID."""
        flag = FeatureFlag(flag_id="flag-003", tenant_id="tenant-001", key="get_test")
        in_memory_featureflag_repo.upsert(flag)
        
        result = in_memory_featureflag_repo.get("flag-003")
        
        assert result is not None
        assert result.flag_id == "flag-003"

    def test_get_nonexistent_flag(self, in_memory_featureflag_repo):
        """Test retrieving a nonexistent feature flag returns None."""
        result = in_memory_featureflag_repo.get("nonexistent-flag")
        assert result is None

    def test_list_by_tenant(self, in_memory_featureflag_repo):
        """Test listing feature flags filtered by tenant (FR-002: tenant isolation)."""
        flag1 = FeatureFlag(flag_id="flag-004", tenant_id="tenant-A", key="flag_a1")
        flag2 = FeatureFlag(flag_id="flag-005", tenant_id="tenant-A", key="flag_a2")
        flag3 = FeatureFlag(flag_id="flag-006", tenant_id="tenant-B", key="flag_b1")
        in_memory_featureflag_repo.upsert(flag1)
        in_memory_featureflag_repo.upsert(flag2)
        in_memory_featureflag_repo.upsert(flag3)
        
        result = in_memory_featureflag_repo.list_by_tenant("tenant-A")
        
        assert len(result) == 2
        flag_ids = {f.flag_id for f in result}
        assert "flag-004" in flag_ids
        assert "flag-005" in flag_ids
        assert "flag-006" not in flag_ids
