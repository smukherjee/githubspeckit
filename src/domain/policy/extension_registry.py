"""Policy Extension Registry (C-039, FR-038).

Maintains registration of resource types and associated predicate references.
This is a minimal in-memory skeleton to enable early tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Tuple

class ExtensionConflictError(Exception):
    pass

@dataclass(frozen=True)
class PolicyExtension:
    resource_type: str
    predicate_ref: str  # import path to predicate function/logic
    version: str        # semantic version string
    created_at: datetime

class PolicyExtensionRegistry:
    def __init__(self) -> None:
        # Key: (resource_type, version)
        self._registry: Dict[Tuple[str, str], PolicyExtension] = {}

    def register(self, resource_type: str, predicate_ref: str, version: str) -> PolicyExtension:
        key = (resource_type, version)
        if key in self._registry:
            raise ExtensionConflictError(f"Extension already registered for {resource_type}@{version}")
        ext = PolicyExtension(
            resource_type=resource_type,
            predicate_ref=predicate_ref,
            version=version,
            created_at=datetime.now(timezone.utc),
        )
        self._registry[key] = ext
        return ext

    def get(self, resource_type: str, version: str) -> PolicyExtension | None:
        return self._registry.get((resource_type, version))

    def list_resource_versions(self, resource_type: str) -> list[PolicyExtension]:
        return [ext for k, ext in self._registry.items() if k[0] == resource_type]

# Singleton accessor (may later become injectable adapter)
_DEFAULT_REGISTRY: PolicyExtensionRegistry = PolicyExtensionRegistry()


def default_policy_extension_registry() -> PolicyExtensionRegistry:
    return _DEFAULT_REGISTRY

__all__ = [
    "PolicyExtension",
    "PolicyExtensionRegistry",
    "ExtensionConflictError",
    "default_policy_extension_registry",
]
