"""Tenant configuration export bundle generator (FR-035 C-029 placeholder).

Generates a deterministic structure with metadata.json including sha256 hash
computed over sorted file contents (roles.json, policies.json, feature_flags.json, metadata.json excluded from its own hash contribution).
"""
from __future__ import annotations
import json, hashlib, tarfile, io, time
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class PolicyRecord:
    policy_id: str
    version: int
    effect: str

@dataclass
class FeatureFlagRecord:
    flag_key: str
    status: str

@dataclass
class RoleRecord:
    role_id: str
    permissions: List[str]

def build_bundle(roles: List[RoleRecord], policies: List[PolicyRecord], flags: List[FeatureFlagRecord]) -> bytes:
    files: Dict[str, str] = {}
    files["roles.json"] = json.dumps([r.__dict__ for r in roles], separators=(",", ":"), sort_keys=True)
    files["policies.json"] = json.dumps([p.__dict__ for p in policies], separators=(",", ":"), sort_keys=True)
    files["feature_flags.json"] = json.dumps([f.__dict__ for f in flags], separators=(",", ":"), sort_keys=True)
    # compute hash over concatenated sorted content excluding metadata.json itself
    concat = "".join(files[k] for k in sorted(files.keys()))
    digest = hashlib.sha256(concat.encode()).hexdigest()
    metadata = {
        "export_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha256": digest,
    }
    files["metadata.json"] = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    # build tar.gz in-memory
    bio = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=bio) as tf:
        for name, content in files.items():
            data = content.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    return bio.getvalue()

__all__ = ["build_bundle", "RoleRecord", "PolicyRecord", "FeatureFlagRecord"]
