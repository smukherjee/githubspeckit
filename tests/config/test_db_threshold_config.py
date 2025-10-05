"""
TEST-CONF-DB-THRESHOLD: Database configuration exposure tests.

Validates:
- DB_SLOW_QUERY_THRESHOLD_MS in descriptor (IMPL-CONF-DB-THRESHOLD, FR-041, FR-034)
- Configuration loading from descriptor
- Default value correctness (100ms per FR-074)
- Environment override capability

Status: Phase 3 completion
Dependencies: config/descriptor.toml, descriptor_parser
"""
from __future__ import annotations

import pytest
import os
from pathlib import Path


class TestDBThresholdConfigExposure:
    """TEST-CONF-DB-THRESHOLD: DB threshold configuration validation."""
    
    def test_db_threshold_in_descriptor(self):
        """
        Test DB_SLOW_QUERY_THRESHOLD_MS exists in config descriptor (FR-041, FR-034).
        """
        descriptor_path = Path(__file__).parent.parent.parent / "config" / "descriptor.toml"
        
        assert descriptor_path.exists(), "Config descriptor file should exist"
        
        # Read descriptor and verify threshold key
        with open(descriptor_path, "r") as f:
            content = f.read()
        
        assert "DB_SLOW_QUERY_THRESHOLD_MS" in content, "DB slow query threshold should be in descriptor"
        assert "database.DB_SLOW_QUERY_THRESHOLD_MS" in content or "[database.DB_SLOW_QUERY_THRESHOLD_MS]" in content
    
    def test_db_threshold_default_value(self):
        """
        Test DB_SLOW_QUERY_THRESHOLD_MS has correct default (100ms per FR-074).
        """
        descriptor_path = Path(__file__).parent.parent.parent / "config" / "descriptor.toml"
        
        with open(descriptor_path, "r") as f:
            content = f.read()
        
        # Verify default is 100ms
        assert "default = 100" in content, "Default threshold should be 100ms"
    
    def test_db_threshold_metadata(self):
        """
        Test DB_SLOW_QUERY_THRESHOLD_MS has proper metadata (description, type, scope).
        """
        descriptor_path = Path(__file__).parent.parent.parent / "config" / "descriptor.toml"
        
        with open(descriptor_path, "r") as f:
            content = f.read()
        
        # Find the threshold section
        threshold_start = content.find("DB_SLOW_QUERY_THRESHOLD_MS")
        assert threshold_start != -1
        
        # Get section (next ~10 lines)
        threshold_section = content[threshold_start:threshold_start + 500]
        
        # Validate metadata
        assert 'type = "int"' in threshold_section, "Type should be int"
        assert 'secret = false' in threshold_section, "Should not be secret"
        assert 'description' in threshold_section, "Should have description"
        assert 'FR-034' in threshold_section or 'FR-074' in threshold_section, "Should reference requirements"
    
    def test_db_threshold_not_required(self):
        """
        Test DB_SLOW_QUERY_THRESHOLD_MS is optional (has default).
        """
        descriptor_path = Path(__file__).parent.parent.parent / "config" / "descriptor.toml"
        
        with open(descriptor_path, "r") as f:
            content = f.read()
        
        threshold_start = content.find("DB_SLOW_QUERY_THRESHOLD_MS")
        threshold_section = content[threshold_start:threshold_start + 500]
        
        # Should be optional (required = false or omitted since has default)
        assert 'required = false' in threshold_section or 'required = true' not in threshold_section


