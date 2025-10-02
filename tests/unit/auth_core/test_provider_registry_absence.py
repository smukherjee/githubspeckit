import pytest
from auth_core import default_registry

# TEST-AUTH-00A: OIDC absence assertion (FR-007, C-036)

def test_only_password_provider_present():
    reg = default_registry()
    assert reg.list_provider_names() == ["password"], "No additional providers expected before OIDC enablement"
