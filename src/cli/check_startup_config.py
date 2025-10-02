"""Startup configuration validation runner emitting aggregated JSON on failure (FR-041 C-045).

This script simulates config loading; on validation error it prints the required
JSON object to stderr and exits with code 1.
"""
from __future__ import annotations
import sys, json
from domain.config.loader import load_config, ConfigValidationError

def main():  # pragma: no cover thin wrapper
    # Simulate missing required key scenario by providing empty raw dict to force validation fail.
    try:
        load_config(raw={})  # missing required keys triggers ConfigValidationError
    except ConfigValidationError as e:
        issues = []
        # naive parse of missing list from error message
        msg = str(e)
        # expecting format: "missing required config keys: ['APP_NAME', ...]"
        if ": [" in msg:
            missing_part = msg.split(": ")[-1]
            missing_part = missing_part.strip()
            for item in missing_part.strip("[]").replace("'", "").split(","):
                name = item.strip()
                if name:
                    issues.append({"name": name, "error": "missing", "expected_type": "str"})
        payload = {
            "error": "configuration_validation_failed",
            "config_hash": None,
            "issues": sorted(issues, key=lambda x: x["name"]),
        }
        sys.stderr.write(json.dumps(payload) + "\n")
        sys.exit(1)
    # If no error we still exit 0

if __name__ == "__main__":  # pragma: no cover
    main()
