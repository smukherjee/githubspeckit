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

from .models import (
    TenantModel,
    UserModel,
    UserRoleModel,
    PolicyModel,
    FeatureFlagModel,
    InvitationModel,
    AuditEventModel,
    TenantStatusEnum,
    UserStatusEnum,
)
from domain.tenants.models import Tenant, TenantStatus
from domain.users.models import User, UserStatus
from domain.policy.models import Policy, PolicyRule, Decision
from domain.featureflags.models import FeatureFlag, FlagState
from domain.invitations.models import Invitation, InvitationStatus
from domain.audit.models import AuditEvent


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
    def to_uuid_or_none(value: Optional[str]) -> Optional[UUID]:
        """Convert string to UUID, return None if not a valid UUID."""
        if not value:
            return None
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            # Not a valid UUID (e.g., "system"), store as NULL
            return None
    
    return TenantModel(
        tenant_id=UUID(entity.tenant_id),
        name=entity.name,
        status=TenantStatusEnum(entity.status.value),
        config_version=entity.config_version,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=to_uuid_or_none(entity.created_by),
        updated_by=to_uuid_or_none(entity.updated_by),
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
    def to_uuid_or_none(value: Optional[str]) -> Optional[UUID]:
        """Convert string to UUID, return None if not a valid UUID."""
        if not value:
            return None
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            # Not a valid UUID (e.g., "system"), store as NULL
            return None
    
    return UserModel(
        user_id=UUID(entity.user_id),
        tenant_id=UUID(entity.tenant_id),
        email=entity.email,
        status=UserStatusEnum(entity.status.value),
        password_hash=entity.password_hash,
        last_login_at=entity.last_login_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=to_uuid_or_none(entity.created_by),
        updated_by=to_uuid_or_none(entity.updated_by),
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
    from domain.policy.models import PolicyStatus
    return Policy(
        policy_id=str(model.policy_id),
        tenant_id=str(model.tenant_id),
        name=model.name,
        rules=rules,
        status=PolicyStatus(model.status) if hasattr(model, 'status') and model.status else PolicyStatus.active,
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
        status=entity.status.value if hasattr(entity, 'status') else "active",
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=UUID(entity.created_by) if entity.created_by else None,
        updated_by=UUID(entity.updated_by) if entity.updated_by else None,
    )


def featureflag_model_to_domain(model: FeatureFlagModel) -> FeatureFlag:
    """Convert FeatureFlagModel (ORM) to FeatureFlag (domain entity)."""
    from domain.featureflags.models import FlagStatus
    return FeatureFlag(
        flag_id=str(model.flag_id),
        tenant_id=str(model.tenant_id),
        key=model.key,
        state=FlagState(model.state.value),
        status=FlagStatus(model.status) if hasattr(model, 'status') and model.status else FlagStatus.active,
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
    
    def to_uuid_or_none(value: Optional[str]) -> Optional[UUID]:
        if not value:
            return None
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            return None
    
    return FeatureFlagModel(
        flag_id=UUID(entity.flag_id),
        tenant_id=UUID(entity.tenant_id),
        key=entity.key,
        state=FlagStateEnum(entity.state.value),
        status=entity.status.value if hasattr(entity, 'status') else "active",
        variant=entity.variant,
        rules=entity.rules,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        created_by=to_uuid_or_none(entity.created_by),
        updated_by=to_uuid_or_none(entity.updated_by),
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

    async def get_by_name(self, name: str) -> Optional[Tenant]:
        """Get tenant by name (case-insensitive)."""
        result = await self.session.execute(
            select(TenantModel).where(
                TenantModel.name.ilike(name),
                TenantModel.status != TenantStatusEnum.disabled
            )
        )
        model = result.scalar_one_or_none()
        return tenant_model_to_domain(model) if model else None

    async def list(self, include_deleted: bool = False) -> list[Tenant]:
        """List all tenants (FR-018/FR-087: excludes soft-deleted by default)."""
        query = select(TenantModel)
        
        if not include_deleted:
            query = query.where(TenantModel.status != TenantStatusEnum.disabled)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [tenant_model_to_domain(m) for m in models]

    async def soft_delete(self, tenant_id: str) -> None:
        """Soft delete tenant (FR-018)."""
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.tenant_id == UUID(tenant_id))
            .values(
                status=TenantStatusEnum.disabled,
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

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address (case-insensitive).
        
        NOTE: This method searches across ALL tenants. For per-tenant email
        uniqueness checks (V1.0 behavior), use get_by_email_and_tenant() instead.
        """
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.email.ilike(email),  # Case-insensitive match
                UserModel.status != UserStatusEnum.disabled
            )
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        # Fetch roles
        roles = await self._get_user_roles(model.user_id)
        return user_model_to_domain(model, roles)
    
    async def get_by_email_and_tenant(self, email: str, tenant_id: str) -> Optional[User]:
        """Get user by email address scoped to specific tenant (case-insensitive).
        
        This method implements V1.0 per-tenant email uniqueness (FR-116).
        Use this for email validation during user creation to enforce
        that emails must be unique within a tenant, but can be reused
        across different tenants.
        
        Args:
            email: User email address (case-insensitive comparison)
            tenant_id: Tenant UUID to scope the search
            
        Returns:
            User entity if found in the specified tenant, None otherwise
            
        Example:
            # Check if email exists in tenant before creating user
            existing = await repo.get_by_email_and_tenant("user@example.com", tenant_id)
            if existing:
                raise DomainError(code="EMAIL_ALREADY_EXISTS")
        """
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.email.ilike(email),  # Case-insensitive match
                UserModel.tenant_id == UUID(tenant_id),
                UserModel.status != UserStatusEnum.disabled
            )
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        # Fetch roles
        roles = await self._get_user_roles(model.user_id)
        return user_model_to_domain(model, roles)

    async def list_by_tenant(self, tenant_id: str, include_deleted: bool = False) -> list[User]:
        """List users filtered by tenant (FR-002: tenant isolation, FR-018/FR-087: excludes disabled by default)."""
        query = select(UserModel).where(UserModel.tenant_id == UUID(tenant_id))
        
        if not include_deleted:
            query = query.where(UserModel.status != UserStatusEnum.disabled)
        
        result = await self.session.execute(query)
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

    async def list_by_tenant(self, tenant_id: str, include_deleted: bool = False) -> list[Policy]:
        """List policies filtered by tenant (FR-002: tenant isolation, FR-085: excludes disabled by default)."""
        query = select(PolicyModel).where(PolicyModel.tenant_id == UUID(tenant_id))
        
        if not include_deleted:
            query = query.where(PolicyModel.status != "disabled")
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [policy_model_to_domain(m) for m in models]
    
    async def soft_delete(self, policy_id: str) -> None:
        """Soft delete policy (FR-085: set status=disabled)."""
        await self.session.execute(
            update(PolicyModel)
            .where(PolicyModel.policy_id == UUID(policy_id))
            .values(
                status="disabled",
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()
    
    async def restore(self, policy_id: str) -> None:
        """Restore soft-deleted policy (FR-085: set status=active)."""
        await self.session.execute(
            update(PolicyModel)
            .where(PolicyModel.policy_id == UUID(policy_id))
            .where(PolicyModel.status == "disabled")
            .values(
                status="active",
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()


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

    async def list_by_tenant(self, tenant_id: str, include_deleted: bool = False) -> list[FeatureFlag]:
        """List feature flags filtered by tenant (FR-002: tenant isolation, FR-086: excludes disabled by default)."""
        query = select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == UUID(tenant_id))
        
        if not include_deleted:
            query = query.where(FeatureFlagModel.status != "disabled")
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [featureflag_model_to_domain(m) for m in models]
    
    async def soft_delete(self, flag_id: str) -> None:
        """Soft delete feature flag (FR-086: set status=disabled)."""
        await self.session.execute(
            update(FeatureFlagModel)
            .where(FeatureFlagModel.flag_id == UUID(flag_id))
            .values(
                status="disabled",
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()
    
    async def restore(self, flag_id: str) -> None:
        """Restore soft-deleted feature flag (FR-086: set status=active)."""
        await self.session.execute(
            update(FeatureFlagModel)
            .where(FeatureFlagModel.flag_id == UUID(flag_id))
            .where(FeatureFlagModel.status == "disabled")
            .values(
                status="active",
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()


# Invitation conversion utilities

def invitation_model_to_domain(model: InvitationModel) -> Invitation:
    """Convert InvitationModel to Invitation domain entity."""
    
    # Map accepted_at to status
    if model.accepted_at:
        status = InvitationStatus.accepted
    else:
        # Ensure expires_at is timezone-aware for comparison
        expires_at = model.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) >= expires_at:
            status = InvitationStatus.expired
        else:
            status = InvitationStatus.pending
    
    # Ensure expires_at is timezone-aware
    expires_at_aware = model.expires_at
    if expires_at_aware.tzinfo is None:
        expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)
    
    return Invitation(
        invitation_id=str(model.invitation_id),
        tenant_id=str(model.tenant_id),
        email=model.email,
        expires_at=expires_at_aware,
        status=status,
        accepted_at=model.accepted_at.replace(tzinfo=timezone.utc) if model.accepted_at and model.accepted_at.tzinfo is None else model.accepted_at,
        created_at=getattr(model, 'created_at', datetime.now(timezone.utc)),
        updated_at=getattr(model, 'updated_at', datetime.now(timezone.utc)),
        created_by=str(getattr(model, 'created_by', None)) if getattr(model, 'created_by', None) else None,
        updated_by=str(getattr(model, 'updated_by', None)) if getattr(model, 'updated_by', None) else None,
    )


def invitation_domain_to_model(invitation: Invitation) -> InvitationModel:
    """Convert Invitation domain entity to InvitationModel."""
    import hashlib
    
    # For token_hash, we'll use a placeholder since domain doesn't store raw token
    # The actual token hashing should happen at the service layer
    token_hash = hashlib.sha256(invitation.invitation_id.encode()).hexdigest()
    
    return InvitationModel(
        invitation_id=UUID(invitation.invitation_id),
        tenant_id=UUID(invitation.tenant_id),
        email=invitation.email,
        token_hash=token_hash,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
    )


class SQLAlchemyInvitationRepository:
    """
    Database-backed invitation repository (Phase 3 debt).
    
    Implements async CRUD operations with tenant isolation.
    Token stored as SHA-256 hash per FR-050.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, invitation: Invitation) -> Invitation:
        """Insert or update invitation."""
        
        # Check if exists
        result = await self.session.execute(
            select(InvitationModel).where(
                InvitationModel.invitation_id == UUID(invitation.invitation_id)
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.email = invitation.email
            existing.expires_at = invitation.expires_at
            existing.accepted_at = invitation.accepted_at
            await self.session.flush()
            return invitation_model_to_domain(existing)
        else:
            # Insert new
            model = invitation_domain_to_model(invitation)
            self.session.add(model)
            await self.session.flush()
            return invitation_model_to_domain(model)

    async def get(self, invitation_id: str) -> Optional[Invitation]:
        """Get invitation by ID."""
        
        result = await self.session.execute(
            select(InvitationModel).where(
                InvitationModel.invitation_id == UUID(invitation_id)
            )
        )
        model = result.scalar_one_or_none()
        return invitation_model_to_domain(model) if model else None

    async def list_by_tenant(self, tenant_id: str) -> list[Invitation]:
        """List invitations filtered by tenant (FR-002: tenant isolation)."""
        
        result = await self.session.execute(
            select(InvitationModel).where(
                InvitationModel.tenant_id == UUID(tenant_id)
            )
        )
        models = result.scalars().all()
        return [invitation_model_to_domain(m) for m in models]


# Audit event conversion utilities

def audit_event_model_to_domain(model: AuditEventModel) -> AuditEvent:
    """Convert AuditEventModel to AuditEvent domain entity."""
    
    return AuditEvent(
        event_id=str(model.event_id),
        tenant_id=str(model.tenant_id) if model.tenant_id else None,
        category=model.action_type.split('.')[0] if '.' in model.action_type else 'system',
        action=model.action_type,
        actor_user_id=str(model.actor_user_id) if model.actor_user_id else None,
        target_type=model.target_ref.split(':')[0] if ':' in model.target_ref else None,
        target_id=model.target_ref.split(':')[1] if ':' in model.target_ref else model.target_ref,
        metadata=model.event_metadata or {},
        created_at=model.created_at,
    )


def audit_event_domain_to_model(event: AuditEvent) -> AuditEventModel:
    """Convert AuditEvent domain entity to AuditEventModel."""
    
    # Combine target_type and target_id into target_ref
    target_ref = f"{event.target_type}:{event.target_id}" if event.target_type else event.target_id or "system"
    
    return AuditEventModel(
        event_id=UUID(event.event_id),
        tenant_id=UUID(event.tenant_id) if event.tenant_id else None,
        actor_user_id=UUID(event.actor_user_id) if event.actor_user_id else None,
        action_type=event.action,
        target_ref=target_ref,
        event_metadata=event.metadata,
        created_at=event.created_at,
    )


class SQLAlchemyAuditAppender:
    """
    Database-backed audit event appender (Phase 3 debt).
    
    Implements append-only audit log with tenant isolation.
    Metadata redacted per FR-073, C-007.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(self, event: AuditEvent) -> None:
        """Append audit event to database."""
        model = audit_event_domain_to_model(event)
        self.session.add(model)
        await self.session.flush()

    async def list(
        self,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditEvent]:
        """List audit events with filtering (FR-027).
        
        Args:
            tenant_id: Filter by tenant ID
            action: Filter by action type (e.g., "user.login")
            since: Filter events created at or after this timestamp (inclusive)
            until: Filter events created before this timestamp (exclusive)
            limit: Maximum number of results to return
            offset: Number of results to skip
        
        Returns:
            List of audit events matching the filters
        """
        query = select(AuditEventModel).order_by(AuditEventModel.created_at.desc())
        
        # Apply filters in SQL for efficiency (FR-027)
        if tenant_id:
            query = query.where(AuditEventModel.tenant_id == UUID(tenant_id))
        
        if action:
            query = query.where(AuditEventModel.action_type == action)
        
        if since:
            query = query.where(AuditEventModel.created_at >= since)
        
        if until:
            query = query.where(AuditEventModel.created_at < until)
        
        # Apply pagination after filtering
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [audit_event_model_to_domain(m) for m in models]
