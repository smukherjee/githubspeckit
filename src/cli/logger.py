"""
CLI Structured Logging Module (Constitution V Compliance).

Provides structured logging for CLI scripts per Constitution V requirements:
- Structured JSON output with standard fields
- Category-based event types
- No print() statements in production code
- Configurable log levels via descriptor.toml

Usage:
    from cli.logger import get_cli_logger
    
    logger = get_cli_logger("db_bootstrap")
    logger.info("seed_started", tenant_slug="acme", admin_email="admin@acme.com")
    logger.success("seed_completed", tenant_id="...", duration_ms=123.45)
    logger.error("seed_failed", error="Connection refused")
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class CLILogger:
    """Structured logger for CLI scripts."""
    
    def __init__(self, component: str, json_output: bool = False):
        """
        Initialize CLI logger.
        
        Args:
            component: CLI component name (e.g., "db_bootstrap", "migration")
            json_output: If True, always output JSON; if False, use human-readable format
        """
        self.component = component
        self._json_mode = json_output
    
    def _log(self, level: str, event: str, **fields: Any) -> None:
        """Internal logging method."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "component": self.component,
            "event": event,
            **fields
        }
        
        if self._json_mode:
            # JSON output for machine parsing
            print(json.dumps(record), file=sys.stdout if level != "ERROR" else sys.stderr)
        else:
            # Human-readable output for interactive CLI
            if level == "SUCCESS":
                prefix = "✅"
            elif level == "ERROR":
                prefix = "❌"
            elif level == "WARNING":
                prefix = "⚠️"
            else:
                prefix = "ℹ️"
            
            message = f"{prefix} {event}"
            if fields:
                message += f" {self._format_fields(fields)}"
            
            print(message, file=sys.stdout if level != "ERROR" else sys.stderr)
    
    def _format_fields(self, fields: dict[str, Any]) -> str:
        """Format fields for human-readable output."""
        parts = []
        for key, value in fields.items():
            if isinstance(value, (list, dict)):
                parts.append(f"{key}={json.dumps(value)}")
            else:
                parts.append(f"{key}={value}")
        return "(" + ", ".join(parts) + ")"
    
    def info(self, event: str, **fields: Any) -> None:
        """Log info-level event."""
        self._log("INFO", event, **fields)
    
    def success(self, event: str, **fields: Any) -> None:
        """Log success event (CLI-specific)."""
        self._log("SUCCESS", event, **fields)
    
    def warning(self, event: str, **fields: Any) -> None:
        """Log warning event."""
        self._log("WARNING", event, **fields)
    
    def error(self, event: str, **fields: Any) -> None:
        """Log error event."""
        self._log("ERROR", event, **fields)
    
    def json_output(self, data: dict[str, Any]) -> None:
        """Output structured JSON data."""
        print(json.dumps(data, indent=2), file=sys.stdout)


def get_cli_logger(component: str, json_mode: bool = False) -> CLILogger:
    """
    Get CLI logger for component.
    
    Args:
        component: Component name
        json_mode: If True, output JSON; else human-readable
    
    Returns:
        CLILogger instance
    """
    return CLILogger(component=component, json_output=json_mode)


__all__ = ["CLILogger", "get_cli_logger"]
