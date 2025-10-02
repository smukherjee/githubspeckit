"""FastAPI dependency providers (Phase 2 incremental DI refactor).

Centralizes in-memory singletons so routers do not construct services directly.
Will be replaced/extended with persistence adapters in Phase 3.
"""
from functools import lru_cache
from datetime import datetime
from domain.users.models import UserRepository
from domain.invitations.models import InvitationRepository
from services.user_lifecycle_service import UserLifecycleService
from services.invitations_service import InvitationService
from auth_core.registry import default_registry
from auth_core.auth_service import AuthenticationService
from auth_core.jwt import JWTService, JWTKeySet


class InMemoryAuditService:
    """Minimal audit service placeholder for Phase 2.

    Real implementation will append to an audit repository & structured log.
    """
    def __init__(self):
        self.events = []

    def log(self, *, action_type: str, tenant_id: str | None, metadata: dict | None = None):  # pragma: no cover simple storage
        self.events.append({
            "action_type": action_type,
            "tenant_id": tenant_id,
            "metadata": metadata or {},
        })


@lru_cache
def get_user_repo() -> UserRepository:
    return UserRepository()


@lru_cache
def get_invitation_repo() -> InvitationRepository:
    return InvitationRepository()


@lru_cache
def get_user_lifecycle() -> UserLifecycleService:
    return UserLifecycleService(repo=get_user_repo())


@lru_cache
def get_invitation_service() -> InvitationService:
    return InvitationService(repo=get_invitation_repo())


@lru_cache
def get_auth_registry():
    return default_registry()


@lru_cache
def get_jwt_service() -> JWTService:
    # Simple static key set for dev / test; rotation to come later.
    ks = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    return JWTService(keys=ks, issuer="modern-backend", audience="modern-backend")


@lru_cache
def get_auth_service() -> AuthenticationService:
    return AuthenticationService(registry=get_auth_registry())


_audit_singleton = None


def get_audit_service() -> InMemoryAuditService:
    global _audit_singleton
    if _audit_singleton is None:
        _audit_singleton = InMemoryAuditService()
    return _audit_singleton

