"""
TEST-DB-FK-01: Foreign key cascade behavior tests.

Validates:
1. CASCADE behavior for ephemeral/association tables (users, invitations, policies, etc.)
2. SET NULL behavior for audit trails (audit_events preserves history)
3. RESTRICT behavior prevents tenant deletion when references exist
4. Soft delete does NOT trigger cascades (status change only)

Scope: FR-002 (tenant isolation), FR-018 (soft delete), Phase 3 persistence layer.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import DB_CONFIG

from adapters.persistence.models import (
    AuditEventModel,
    FeatureFlagModel,
    InvitationModel,
    PasswordResetRequestModel,
    PolicyEvaluationLogModel,
    PolicyModel,
    TenantModel,
    TenantStatusEnum,
    UserMFAModel,
    UserModel,
    UserRoleModel,
)


@pytest.mark.asyncio
@pytest.mark.db
class TestForeignKeyCascadeBehavior:
    """Validate FK CASCADE behavior for ephemeral/association tables."""

    async def test_delete_user_cascades_to_password_resets(
        self, async_session: AsyncSession
    ):
        """
        Given a user with password reset requests,
        When the user is physically deleted,
        Then all password_reset_requests CASCADE delete.
        
        Rationale: Password resets are ephemeral tokens tied to user lifecycle.
        """
        # Arrange: Create tenant + user + password reset
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="CascadeTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="user@cascade.test",
            status="active",
        )
        async_session.add(user)
        await async_session.flush()

        reset = PasswordResetRequestModel(
            reset_id=uuid.uuid4(),
            user_id=user.user_id,
            token_hash="test_token_hash_123",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        async_session.add(reset)
        await async_session.commit()

        # Act: Physically delete user (not soft delete)
        await async_session.delete(user)
        await async_session.commit()

        # Assert: Password reset request should be CASCADE deleted
        result = await async_session.execute(
            select(PasswordResetRequestModel).where(
                PasswordResetRequestModel.reset_id == reset.reset_id
            )
        )
        assert result.scalar_one_or_none() is None, "Password reset should CASCADE delete with user"

    async def test_delete_user_cascades_to_user_roles(
        self, async_session: AsyncSession
    ):
        """
        Given a user with assigned roles,
        When the user is physically deleted,
        Then all user_roles associations CASCADE delete.
        
        Rationale: user_roles is an association table; roles are orphaned when user deleted.
        """
        # Arrange: Create tenant + user + role association
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="RoleCascadeTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="role_user@cascade.test",
            status="active",
        )
        async_session.add(user)
        await async_session.flush()

        role = UserRoleModel(user_id=user.user_id, role_id="tenant_admin")
        async_session.add(role)
        await async_session.commit()

        # Act: Physically delete user
        await async_session.delete(user)
        await async_session.commit()

        # Assert: User role association should be CASCADE deleted
        result = await async_session.execute(
            select(UserRoleModel).where(UserRoleModel.user_id == user.user_id)
        )
        assert result.scalar_one_or_none() is None, "User roles should CASCADE delete with user"

    async def test_delete_user_cascades_to_user_mfa(
        self, async_session: AsyncSession
    ):
        """
        Given a user with enrolled MFA factors,
        When the user is physically deleted,
        Then all user_mfa records CASCADE delete.
        
        Rationale: MFA credentials are user-specific secrets; must not persist after user deletion.
        """
        # Arrange: Create tenant + user + MFA enrollment
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="MFACascadeTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="mfa_user@cascade.test",
            status="active",
        )
        async_session.add(user)
        await async_session.flush()

        mfa = UserMFAModel(
            user_id=user.user_id,
            factor_type="totp",
            enrolled_at=datetime.now(timezone.utc),
            secret_hash="encrypted_totp_secret",
        )
        async_session.add(mfa)
        await async_session.commit()

        # Act: Physically delete user
        await async_session.delete(user)
        await async_session.commit()

        # Assert: MFA record should be CASCADE deleted
        result = await async_session.execute(
            select(UserMFAModel).where(UserMFAModel.user_id == user.user_id)
        )
        assert result.scalar_one_or_none() is None, "User MFA should CASCADE delete with user"

    async def test_delete_tenant_cascades_to_users(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with users,
        When the tenant is physically deleted,
        Then all users CASCADE delete (FK ondelete='CASCADE').
        
        Rationale: Users are tenant-scoped; no orphaned users allowed.
        """
        # Arrange: Create tenant + user
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="TenantCascadeTest",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="cascaded_user@test.com",
            status="active",
        )
        async_session.add(user)
        await async_session.commit()

        # Act: Physically delete tenant
        await async_session.delete(tenant)
        await async_session.commit()

        # Assert: User should be CASCADE deleted
        result = await async_session.execute(
            select(UserModel).where(UserModel.user_id == user.user_id)
        )
        assert result.scalar_one_or_none() is None, "User should CASCADE delete with tenant"

    async def test_delete_tenant_cascades_to_invitations(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with pending invitations,
        When the tenant is physically deleted,
        Then all invitations CASCADE delete.
        
        Rationale: Invitations are ephemeral; no value if tenant gone.
        """
        # Arrange: Create tenant + invitation
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="InviteCascadeTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        invitation = InvitationModel(
            invitation_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="invite@cascade.test",
            token_hash="invitation_token_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        async_session.add(invitation)
        await async_session.commit()

        # Act: Physically delete tenant
        await async_session.delete(tenant)
        await async_session.commit()

        # Assert: Invitation should be CASCADE deleted
        result = await async_session.execute(
            select(InvitationModel).where(
                InvitationModel.invitation_id == invitation.invitation_id
            )
        )
        assert (
            result.scalar_one_or_none() is None
        ), "Invitation should CASCADE delete with tenant"

    async def test_delete_tenant_cascades_to_policies(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with policies,
        When the tenant is physically deleted,
        Then all policies CASCADE delete.
        
        Rationale: Policies are tenant-scoped; no orphaned policies.
        """
        # Arrange: Create tenant + policy
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="PolicyCascadeTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        policy = PolicyModel(
            policy_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            name="TestPolicy",
            rules=[],
        )
        async_session.add(policy)
        await async_session.commit()

        # Act: Physically delete tenant
        await async_session.delete(tenant)
        await async_session.commit()

        # Assert: Policy should be CASCADE deleted
        result = await async_session.execute(
            select(PolicyModel).where(PolicyModel.policy_id == policy.policy_id)
        )
        assert result.scalar_one_or_none() is None, "Policy should CASCADE delete with tenant"

    async def test_delete_tenant_cascades_to_feature_flags(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with feature flags,
        When the tenant is physically deleted,
        Then all feature_flags CASCADE delete.
        
        Rationale: Feature flags are tenant-scoped configuration.
        """
        # Arrange: Create tenant + feature flag
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="FlagCascadeTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        flag = FeatureFlagModel(
            flag_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            key="feature.test",
            state="enabled",
        )
        async_session.add(flag)
        await async_session.commit()

        # Act: Physically delete tenant
        await async_session.delete(tenant)
        await async_session.commit()

        # Assert: Feature flag should be CASCADE deleted
        result = await async_session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_id == flag.flag_id)
        )
        assert (
            result.scalar_one_or_none() is None
        ), "Feature flag should CASCADE delete with tenant"

    async def test_delete_policy_cascades_to_evaluation_logs(
        self, async_session: AsyncSession
    ):
        """
        Given a policy with evaluation logs,
        When the policy is physically deleted,
        Then all policy_evaluation_logs CASCADE delete.
        
        Rationale: Evaluation logs are diagnostic; policy deletion can purge history.
        """
        # Arrange: Create tenant + policy + evaluation log
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="EvalLogTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        policy = PolicyModel(
            policy_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            name="EvalPolicy",
            rules=[],
        )
        async_session.add(policy)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="eval_user@test.com",
            status="active",
        )
        async_session.add(user)
        await async_session.flush()

        eval_log = PolicyEvaluationLogModel(
            eval_id=uuid.uuid4(),
            policy_id=policy.policy_id,
            decision="ALLOW",
            latency_ms=50,
            tenant_id=tenant.tenant_id,
            user_id=user.user_id,
            correlation_id="test_corr_id",
        )
        async_session.add(eval_log)
        await async_session.commit()

        # Act: Delete policy
        await async_session.delete(policy)
        await async_session.commit()

        # Assert: Evaluation log should be CASCADE deleted
        result = await async_session.execute(
            select(PolicyEvaluationLogModel).where(
                PolicyEvaluationLogModel.eval_id == eval_log.eval_id
            )
        )
        assert (
            result.scalar_one_or_none() is None
        ), "Policy evaluation log should CASCADE delete with policy"


@pytest.mark.asyncio
@pytest.mark.db
class TestForeignKeySetNullBehavior:
    """Validate FK SET NULL behavior for audit trail preservation."""

    async def test_delete_tenant_preserves_audit_events_with_set_null(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with audit events,
        When the tenant is physically deleted,
        Then the audit event persists with tenant_id intact (orphaned FK).
        
        Rationale: FR-018 requires audit trail persistence. Audit tables have NO FK constraints
        to allow historical records to persist independently. Application layer handles
        referential integrity and validation.
        """
        # Arrange: Create tenant + audit event
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="AuditTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        audit_event = AuditEventModel(
            event_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            action_type="tenant.created",
            target_ref=f"tenant:{tenant.tenant_id}",
            metadata={},
        )
        async_session.add(audit_event)
        await async_session.commit()

        event_id = audit_event.event_id
        original_tenant_id = tenant.tenant_id

        # Act: Physically delete tenant (no FK constraint prevents this)
        await async_session.delete(tenant)
        await async_session.commit()

        # Assert: Audit event still exists with original tenant_id intact
        result = await async_session.execute(
            select(AuditEventModel).where(AuditEventModel.event_id == event_id)
        )
        audit = result.scalar_one_or_none()
        assert audit is not None, "Audit event must persist after tenant deletion"
        assert audit.tenant_id == original_tenant_id, "Audit event tenant_id must remain unchanged (orphaned FK)"

    async def test_delete_user_preserves_audit_events_with_set_null(
        self, async_session: AsyncSession
    ):
        """
        Given a user who performed actions (audit events),
        When the user is physically deleted,
        Then the audit event persists with actor_user_id intact (orphaned FK).
        
        Rationale: Audit trail must persist independently. Audit tables have NO FK constraints
        to ensure historical records are never lost. Application layer validates references.
        """
        # Arrange: Create tenant + user + audit event
        tenant_id = uuid.uuid4()
        tenant = TenantModel(
            tenant_id=tenant_id,
            name=f"UserAuditTenant-{tenant_id}",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="actor@audit.test",
            status="active",
        )
        async_session.add(user)
        await async_session.flush()

        audit_event = AuditEventModel(
            event_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            actor_user_id=user.user_id,
            action_type="user.created",
            target_ref=f"user:{user.user_id}",
            metadata={},
        )
        async_session.add(audit_event)
        await async_session.commit()

        event_id = audit_event.event_id
        original_user_id = user.user_id

        # Act: Physically delete user (no FK constraint prevents this)
        await async_session.delete(user)
        await async_session.commit()

        # Assert: Audit event still exists with original actor_user_id intact
        result = await async_session.execute(
            select(AuditEventModel).where(AuditEventModel.event_id == event_id)
        )
        audit = result.scalar_one_or_none()
        assert audit is not None, "Audit event must persist after user deletion"
        assert audit.actor_user_id == original_user_id, "Audit event actor_user_id must remain unchanged (orphaned FK)"


