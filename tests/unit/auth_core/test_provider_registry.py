import pytest

from auth_core import AuthProviderRegistry, default_registry
from auth_core.providers.password import PasswordAuthProvider


def test_default_registry_contains_only_password_provider():
    reg = default_registry()
    assert reg.list_provider_names() == ["password"], "Registry should expose only password provider in Phase 2"


def test_registering_duplicate_provider_raises():
    reg = AuthProviderRegistry()
    reg.register(PasswordAuthProvider())
    with pytest.raises(ValueError):
        reg.register(PasswordAuthProvider())  # same name should fail
