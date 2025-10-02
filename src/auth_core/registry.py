from __future__ import annotations

from typing import Dict, List

from .providers.base import AuthProvider
from .providers.password import PasswordAuthProvider


class AuthProviderRegistry:
    """In-memory registry of authentication providers.

    Minimal feature set now:
    - register(provider)
    - get(name)
    - list_provider_names()

    Future extensions (OIDC, MFA) simply call `register()` at startup.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, AuthProvider] = {}

    def register(self, provider: AuthProvider) -> None:
        name = provider.name
        if name in self._providers:
            raise ValueError(f"Auth provider '{name}' already registered")
        self._providers[name] = provider

    def get(self, name: str) -> AuthProvider:
        return self._providers[name]

    def list_provider_names(self) -> List[str]:
        return sorted(self._providers.keys())


def default_registry() -> AuthProviderRegistry:
    """Create a registry preloaded with the password provider only.

    This function is used by tests to assert Phase 2 baseline (Clarification C-024).
    """

    registry = AuthProviderRegistry()
    registry.register(PasswordAuthProvider())
    return registry
