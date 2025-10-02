import pytest
from domain.config.loader import load_config, ConfigValidationError, REQUIRED_KEYS


def test_required_keys_missing_raises():
    # Provide only subset (omit one required key) to force failure
    partial = {
        "APP_NAME": ("svc", False),
        # Intentionally omit PASSWORD_MIN_LENGTH for failure
        "PASSWORD_COMPLEXITY_STRICT": (False, False),
    }
    with pytest.raises(ConfigValidationError) as exc:
        load_config(partial)
    msg = str(exc.value)
    assert "missing required config keys" in msg
    assert "PASSWORD_MIN_LENGTH" in msg


def test_password_policy_exposed_when_present():
    cfg = load_config({
        "APP_NAME": ("svc", False),
        "PASSWORD_MIN_LENGTH": (12, False),
        "PASSWORD_COMPLEXITY_STRICT": (False, False),
    })
    # Ensure entries exist and values accessible
    assert cfg.entries["PASSWORD_MIN_LENGTH"].value == 12
    assert cfg.entries["PASSWORD_COMPLEXITY_STRICT"].value is False
