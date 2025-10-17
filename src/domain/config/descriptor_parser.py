"""
Configuration descriptor parser (IMPL-CONF-DB-THRESHOLD, FR-039, FR-041).

Parses config/descriptor.toml and creates AppConfig instance.
Validates required keys, applies defaults, generates .env.example.

Status: Phase 3 completion (config system integration)
Dependencies: tomli (TOML parser), domain.config.loader
"""
from __future__ import annotations

import os
import tomli
from pathlib import Path
from typing import Any, Dict, Tuple

from src.domain.config.loader import AppConfig, ConfigEntry, ConfigValidationError


def parse_descriptor(descriptor_path: str | Path = "config/descriptor.toml") -> Dict[str, Tuple[Any, bool]]:
    """
    Parse TOML descriptor file into raw config format.
    
    Args:
        descriptor_path: Path to descriptor.toml file
    
    Returns:
        Dictionary mapping variable name to (value, is_secret) tuple
    
    Raises:
        FileNotFoundError: If descriptor file doesn't exist
        tomli.TOMLDecodeError: If descriptor is invalid TOML
    """
    descriptor_path = Path(descriptor_path)
    
    if not descriptor_path.exists():
        raise FileNotFoundError(f"Config descriptor not found: {descriptor_path}")
    
    with open(descriptor_path, "rb") as f:
        descriptor = tomli.load(f)
    
    raw_config: Dict[str, Tuple[Any, bool]] = {}
    
    # Iterate through sections (app, database, auth, etc.)
    for section_name, section_vars in descriptor.items():
        for var_name, var_spec in section_vars.items():
            # Get value from environment or use default
            env_value = os.getenv(var_name)
            
            if env_value is not None:
                # Parse environment value based on type
                value = _parse_env_value(env_value, var_spec.get("type", "string"))
            elif "default" in var_spec:
                value = var_spec["default"]
            elif var_spec.get("required", False):
                # Required but no value - will be caught by loader validation
                value = None
            else:
                # Optional and no value
                value = None
            
            is_secret = var_spec.get("secret", False)
            
            # Only add to config if value is not None
            if value is not None:
                raw_config[var_name] = (value, is_secret)
    
    return raw_config


def _parse_env_value(value: str, type_spec: str) -> Any:
    """
    Parse environment variable string to typed value.
    
    Args:
        value: String value from environment
        type_spec: Type specification ("string", "int", "bool", "float")
    
    Returns:
        Typed value
    """
    if type_spec == "string":
        return value
    elif type_spec == "int":
        return int(value)
    elif type_spec == "bool":
        return value.lower() in ("true", "1", "yes", "on")
    elif type_spec == "float":
        return float(value)
    else:
        # Unknown type, return as string
        return value


def generate_env_example(
    descriptor_path: str | Path = "config/descriptor.toml",
    output_path: str | Path = ".env.example",
) -> None:
    """
    Generate .env.example file from descriptor (FR-039).
    
    Args:
        descriptor_path: Path to descriptor.toml file
        output_path: Path to output .env.example file
    """
    descriptor_path = Path(descriptor_path)
    output_path = Path(output_path)
    
    with open(descriptor_path, "rb") as f:
        descriptor = tomli.load(f)
    
    lines = [
        "# Auto-generated from config/descriptor.toml (FR-039)",
        "# Copy to .env and fill in your values",
        "",
    ]
    
    for section_name, section_vars in descriptor.items():
        # Add section header
        lines.append(f"# ============================================================================")
        lines.append(f"# {section_name.upper()}")
        lines.append(f"# ============================================================================")
        lines.append("")
        
        for var_name, var_spec in section_vars.items():
            # Add description
            description = var_spec.get("description", "")
            if description:
                lines.append(f"# {description}")
            
            # Add metadata
            required = var_spec.get("required", False)
            secret = var_spec.get("secret", False)
            lines.append(f"# Type: {var_spec.get('type', 'string')} | Required: {required} | Secret: {secret}")
            
            # Add example value
            if secret:
                example_value = "<SECRET_VALUE>"
            elif "default" in var_spec:
                example_value = var_spec["default"]
            else:
                example_value = f"<{var_spec.get('type', 'string').upper()}>"
            
            if required:
                lines.append(f"{var_name}={example_value}")
            else:
                lines.append(f"# {var_name}={example_value}")
            
            lines.append("")
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def load_config_from_descriptor(
    descriptor_path: str | Path = "config/descriptor.toml",
    validate: bool = True,
    freeze: bool = True,
) -> AppConfig:
    """
    Load AppConfig from descriptor file (FR-039, FR-041).
    
    Convenience function combining parse + load.
    
    Args:
        descriptor_path: Path to descriptor.toml file
        validate: Validate required keys (default: True)
        freeze: Freeze config after loading (default: True)
    
    Returns:
        Configured AppConfig instance
    
    Raises:
        ConfigValidationError: If required keys are missing
    """
    from domain.config.loader import load_config
    
    raw_config = parse_descriptor(descriptor_path)
    return load_config(raw_config, validate=validate, freeze=freeze)


__all__ = [
    "parse_descriptor",
    "generate_env_example",
    "load_config_from_descriptor",
]
