"""Configuration loader (C-037, FR-039..FR-048, FR-043 secret omission rule).

Responsibilities:
- Load descriptor-driven config (placeholder data structure for now)
- Produce a stable config hash excluding secrets per C-037
- Provide deterministic namespace UUID constant (C-038)

NOTE: This is an early skeleton; real implementation will parse a descriptor file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, Tuple
import os
import uuid

# C-038 deterministic namespace UUID constant
DETERMINISTIC_NAMESPACE_UUID = uuid.UUID("9b4f53c4-2e74-5e5b-9e33-3d4c0fd84c11")

@dataclass
class ConfigEntry:
    name: str
    value: Any
    secret: bool = False

@dataclass
class AppConfig:
    entries: Dict[str, ConfigEntry] = field(default_factory=dict)
    hash_excluding_secrets: str | None = None

    def compute_hash(self) -> str:
        """Compute configuration hash excluding secrets (C-037).
        Exclusion rules:
        - Any entry with secret=True
        - Any env var whose name starts with SECRET_ (defensive exclusion)
        Stable ordering: sort by key name.
        """
        parts: list[str] = []
        for key in sorted(self.entries.keys()):
            entry = self.entries[key]
            if entry.secret:
                continue
            if key.startswith("SECRET_"):
                continue
            parts.append(f"{key}={entry.value}")
        digest = sha256("\n".join(parts).encode("utf-8")).hexdigest()
        self.hash_excluding_secrets = digest
        return digest


def load_config(raw: Dict[str, Tuple[Any, bool]] | None = None) -> AppConfig:
    """Load configuration from a raw mapping of name -> (value, secret_flag).
    In future this will read the unified descriptor artifact.
    """
    raw = raw or {}
    entries: Dict[str, ConfigEntry] = {}
    for name, (value, secret_flag) in raw.items():
        entries[name] = ConfigEntry(name=name, value=value, secret=secret_flag)
    cfg = AppConfig(entries=entries)
    cfg.compute_hash()
    return cfg

__all__ = [
    "ConfigEntry",
    "AppConfig",
    "load_config",
    "DETERMINISTIC_NAMESPACE_UUID",
]
