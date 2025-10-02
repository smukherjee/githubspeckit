import pytest
from domain.config.loader import load_config, ConfigImmutableError


def test_config_immutability_guard_blocks_mutation():
    cfg = load_config({
        "APP_NAME": ("svc", False),
        "PASSWORD_MIN_LENGTH": (12, False),
        "PASSWORD_COMPLEXITY_STRICT": (False, False),
    })
    with pytest.raises(ConfigImmutableError):
        cfg.set_value("APP_NAME", "other")
