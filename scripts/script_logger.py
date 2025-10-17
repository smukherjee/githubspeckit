"""Structured logging for development and maintenance scripts.

Provides a ScriptLogger class that outputs structured logs in either:
- JSON format (for CI/automation)
- Human-readable format with emojis (for terminal use)

Auto-detects CI environment and switches to JSON mode automatically.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


class ScriptLogger:
    """Structured logger for development/maintenance scripts."""
    
    def __init__(self, script_name: str, json_mode: bool = False):
        """
        Initialize script logger.
        
        Args:
            script_name: Name of the script (e.g., "seed_infysight")
            json_mode: If True, output JSON; if False, human-readable format
        
        NOTE: Script exception - direct os.getenv() allowed for operational scripts
        to detect runtime environment (CI vs development).
        """
        self.script_name = script_name
        self.json_mode = json_mode or self._is_ci_mode()
    
    @staticmethod
    def _is_ci_mode() -> bool:
        """Detect if running in CI environment."""
        return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))
    
    def _log(self, level: str, event: str, **kwargs: Any) -> None:
        """
        Internal logging method.
        
        Args:
            level: Log level (INFO, SUCCESS, WARNING, ERROR)
            event: Event identifier
            **kwargs: Additional structured fields
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "script": self.script_name,
            "event": event,
            **kwargs
        }
        
        if self.json_mode:
            output = json.dumps(record)
            file = sys.stderr if level == "ERROR" else sys.stdout
            print(output, file=file)
        else:
            # Human-readable format for development
            emoji = {
                "INFO": "ℹ️ ",
                "SUCCESS": "✅",
                "WARNING": "⚠️ ",
                "ERROR": "❌"
            }.get(level, "  ")
            
            # Format main message
            parts = [f"{emoji} {event}"]
            
            # Add structured fields (excluding common ones)
            details = {k: v for k, v in kwargs.items() if k not in ("timestamp", "level", "script", "event")}
            if details:
                detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
                parts.append(f"({detail_str})")
            
            message = " ".join(parts)
            file = sys.stderr if level == "ERROR" else sys.stdout
            print(message, file=file)
    
    def info(self, event: str, **kwargs: Any) -> None:
        """Log info-level event."""
        self._log("INFO", event, **kwargs)
    
    def success(self, event: str, **kwargs: Any) -> None:
        """Log success-level event."""
        self._log("SUCCESS", event, **kwargs)
    
    def warning(self, event: str, **kwargs: Any) -> None:
        """Log warning-level event."""
        self._log("WARNING", event, **kwargs)
    
    def error(self, event: str, **kwargs: Any) -> None:
        """Log error-level event."""
        self._log("ERROR", event, **kwargs)
    
    def json_output(self, data: dict) -> None:
        """
        Output structured data as JSON (always, regardless of mode).
        
        Useful for scripts that produce machine-readable output.
        
        Args:
            data: Dictionary to output as JSON
        """
        print(json.dumps(data, indent=2), file=sys.stdout)


# Convenience function for scripts that don't need instance
def get_logger(script_name: str) -> ScriptLogger:
    """
    Get a script logger instance.
    
    Args:
        script_name: Name of the script
        
    Returns:
        ScriptLogger instance
    """
    return ScriptLogger(script_name)
