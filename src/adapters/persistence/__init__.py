"""
Persistence adapter package.

Provides SQLAlchemy ORM models and database repository implementations.

Status: Phase 3 (Persistence Layer)
"""
from .models import (
    Base,
    TenantModel,
    UserModel,
    UserRoleModel,
    InvitationModel,
    PasswordResetRequestModel,
    PolicyModel,
    PolicyEvaluationLogModel,
    AuditEventModel,
    FeatureFlagModel,
    KeyRotationRecordModel,
    UserMFAModel,
    # Enums
    TenantStatusEnum,
    UserStatusEnum,
    FlagStateEnum,
    DecisionEnum,
    MFAFactorTypeEnum,
)
from .repositories import (
    SQLAlchemyTenantRepository,
    SQLAlchemyUserRepository,
    SQLAlchemyPolicyRepository,
    SQLAlchemyFeatureFlagRepository,
)

__all__ = [
    # Models
    "Base",
    "TenantModel",
    "UserModel",
    "UserRoleModel",
    "InvitationModel",
    "PasswordResetRequestModel",
    "PolicyModel",
    "PolicyEvaluationLogModel",
    "AuditEventModel",
    "FeatureFlagModel",
    "KeyRotationRecordModel",
    "UserMFAModel",
    # Enums
    "TenantStatusEnum",
    "UserStatusEnum",
    "FlagStateEnum",
    "DecisionEnum",
    "MFAFactorTypeEnum",
    # Repositories
    "SQLAlchemyTenantRepository",
    "SQLAlchemyUserRepository",
    "SQLAlchemyPolicyRepository",
    "SQLAlchemyFeatureFlagRepository",
]
