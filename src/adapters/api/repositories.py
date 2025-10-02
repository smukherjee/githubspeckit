"""Shared in-memory repository singletons for Phase 2 (C-050 API-before-DB).

Routers import from here to ensure consistent state across user + auth flows.
"""
from domain.users.models import UserRepository
from domain.invitations.models import InvitationRepository

user_repo = UserRepository()
invitation_repo = InvitationRepository()

__all__ = ["user_repo", "invitation_repo"]
