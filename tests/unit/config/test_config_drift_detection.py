import pytest

from domain.config.loader import load_config, detect_config_drift, REQUIRED_KEYS, ConfigValidationError

# TEST-CONF-03 Drift detection anomaly audit (FR-040, FR-045)
# Minimal test: ensure drift detects both missing and unexpected keys.

def test_config_drift_detects_missing_and_unexpected():
    # Start with valid baseline containing required keys + an extra
    raw = {
        "APP_NAME": ("speckit", False),
        "PASSWORD_MIN_LENGTH": (12, False),
        "PASSWORD_COMPLEXITY_STRICT": (False, False),
        "EXTRA_FLAG": (True, False),
    }
    cfg = load_config(raw, validate=True, freeze=True)

    # Expected keys purposely omit EXTRA_FLAG and add FUTURE_FLAG to simulate drift
    expected = set(REQUIRED_KEYS + ["FUTURE_FLAG"])  # FUTURE_FLAG missing; EXTRA_FLAG unexpected
    drift = detect_config_drift(cfg, expected)

    assert drift["has_drift"] is True
    assert "FUTURE_FLAG" in drift["missing"]
    assert "EXTRA_FLAG" in drift["unexpected"]


def test_config_drift_no_drift_when_exact_match():
    raw = {
        "APP_NAME": ("speckit", False),
        "PASSWORD_MIN_LENGTH": (12, False),
        "PASSWORD_COMPLEXITY_STRICT": (False, False),
    }
    cfg = load_config(raw, validate=True, freeze=True)
    drift = detect_config_drift(cfg, set(REQUIRED_KEYS))
    assert drift["has_drift"] is False
    assert drift["missing"] == []
    assert drift["unexpected"] == []