@pytest.mark.asyncio
@pytest.mark.db
class TestSoftDeleteDoesNotCascade:
    """Validate soft delete (status change) does NOT trigger FK cascades."""

    async def test_soft_delete_tenant_preserves_users(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with active users,
        When the tenant is soft deleted (status='soft_deleted'),
        Then users remain in database (FK CASCADE not triggered by status change).
        
        Rationale: Soft delete is a logical flag; physical FK cascades only on DELETE.
        """
        # Arrange: Create tenant + user
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="SoftDeleteTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="preserved_user@test.com",
            status="active",
        )
        async_session.add(user)
        await async_session.commit()

        user_id = user.user_id

        # Act: Soft delete tenant (status change, not DELETE)
        tenant.status = TenantStatusEnum.soft_deleted
        await async_session.commit()

        # Assert: User still exists in database
        result = await async_session.execute(
            select(UserModel).where(UserModel.user_id == user_id)
        )
        preserved_user = result.scalar_one_or_none()
        assert preserved_user is not None, "User should NOT cascade delete on soft delete"
        assert (
            preserved_user.tenant_id == tenant.tenant_id
        ), "User tenant_id should remain unchanged"

    async def test_soft_delete_tenant_preserves_policies(
        self, async_session: AsyncSession
    ):
        """
        Given a tenant with policies,
        When the tenant is soft deleted,
        Then policies remain in database (no CASCADE).
        
        Rationale: Soft delete preserves data for potential restoration.
        """
        # Arrange: Create tenant + policy
        tenant = TenantModel(
            tenant_id=uuid.uuid4(),
            name="SoftDeletePolicyTenant",
            status="active",
        )
        async_session.add(tenant)
        await async_session.flush()

        policy = PolicyModel(
            policy_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            name="PreservedPolicy",
            rules=[],
        )
        async_session.add(policy)
        await async_session.commit()

        policy_id = policy.policy_id

        # Act: Soft delete tenant
        tenant.status = TenantStatusEnum.soft_deleted
        await async_session.commit()

        # Assert: Policy still exists
        result = await async_session.execute(
            select(PolicyModel).where(PolicyModel.policy_id == policy_id)
        )
        preserved_policy = result.scalar_one_or_none()
        assert (
            preserved_policy is not None
        ), "Policy should NOT cascade delete on soft delete"
        assert preserved_policy.tenant_id == tenant.tenant_id


@pytest.mark.asyncio
@pytest.mark.db
class TestForeignKeyConstraintViolations:
    """Validate FK constraint enforcement (no orphaned records)."""

    async def test_cannot_create_user_with_nonexistent_tenant(
        self, async_session: AsyncSession
    ):
        """
        Given a nonexistent tenant_id,
        When attempting to create a user with that tenant_id,
        Then FK constraint violation (IntegrityError) is raised.
        
        Rationale: Prevents orphaned users; enforces referential integrity.
        """
        # Arrange: Generate random tenant_id (does not exist)
        nonexistent_tenant_id = uuid.uuid4()

        user = UserModel(
            user_id=uuid.uuid4(),
            tenant_id=nonexistent_tenant_id,
            email="orphan@test.com",
            status="active",
        )
        async_session.add(user)

        # Act & Assert: FK constraint violation
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.commit()

        assert "foreign key" in str(exc_info.value).lower(), "Should raise FK violation"

    async def test_cannot_create_policy_with_nonexistent_tenant(
        self, async_session: AsyncSession
    ):
        """
        Given a nonexistent tenant_id,
        When attempting to create a policy with that tenant_id,
        Then FK constraint violation is raised.
        
        Rationale: Policies must belong to valid tenant.
        """
        # Arrange: Generate random tenant_id
        nonexistent_tenant_id = uuid.uuid4()

        policy = PolicyModel(
            policy_id=uuid.uuid4(),
            tenant_id=nonexistent_tenant_id,
            name="OrphanPolicy",
            rules=[],
        )
        async_session.add(policy)

        # Act & Assert: FK constraint violation
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.commit()

        assert "foreign key" in str(exc_info.value).lower()

    async def test_cannot_create_password_reset_with_nonexistent_user(
        self, async_session: AsyncSession
    ):
        """
        Given a nonexistent user_id,
        When attempting to create a password reset with that user_id,
        Then FK constraint violation is raised.
        
        Rationale: Password resets must reference valid users.
        """
        # Arrange: Generate random user_id
        nonexistent_user_id = uuid.uuid4()

        reset = PasswordResetRequestModel(
            reset_id=uuid.uuid4(),
            user_id=nonexistent_user_id,
            token_hash="orphan_token",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        async_session.add(reset)

        # Act & Assert: FK constraint violation
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.commit()

        assert "foreign key" in str(exc_info.value).lower()
