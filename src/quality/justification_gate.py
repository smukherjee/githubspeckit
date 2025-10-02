"""Justification enforcement gate implementing TEST-SEC-13 / IMPL-SEC-14."""
from __future__ import annotations
from pathlib import Path
import yaml
from datetime import datetime, date, timezone


def validate_justifications_fresh(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    try:
        data = yaml.safe_load(p.read_text()) or {}
    except Exception:
        return False
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return False
    today = datetime.now(timezone.utc).date()
    for e in entries:
        rb = e.get("review_by")
        if not rb:
            return False
        try:
            rb_date = date.fromisoformat(rb)
        except Exception:
            return False
        if rb_date < today:
            return False
    return True


__all__ = ["validate_justifications_fresh"]
