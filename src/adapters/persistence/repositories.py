"""
IMPL-DB-05: SQLAlchemy persistence adapters implementing repository interfaces.

Provides async database-backed implementations of domain repository interfaces:
- TenantRepository: Multi-tenant root with soft delete support
- UserRepository: Tenant-scoped users with soft delete
- PolicyRepository: Authorization rules with tenant scoping
- FeatureFlagRepository: Feature toggles with tenant scoping

Architecture:
- Async SQLAlchemy sessions for all operations
- Tenant isolation enforced at query level (FR-002)
- Soft delete via status filters (FR-018)
- Transaction management via session context
- Error handling with domain-appropriate exceptions

Status: Phase 3 Lane DB-B
Dependencies: IMPL-DB-02 (models), IMPL-DB-03 (migrations), TEST-DB-01 (contracts)
Next: TEST-DB-06 (seed idempotency tests)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.models import (
    TenantModel,
    UserModel,
    UserRoleModel,
    PolicyModel,
    FeatureFlagModel,
    TenantStatusEnum,
    UserStatusEnum,
)
from domain.tenants.models import Tenant, TenantStatus
from domain.users.models import User, UserStatus
from domain.policy.models import Policy, PolicyRule, Decision
from domain.featureflags.models import FeatureFlag, FlagState


# Conversion utilities (ORM model ↔ Domain entity)

def tenant_model_to_domain(model: TenantModel) -> Tenant:
    """Convert TenantModel (ORM) to Tenant (domain entity)."""
    return Tenant(
        tenant_id=str(model.tenant_id),
        name=model.name,
        status=TenantStatus(model.status.value),
        config_version=model.config_version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=str(model.created_by) if model.created_by else None,
        updated_by=str(model.updated_by) if model.updated_by else None,
    )


def tenant_domain_to_model(entity: Tenant) -> TenantModel:
    """Convert Tenant (domain entity) to TenantModel (ORM)."""
    return TenantModel(
        tenant_id=UUID(entity.tenant_id),
        name=entity.name,
        status=TenantStatusEnum(entity.status.value),
        config_version=entity.config_version,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=UUID(entity.created_by) if entity.created_by else None,
        updated_by=UUID(entity.updated_by) if entity.updated_by else None,
    )


def user_model_to_domain(model: UserModel, roles: list[str]) -> User:
    """Convert UserModel (ORM) to User (domain entity)."""
    return User(
        user_id=str(model.user_id),
        tenant_id=str(model.tenant_id),
        email=model.email,
        status=UserStatus(model.status.value),
        roles=roles,
        password_hash=model.password_hash,
        last_login_at=model.last_login_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=str(model.created_by) if model.created_by else None,
        updated_by=str(model.updated_by) if model.updated_by else None,
    )


def user_domain_to_model(entity: User) -> UserModel:
    """Convert User (domain entity) to UserModel (ORM)."""
    return UserModel(
        user_id=UUID(entity.user_id),
        tenant_id=UUID(entity.tenant_id),
        email=entity.email,
        status=UserStatusEnum(entity.status.value),
        password_hash=entity.password_hash,
        last_login_at=entity.last_login_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=UUID(entity.created_by) if entity.created_by else None,
        updated_by=UUID(entity.updated_by) if entity.updated_by else None,
    )


def policy_model_to_domain(model: PolicyModel) -> Policy:
    """Convert PolicyModel (ORM) to Policy (domain entity)."""
    rules = [
        PolicyRule(
            rule_id=r["rule_id"],
            version=r["version"],
            resource=r["resource"],
            action=r["action"],
            effect=Decision(r["effect"]),
            condition=r.get("condition"),
        )
        for r in model.rules
    ]
    return Policy(
        policy_id=str(model.policy_id),
        tenant_id=str(model.tenant_id),
        name=model.name,
        rules=rules,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=str(model.created_by) if model.created_by else None,
        updated_by=str(model.updated_by) if model.updated_by else None,
    )


def policy_domain_to_model(entity: Policy) -> PolicyModel:
    """Convert Policy (domain entity) to PolicyModel (ORM)."""
    rules_json = [
        {
            "rule_id": r.rule_id,
            "version": r.version,
            "resource": r.resource,
            "action": r.action,
            "effect": r.effect.value,
            "condition": r.condition,
        }
        for r in entity.rules
    ]
    return PolicyModel(
        policy_id=UUID(entity.policy_id),
        tenant_id=UUID(entity.tenant_id),
        name=entity.name,
        rules=rules_json,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=UUID(entity.created_by) if entity.created_by else None,
        updated_by=UUID(entity.updated_by) if entity.updated_by else None,
    )


def featureflag_model_to_domain(model: FeatureFlagModel) -> FeatureFlag:
    """Convert FeatureFlagModel (ORM) to FeatureFlag (domain entity)."""
    return FeatureFlag(
        flag_id=str(model.flag_id),
        tenant_id=str(model.tenant_id),
        key=model.key,
        state=FlagState(model.state.value),
        variant=model.variant,
        rules=model.rules,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=str(model.created_by) if model.created_by else None,
        updated_by=str(model.updated_by) if model.updated_by else None,
    )


def featureflag_domain_to_model(entity: FeatureFlag) -> FeatureFlagModel:
    """Convert FeatureFlag (domain entity) to FeatureFlagModel (ORM)."""
    from adapters.persistence.models import FlagStateEnum
    
    return FeatureFlagModel(
        flag_id=UUID(entity.flag_id),
        tenant_id=UUID(entity.tenant_id),
        key=entity.key,
        state=FlagStateEnum(entity.state.value),
        variant=entity.variant,
        rules=entity.rules,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=UUID(entity.created_by) if entity.created_by else None,
        updated_by=UUID(entity.updated_by) if entity.updated_by else None,
    )


# Repository Implementations

class SQLAlchemyTenantRepository:
    """
    Database-backed tenant repository (FR-002, FR-018).
    
    Implements async CRUD operations with soft delete support.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, tenant: Tenant) -> Tenant:
        """Insert or update tenant."""
        model = tenant_domain_to_model(tenant)
        
        # Check if exists
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.tenant_id == model.tenant_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.name = model.name
            existing.status = model.status
            existing.config_version = model.config_version
            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by = model.updated_by
            await self.session.flush()
            return tenant_model_to_domain(existing)
        else:
            # Insert new
            self.session.add(model)
            await self.session.flush()
            return tenant_model_to_domain(model)

    async def get(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.tenant_id == UUID(tenant_id))
        )
        model = result.scalar_one_or_none()
        return tenant_model_to_domain(model) if model else None

    async def list(self) -> list[Tenant]:
        """List all active tenants (excludes soft-deleted per FR-018)."""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.status != TenantStatusEnum.soft_deleted)
        )
        models = result.scalars().all()
        return [tenant_model_to_domain(m) for m in models]

    async def soft_delete(self, tenant_id: str) -> None:
        """Soft delete tenant (FR-018)."""
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.tenant_id == UUID(tenant_id))
            .values(
                status=TenantStatusEnum.soft_deleted,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()

    async def restore(self, tenant_id: str) -> None:
        """Restore soft-deleted tenant."""
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.tenant_id == UUID(tenant_id))
            .values(
                status=TenantStatusEnum.active,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()


class SQLAlchemyUserRepository:
    """
    Database-backed user repository (FR-002, FR-018).
    
    Implements async CRUD operations with tenant isolation and soft delete.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, user: User) -> User:
        """Insert or update user."""
        model = user_domain_to_model(user)
        
        # Check if exists
        result = await self.session.execute(
            select(UserModel).where(UserModel.user_id == model.user_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.email = model.email
            existing.status = model.status
            existing.password_hash = model.password_hash
            existing.last_login_at = model.last_login_at
            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by = model.updated_by
            await self.session.flush()
            
            # Update roles
            await self._update_roles(existing.user_id, user.roles)
            
            return user_model_to_domain(existing, user.roles)
        else:
            # Insert new
            self.session.add(model)
            await self.session.flush()
            
            # Insert roles
            await self._update_roles(model.user_id, user.roles)
            
            return user_model_to_domain(model, user.roles)

    async def get(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.user_id == UUID(user_id))
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        # Fetch roles
        roles = await self._get_user_roles(model.user_id)
        return user_model_to_domain(model, roles)

    async def list_by_tenant(self, tenant_id: str) -> list[User]:
        """List users filtered by tenant (FR-002: tenant isolation, FR-018: excludes soft-deleted)."""
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.tenant_id == UUID(tenant_id),
                UserModel.status != UserStatusEnum.disabled
            )
        )
        models = result.scalars().all()
        
        users = []
        for model in models:
            roles = await self._get_user_roles(model.user_id)
            users.append(user_model_to_domain(model, roles))
        
        return users

    async def soft_delete(self, user_id: str) -> None:
        """Soft delete user (FR-018)."""
        await self.session.execute(
            update(UserModel)
            .where(UserModel.user_id == UUID(user_id))
            .values(
                status=UserStatusEnum.disabled,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()

    async def restore(self, user_id: str) -> None:
        """Restore soft-deleted user."""
        await self.session.execute(
            update(UserModel)
            .where(UserModel.user_id == UUID(user_id))
            .where(UserModel.status == UserStatusEnum.disabled)
            .values(
                status=UserStatusEnum.active,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()

    async def _get_user_roles(self, user_id: UUID) -> list[str]:
        """Get roles for user."""
        result = await self.session.execute(
            select(UserRoleModel.role_id).where(UserRoleModel.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def _update_roles(self, user_id: UUID, roles: list[str]) -> None:
        """Update user roles (delete all, insert new)."""
        # Delete existing roles
        from sqlalchemy import delete
        await self.session.execute(
            delete(UserRoleModel).where(UserRoleModel.user_id == user_id)
        )
        
        # Insert new roles
        for role in roles:
            role_model = UserRoleModel(user_id=user_id, role_id=role)
            self.session.add(role_model)
        
        await self.session.flush()


class SQLAlchemyPolicyRepository:
    """
    Database-backed policy repository (FR-030).
    
    Implements async CRUD operations with tenant isolation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, policy: Policy) -> Policy:
        """Insert or update policy."""
        model = policy_domain_to_model(policy)
        
        # Check if exists
        result = await self.session.execute(
            select(PolicyModel).where(PolicyModel.policy_id == model.policy_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.name = model.name
            existing.rules = model.rules
            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by = model.updated_by
            await self.session.flush()
            return policy_model_to_domain(existing)
        else:
            # Insert new
            self.session.add(model)
            await self.session.flush()
            return policy_model_to_domain(model)

    async def get(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        result = await self.session.execute(
            select(PolicyModel).where(PolicyModel.policy_id == UUID(policy_id))
        )
        model = result.scalar_one_or_none()
        return policy_model_to_domain(model) if model else None

    async def list_by_tenant(self, tenant_id: str) -> list[Policy]:
        """List policies filtered by tenant (FR-002: tenant isolation)."""
        result = await self.session.execute(
            select(PolicyModel).where(PolicyModel.tenant_id == UUID(tenant_id))
        )
        models = result.scalars().all()
        return [policy_model_to_domain(m) for m in models]


class SQLAlchemyFeatureFlagRepository:
    """
    Database-backed feature flag repository.
    
    Implements async CRUD operations with tenant isolation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, flag: FeatureFlag) -> FeatureFlag:
        """Insert or update feature flag."""
        model = featureflag_domain_to_model(flag)
        
        # Check if exists
        result = await self.session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_id == model.flag_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.key = model.key
            existing.state = model.state
            existing.variant = model.variant
            existing.rules = model.rules
            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by = model.updated_by
            await self.session.flush()
            return featureflag_model_to_domain(existing)
        else:
            # Insert new
            self.session.add(model)
            await self.session.flush()
            return featureflag_model_to_domain(model)

    async def get(self, flag_id: str) -> Optional[FeatureFlag]:
        """Get feature flag by ID."""
        result = await self.session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_id == UUID(flag_id))
        )
        model = result.scalar_one_or_none()
        return featureflag_model_to_domain(model) if model else None

    async def list_by_tenant(self, tenant_id: str) -> list[FeatureFlag]:
        """List feature flags filtered by tenant (FR-002: tenant isolation)."""
        result = await self.session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == UUID(tenant_id))
        )
        models = result.scalars().all()
        return [featureflag_model_to_domain(m) for m in models]
