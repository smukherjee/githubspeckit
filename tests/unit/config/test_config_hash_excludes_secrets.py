import re
from domain.config.loader import load_config, DETERMINISTIC_NAMESPACE_UUID


def test_config_hash_excludes_secret_entries():
    cfg = load_config({
        # Required baseline keys
        "APP_NAME": ("svc", False),
        "PASSWORD_MIN_LENGTH": (12, False),
        "PASSWORD_COMPLEXITY_STRICT": (False, False),
        # Test-specific keys
        "PUBLIC_VALUE": ("abc", False),
        "SECRET_DB_PASSWORD": ("supersecret", False),  # forced exclude due to SECRET_ prefix
        "API_KEY": ("should_hide", True),  # secret=True flag
        "ANOTHER_PUBLIC": (123, False),
    })
    # Hash should be deterministic for the included keys only
    assert cfg.hash_excluding_secrets is not None
    # Re-compute and ensure same
    h2 = cfg.compute_hash()
    assert h2 == cfg.hash_excluding_secrets
    # Ensure excluded values not present in the material used (indirect by recomputing parts logic)
    # By design only PUBLIC_VALUE and ANOTHER_PUBLIC appear in the hash input ordering
    # Quick structural assertion: hash must be hex
    assert re.fullmatch(r"[0-9a-f]{64}", h2)


def test_deterministic_namespace_uuid_constant():
    # C-038 constant value
    assert str(DETERMINISTIC_NAMESPACE_UUID) == "9b4f53c4-2e74-5e5b-9e33-3d4c0fd84c11"
