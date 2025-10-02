import pytest
from domain.policy.extension_registry import PolicyExtensionRegistry, ExtensionConflictError

# TEST-POL-12: Extension registry registration (FR-038, C-039)


def test_extension_registry_registration_and_conflict():
    reg = PolicyExtensionRegistry()
    ext = reg.register("res.type", "module.path:pred", "1.0.0")
    assert reg.get("res.type", "1.0.0") == ext
    versions = reg.list_resource_versions("res.type")
    assert len(versions) == 1 and versions[0].version == "1.0.0"
    with pytest.raises(ExtensionConflictError):
        reg.register("res.type", "module.path:pred", "1.0.0")

