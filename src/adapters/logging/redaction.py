from typing import Any, Dict, Tuple

REDACT_KEYS = {
    "password",
    "password_hash",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "authorization",
    "set-cookie",
    "mfa_secret",
    "email",
    "pii_hint",
}


def _redact_value(val: Any) -> Any:
    # non-destructive redact marker
    return "REDACTED"


def redact_dict(obj: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Return (redacted_obj, had_secret)

    had_secret is True if any configured sensitive key was present (case-insensitive).
    """
    had = False
    out: Dict[str, Any] = {}
    for k, v in obj.items():
        lk = k.lower()
        if lk in REDACT_KEYS:
            out[k] = _redact_value(v)
            had = True
        elif isinstance(v, dict):
            sub, sub_had = redact_dict(v)
            out[k] = sub
            had = had or sub_had
        else:
            out[k] = v
    return out, had


__all__ = ["redact_dict", "REDACT_KEYS"]
