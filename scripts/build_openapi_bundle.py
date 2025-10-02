"""Build a combined OpenAPI specification from fragment files.

This script:
1. Loads the base fragment first (must define shared components & securitySchemes).
2. Merges additional fragments (auth-policy, observability) by:
   - Merging `paths` (overrides not allowed; will error if duplicate path+method encountered)
   - Merging new component schemas/responses without overwriting existing names
   - Ignoring duplicate shared component sections (e.g., securitySchemes) in non-base fragments
3. Writes a combined YAML with generation header & fragment source annotation.
4. Validates unique operationIds and presence of referenced schemas.

Usage:
  python scripts/build_openapi_bundle.py \
      --out specs/001-modern-enterprise-grade/contracts/openapi-combined.yaml

Requirements: pyyaml (dev dependency) installed.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Set
import yaml

FRAG_ORDER = [
    "openapi-base.yaml",
    "openapi-auth-policy.yaml",
    "openapi-observability.yaml",
]
SHARED_COMPONENT_KEYS = {"securitySchemes"}

CONTRACT_DIR = Path("specs/001-modern-enterprise-grade/contracts")


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_components(base: Dict[str, Any], extra: Dict[str, Any]):
    for section, value in (extra or {}).items():
        if section in SHARED_COMPONENT_KEYS:
            # Skip shared definitions in non-base fragments
            continue
        if section not in base:
            base[section] = value
            continue
        # Both have this component section e.g., schemas/responses/parameters
        if not isinstance(value, dict) or not isinstance(base[section], dict):
            raise ValueError(f"Component section type mismatch for {section}")
        for name, obj in value.items():
            if name in base[section]:
                # Disallow silent overwrite
                raise ValueError(f"Duplicate component name '{name}' in section '{section}'")
            base[section][name] = obj


def merge_paths(base: Dict[str, Any], extra: Dict[str, Any]):
    for path, methods in (extra or {}).items():
        if path not in base:
            base[path] = methods
            continue
        # Path exists; merge methods
        if not isinstance(methods, dict) or not isinstance(base[path], dict):
            raise ValueError(f"Path structure mismatch for {path}")
        for method, op in methods.items():
            lower = method.lower()
            if lower in base[path]:
                raise ValueError(f"Duplicate operation for {method.upper()} {path}")
            base[path][lower] = op


def collect_operation_ids(spec: Dict[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            op_id = op.get("operationId")
            if not op_id:
                raise ValueError(f"Missing operationId for {method.upper()} {path}")
            if op_id in ids:
                raise ValueError(f"Duplicate operationId '{op_id}' for {method.upper()} {path}")
            ids.add(op_id)
    return ids


def validate_refs(spec: Dict[str, Any]):
    schemas = set(((spec.get("components") or {}).get("schemas") or {}).keys())

    def walk(node: Any):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if ref and ref.startswith("#/components/schemas/"):
                target = ref.split("/")[-1]
                if target not in schemas:
                    raise ValueError(f"Unknown schema reference: {ref}")
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(spec.get("paths"))


def build(out_path: Path):
    combined: Dict[str, Any] = {}
    for idx, fname in enumerate(FRAG_ORDER):
        frag_path = CONTRACT_DIR / fname
        if not frag_path.exists():
            raise FileNotFoundError(f"Fragment not found: {frag_path}")
        frag = load_yaml(frag_path)
        if idx == 0:
            # Shallow copy base first
            combined = frag
        else:
            # Merge components
            merge_components(combined.setdefault("components", {}), (frag.get("components") or {}))
            # Merge paths
            merge_paths(combined.setdefault("paths", {}), (frag.get("paths") or {}))

    # Annotate and validate
    combined.setdefault("info", {}).setdefault("x-source-fragments", FRAG_ORDER)
    collect_operation_ids(combined)
    validate_refs(combined)

    header_comment = (
        "# GENERATED FILE - DO NOT EDIT DIRECTLY\n"
        "# Regenerate with: python scripts/build_openapi_bundle.py --out " + str(out_path) + "\n"
    )
    yaml_str = yaml.safe_dump(combined, sort_keys=False)
    out_path.write_text(header_comment + yaml_str, encoding="utf-8")
    print(f"Wrote combined spec to {out_path}")


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True, help="Output path for combined YAML")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    try:
        build(args.out)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