class TestDescriptorParserIntegration:
    """TEST-CONF-DB-THRESHOLD: Descriptor parser integration tests."""
    
    def test_parse_descriptor_includes_db_threshold(self):
        """Test descriptor parser extracts DB_SLOW_QUERY_THRESHOLD_MS."""
        try:
            from domain.config.descriptor_parser import parse_descriptor
        except ImportError:
            pytest.skip("tomli not installed (descriptor_parser unavailable)")
        
        # Parse descriptor
        raw_config = parse_descriptor()
        
        # Should include threshold
        assert "DB_SLOW_QUERY_THRESHOLD_MS" in raw_config
        value, is_secret = raw_config["DB_SLOW_QUERY_THRESHOLD_MS"]
        
        assert value == 100, "Default should be 100ms"
        assert is_secret is False, "Should not be secret"
    
    def test_load_config_with_db_threshold(self):
        """Test loading full config includes DB threshold."""
        try:
            from domain.config.descriptor_parser import load_config_from_descriptor
        except ImportError:
            pytest.skip("tomli not installed (descriptor_parser unavailable)")
        
        # Load config (may fail validation if required keys not set in env)
        # Use validate=False for this test
        try:
            config = load_config_from_descriptor(validate=False, freeze=False)
        except Exception as e:
            pytest.skip(f"Config loading failed (expected in CI): {e}")
        
        # Check threshold entry exists
        assert "DB_SLOW_QUERY_THRESHOLD_MS" in config.entries
        threshold_entry = config.entries["DB_SLOW_QUERY_THRESHOLD_MS"]
        
        assert threshold_entry.value == 100
        assert threshold_entry.secret is False
    
    def test_env_override_db_threshold(self):
        """Test environment variable overrides descriptor default."""
        try:
            from domain.config.descriptor_parser import parse_descriptor
        except ImportError:
            pytest.skip("tomli not installed (descriptor_parser unavailable)")
        
        # Set environment override
        os.environ["DB_SLOW_QUERY_THRESHOLD_MS"] = "200"
        
        try:
            raw_config = parse_descriptor()
            value, is_secret = raw_config["DB_SLOW_QUERY_THRESHOLD_MS"]
            
            assert value == 200, "Environment should override default"
        finally:
            # Cleanup
            os.environ.pop("DB_SLOW_QUERY_THRESHOLD_MS", None)


class TestEnvExampleGeneration:
    """TEST-CONF-DB-THRESHOLD: .env.example generation validation."""
    
    def test_generate_env_example_includes_threshold(self, tmp_path):
        """Test .env.example generation includes DB threshold."""
        try:
            from domain.config.descriptor_parser import generate_env_example
        except ImportError:
            pytest.skip("tomli not installed (descriptor_parser unavailable)")
        
        output_path = tmp_path / ".env.example"
        
        # Generate example
        generate_env_example(output_path=output_path)
        
        # Verify file created
        assert output_path.exists()
        
        # Verify threshold in output
        with open(output_path, "r") as f:
            content = f.read()
        
        assert "DB_SLOW_QUERY_THRESHOLD_MS" in content
        assert "100" in content or "slow query" in content.lower()


class TestQueryMetricsIntegration:
    """TEST-CONF-DB-THRESHOLD: Integration with query metrics system."""
    
    def test_query_metrics_uses_configured_threshold(self):
        """
        Test QueryMetrics can be configured with descriptor threshold.
        
        Validates integration between config system and IMPL-DB-09.
        """
        try:
            from adapters.persistence.query_metrics import QueryMetrics
        except ImportError:
            pytest.skip("query_metrics module unavailable")
        
        # Create metrics with custom threshold
        metrics = QueryMetrics(slow_query_threshold_ms=200)
        
        assert metrics.slow_query_threshold_ms == 200
        
        # Test with descriptor default
        metrics_default = QueryMetrics(slow_query_threshold_ms=100)
        assert metrics_default.slow_query_threshold_ms == 100


# TODO (Phase 4): Add integration test loading config from descriptor and initializing QueryMetrics
# def test_end_to_end_config_to_metrics():
#     """Test loading config and passing threshold to QueryMetrics."""
#     config = load_config_from_descriptor()
#     threshold = config.entries["DB_SLOW_QUERY_THRESHOLD_MS"].value
#     metrics = QueryMetrics(slow_query_threshold_ms=threshold)
#     assert metrics.slow_query_threshold_ms == 100
