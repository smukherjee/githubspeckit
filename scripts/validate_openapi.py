"""Validate and lint OpenAPI fragment consistency.

Combines fragments (base, auth-policy, observability) and ensures there are:
- No duplicate path + method operationIds.
- All referenced component schemas exist.
- Required shared components not redefined in fragment files (securitySchemes duplication check).

Usage (after installing dev deps):
  python scripts/validate_openapi.py
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import Dict, Any, Set

import yaml

BASE = Path("specs/001-modern-enterprise-grade/contracts")
FRAGMENTS = [
    BASE / "openapi-base.yaml",
    BASE / "openapi-auth-policy.yaml",
    BASE / "openapi-observability.yaml",
]

SHARED_COMPONENT_KEYS = {"securitySchemes"}


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    specs = [load_yaml(p) for p in FRAGMENTS]

    # Ensure base provides shared components
    base_components = specs[0].get("components", {})
    for key in SHARED_COMPONENT_KEYS:
        if key not in base_components:
            print(f"ERROR: base fragment missing shared component: {key}", file=sys.stderr)
            return 1

    # Check duplicates of shared components in other fragments
    for p, spec in zip(FRAGMENTS[1:], specs[1:]):
        comp = spec.get("components", {})
        for key in SHARED_COMPONENT_KEYS:
            if key in comp:
                print(f"ERROR: {p.name} should not redefine shared component '{key}'", file=sys.stderr)
                return 1

    # Collect operationIds & component schema names
    operation_ids: Set[str] = set()
    for spec in specs:
        paths = spec.get("paths", {}) or {}
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, op in methods.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                op_id = op.get("operationId")
                if not op_id:
                    print(f"ERROR: Missing operationId for {method.upper()} {path}")
                    return 1
                if op_id in operation_ids:
                    print(f"ERROR: Duplicate operationId '{op_id}' at {method.upper()} {path}")
                    return 1
                operation_ids.add(op_id)

    # Validate combined references (simple check for schema existence)
    schema_names = set(base_components.get("schemas", {}).keys())
    for spec in specs[1:]:
        schema_names.update((spec.get("components", {}) or {}).get("schemas", {}) or {})

    def walk(node: Any):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if ref and ref.startswith("#/components/schemas/"):
                target = ref.split("/")[-1]
                if target not in schema_names:
                    print(f"ERROR: Unknown schema reference: {ref}")
                    raise SystemExit(1)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for spec in specs:
        walk(spec.get("paths", {}))
        walk((spec.get("components", {}) or {}).get("responses", {}))

    print(json.dumps({
        "status": "ok",
        "fragments": [p.name for p in FRAGMENTS],
        "operations": len(operation_ids)
    }, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
