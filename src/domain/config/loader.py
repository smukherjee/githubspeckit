"""Configuration loader (C-037, FR-039..FR-048, FR-043 secret omission rule).

Responsibilities:
- Load descriptor-driven config (placeholder data structure for now)
- Produce a stable config hash excluding secrets per C-037
- Provide deterministic namespace UUID constant (C-038)

NOTE: This is an early skeleton; real implementation will parse a descriptor file.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any, Dict, Tuple, List, Iterable
import uuid

# C-038 deterministic namespace UUID constant
DETERMINISTIC_NAMESPACE_UUID = uuid.UUID("9b4f53c4-2e74-5e5b-9e33-3d4c0fd84c11")

@dataclass
class ConfigEntry:
    name: str
    value: Any
    secret: bool = False

class ConfigValidationError(ValueError):
    pass

class ConfigImmutableError(RuntimeError):
    pass

REQUIRED_KEYS = [
    "APP_NAME",
    "PASSWORD_MIN_LENGTH",  # C-001 / FR-009 exposure
    "PASSWORD_COMPLEXITY_STRICT",
]

@dataclass
class AppConfig:
    entries: Dict[str, ConfigEntry] = field(default_factory=dict)
    hash_excluding_secrets: str | None = None
    _immutable: bool = False

    def compute_hash(self) -> str:
        parts: List[str] = []
        for key in sorted(self.entries.keys()):
            entry = self.entries[key]
            if entry.secret or key.startswith("SECRET_"):
                continue
            parts.append(f"{key}={entry.value}")
        digest = sha256("\n".join(parts).encode("utf-8")).hexdigest()
        self.hash_excluding_secrets = digest
        return digest

    def set_value(self, key: str, value: Any) -> None:
        if self._immutable:
            raise ConfigImmutableError("configuration is immutable (FR-043)")
        if key not in self.entries:
            raise KeyError(key)
        self.entries[key].value = value
        self.compute_hash()

    def freeze(self) -> None:
        self._immutable = True

    def export(self) -> dict[str, object]:
        return {
            "hash": self.hash_excluding_secrets,
            "entries": {
                k: {"value": (v.value if not v.secret else "REDACTED"), "secret": v.secret}
                for k, v in self.entries.items()
            }
        }


def load_config(raw: Dict[str, Tuple[Any, bool]] | None = None, *, validate: bool = True, freeze: bool = True) -> AppConfig:
    raw = raw or {}
    entries: Dict[str, ConfigEntry] = {}
    for name, (value, secret_flag) in raw.items():
        entries[name] = ConfigEntry(name=name, value=value, secret=secret_flag)

    if validate:
        missing = [k for k in REQUIRED_KEYS if k not in entries]
        if missing:
            raise ConfigValidationError(f"missing required config keys: {missing}")

    # inject defaults only after validating required baseline presence
    if "PASSWORD_MIN_LENGTH" not in entries:
        entries["PASSWORD_MIN_LENGTH"] = ConfigEntry(name="PASSWORD_MIN_LENGTH", value=12)
    if "PASSWORD_COMPLEXITY_STRICT" not in entries:
        entries["PASSWORD_COMPLEXITY_STRICT"] = ConfigEntry(name="PASSWORD_COMPLEXITY_STRICT", value=False)
    cfg = AppConfig(entries=entries)
    cfg.compute_hash()
    if freeze:
        cfg.freeze()
    return cfg


def detect_config_drift(cfg: AppConfig, expected_keys: Iterable[str]) -> Dict[str, Any]:
    """Detect configuration drift against expected keys set.

    FR-040 / FR-045 minimal implementation:
    - missing: keys expected but absent
    - unexpected: keys present but not expected
    - has_drift: boolean convenience flag
    This is a pure function (no side effects); audit emission will hook later.
    """
    expected_set = set(expected_keys)
    present_keys = set(cfg.entries.keys())
    missing = sorted(list(expected_set - present_keys))
    unexpected = sorted(list(present_keys - expected_set))
    return {
        "missing": missing,
        "unexpected": unexpected,
        "has_drift": bool(missing or unexpected),
    }

__all__ = [
    "ConfigEntry",
    "AppConfig",
    "load_config",
    "DETERMINISTIC_NAMESPACE_UUID",
    "ConfigValidationError",
    "ConfigImmutableError",
    "REQUIRED_KEYS",
    "detect_config_drift",
]
