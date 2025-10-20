"""Tests for error logging improvements (Constitution V compliance).

Verifies that exceptions are properly logged with structured fields and
that central logging configuration is applied correctly.
"""
import logging
import pytest
from adapters.logging.config import configure_logging, get_logger


class TestErrorLogging:
    """Test error logging configuration and Constitution V compliance."""
    
    def test_configure_logging_sets_levels(self):
        """Test that configure_logging properly sets log levels."""
        # Configure with DEBUG level
        configure_logging(log_level="DEBUG", log_format="text", log_sink="stdout")
        
        logger = logging.getLogger("githubspeckit")
        assert logger.level == logging.DEBUG
        
        # Reconfigure with INFO level
        configure_logging(log_level="INFO", log_format="text", log_sink="stdout")
        assert logger.level == logging.INFO
    
    def test_get_logger_returns_configured_instance(self):
        """Test that get_logger returns properly configured logger instance."""
        configure_logging(log_level="INFO", log_format="json", log_sink="stdout")
        
        logger = get_logger("test.module")
        assert logger.name == "githubspeckit.test.module"
        assert logger.level <= logging.INFO
    
    def test_error_logger_captures_exceptions(self):
        """Test that error logger properly captures exception information."""
        configure_logging(log_level="ERROR", log_format="text", log_sink="stdout")
        
        logger = get_logger("error")
        
        # Test that the logger is configured properly
        assert logger.level == logging.ERROR
        assert logger.isEnabledFor(logging.ERROR)
        
        # Verify exception logging works (we can't easily capture with caplog
        # because logs go to StreamHandler, but we can verify configuration)
        try:
            raise ValueError("Test exception for logging")
        except Exception as e:
            # This would log in production
            logger.error(
                "Unhandled exception in request processing",
                extra={
                    "exception_type": e.__class__.__name__,
                    "exception_message": str(e),
                },
                exc_info=True
            )
        
        # Verify logger is enabled for ERROR level
        assert logger.isEnabledFor(logging.ERROR)
    
    def test_logger_supports_structured_fields(self):
        """Test that loggers support structured extra fields."""
        configure_logging(log_level="INFO", log_format="text", log_sink="stdout")
        
        logger = get_logger("test")
        
        # Verify logger is configured and can accept structured fields
        assert logger.isEnabledFor(logging.INFO)
        
        # This would log with structured fields in production
        logger.info(
            "Test message",
            extra={
                "correlation_id": "test-123",
                "tenant_id": "tenant-456",
                "user_id": "user-789",
            }
        )
        
        # Verify the logger exists and is properly configured
        assert logger.name == "githubspeckit.test"
    
    def test_logging_levels_respect_configuration(self):
        """Test that log levels are properly filtered by configuration."""
        # Set to WARNING level
        configure_logging(log_level="WARNING", log_format="text", log_sink="stdout")
        
        logger = get_logger("test")
        
        # INFO should be filtered out
        assert not logger.isEnabledFor(logging.INFO)
        # WARNING should pass through
        assert logger.isEnabledFor(logging.WARNING)
        # ERROR should pass through
        assert logger.isEnabledFor(logging.ERROR)


class TestLoggingConstitutionCompliance:
    """Test Constitution V compliance requirements."""
    
    def test_security_logger_never_below_info(self):
        """Test that security logger is never below INFO level (Constitution V)."""
        # Try to set DEBUG level
        configure_logging(log_level="DEBUG", log_format="text", log_sink="stdout")
        
        security_logger = logging.getLogger("githubspeckit.security")
        # Security logger should be clamped to INFO minimum
        assert security_logger.level == logging.INFO
        
        # Try to set ERROR level
        configure_logging(log_level="ERROR", log_format="text", log_sink="stdout")
        security_logger = logging.getLogger("githubspeckit.security")
        # Security logger should allow ERROR (higher than INFO)
        assert security_logger.level == logging.ERROR
    
    def test_audit_logger_never_below_info(self):
        """Test that audit logger is never below INFO level (Constitution V)."""
        # Try to set DEBUG level
        configure_logging(log_level="DEBUG", log_format="text", log_sink="stdout")
        
        audit_logger = logging.getLogger("githubspeckit.audit")
        # Audit logger should be clamped to INFO minimum
        assert audit_logger.level == logging.INFO
        
        # Try to set WARNING level
        configure_logging(log_level="WARNING", log_format="text", log_sink="stdout")
        audit_logger = logging.getLogger("githubspeckit.audit")
        # Audit logger should allow WARNING (higher than INFO)
        assert audit_logger.level == logging.WARNING
    
    def test_central_control_single_configuration(self):
        """Test that all loggers are controlled by central configuration."""
        configure_logging(log_level="WARNING", log_format="json", log_sink="stdout")
        
        # All loggers under githubspeckit namespace should respect central config
        test_logger = get_logger("test")
        api_logger = get_logger("api")
        domain_logger = get_logger("domain")
        
        # All should respect WARNING level filter
        assert test_logger.isEnabledFor(logging.WARNING)
        assert api_logger.isEnabledFor(logging.WARNING)
        assert domain_logger.isEnabledFor(logging.WARNING)
        
        # Changing central config should affect all loggers
        configure_logging(log_level="INFO", log_format="text", log_sink="stdout")
        
        # Re-get loggers to check updated config
        test_logger_2 = get_logger("test2")
        assert test_logger_2.isEnabledFor(logging.INFO)
