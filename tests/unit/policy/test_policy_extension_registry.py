import pytest
from domain.policy.extension_registry import (
    PolicyExtensionRegistry,
    ExtensionConflictError,
    default_policy_extension_registry,
)


def test_register_and_retrieve_extension():
    registry = PolicyExtensionRegistry()
    ext = registry.register("resource.example", "pkg.module:predicate", "1.0.0")
    assert registry.get("resource.example", "1.0.0") == ext
    versions = registry.list_resource_versions("resource.example")
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"


def test_duplicate_registration_conflict():
    registry = PolicyExtensionRegistry()
    registry.register("resource.example", "pkg.module:predicate", "1.0.0")
    with pytest.raises(ExtensionConflictError):
        registry.register("resource.example", "pkg.module:predicate", "1.0.0")


def test_default_registry_singleton():
    r1 = default_policy_extension_registry()
    r2 = default_policy_extension_registry()
    assert r1 is r2
