"""Embed docs freshness check (IMPL-ULF-12 placeholder).

Will be used in CI to assert the embed docs artifact was (re)generated
recently (per clarification C-047 / FR-059). For now this is a stub
raising NotImplemented so the corresponding test (TEST-ULF-11) fails
until implemented.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone


def assert_embed_docs_fresh(path: str | Path, max_age_seconds: int = 86_400) -> bool:
    """Return True if the embed docs at path are fresh.

    Rules:
    - File must exist.
    - Must contain a line beginning with 'Generated:' and an ISO8601 timestamp ending with 'Z'.
    - Timestamp interpreted as UTC; if naive it is assumed UTC.
    - Age (current UTC - timestamp) must be <= max_age_seconds.
    Returns True when fresh, False when stale or format invalid.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        lines = p.read_text().splitlines()
    except Exception:
        return False
    gen_line = next((l for l in lines if l.startswith("Generated:")), None)
    if not gen_line:
        return False
    ts_part = gen_line[len("Generated:"):].strip()
    if not ts_part.endswith("Z"):
        return False
    ts_txt = ts_part[:-1]  # drop trailing Z
    try:
        dt = datetime.fromisoformat(ts_txt)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age = (now - dt).total_seconds()
    return age <= max_age_seconds


__all__ = ["assert_embed_docs_fresh"]
