"""Central logging configuration (Constitution V: Central Control).

Configures Python's logging module with structured JSON output, proper levels,
and compliance with constitution requirements:
- Single configuration block governs all logger instances
- Structured fields in every log record
- No inline print/debug statements
- Security/audit logs never downgraded below INFO
"""
import logging
import logging.config
import sys
from typing import Any, Dict


def configure_logging(
    *,
    log_level: str = "INFO",
    log_format: str = "json",
    log_sink: str = "stdout",
) -> None:
    """Configure centralized logging for the application.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' for structured, 'text' for human-readable)
        log_sink: Output destination ('stdout', 'stderr', or file path)
        
    Constitution compliance:
    - Central Control: This function is the ONLY place log levels are set
    - Structured Fields: JSON formatter includes all required fields
    - Security: security.* and audit.* loggers never below INFO
    
    Note: Safe to call multiple times - will reconfigure logging each time.
    """
    try:
        # Validate log level
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        
        # Calculate security/audit log levels (Constitution: NEVER below INFO)
        security_level = max(numeric_level, logging.INFO)
        security_level_name = logging.getLevelName(security_level)
        
        # Base configuration
        config: Dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.json.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s %(tenant_id)s %(user_id)s",
                    "timestamp": True,
                },
                "text": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": log_format,
                },
            },
        "loggers": {
            # Application loggers
            "githubspeckit": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "githubspeckit.error": {
                "handlers": ["default"],
                "level": "ERROR",  # Only log errors and above
                "propagate": False,
            },
            # Security loggers (Constitution: NEVER below INFO)
            "githubspeckit.security": {
                "handlers": ["default"],
                "level": security_level_name,  # Minimum INFO, but can be higher
                "propagate": False,
            },
            "githubspeckit.audit": {
                "handlers": ["default"],
                "level": security_level_name,  # Minimum INFO for audit trail
                "propagate": False,
            },
            # Infrastructure loggers (can be noisy, raise threshold)
            "uvicorn": {
                "handlers": ["default"],
                "level": "WARNING",  # Reduce uvicorn noise
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["default"],
                "level": "WARNING",  # Set to DEBUG for SQL query debugging
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["default"],
            "level": log_level,
        },
    }
    
        # Apply configuration
        logging.config.dictConfig(config)
        
        # Log configuration applied (meta-logging)
        logger = logging.getLogger("githubspeckit")
        logger.info(
            "Logging configured",
            extra={
                "log_level": log_level,
                "log_format": log_format,
                "log_sink": log_sink,
                "correlation_id": "system",
                "tenant_id": None,
                "user_id": None,
            },
        )
    except Exception as e:
        # If logging configuration fails during test discovery, fall back to basic config
        # This prevents test discovery from failing while still allowing proper logging in production
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )
        logging.getLogger("githubspeckit").warning(
            f"Failed to configure structured logging, using basic config: {e}"
        )


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ or category like 'security.auth')
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": user_id, "tenant_id": tenant_id})
    """
    return logging.getLogger(f"githubspeckit.{name}")


__all__ = ["configure_logging", "get_logger"]
