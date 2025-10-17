"""Small embed docs generator stub (IMPL-ULF-10).

Creates a minimal markdown snippet describing the embed exchange endpoint and
origin allowlist semantics. This is intentionally tiny and safe for Phase 2.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone


def generate_embed_docs(out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# Embed Exchange (stub)

Generated: {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}Z

Endpoint: POST /v1/embed/exchange

Headers:
- X-Embed-Origin: origin of the parent frame

Behavior: Validates origin against configured allowlist. Issues short-lived embed token.
"""
    out.write_text(content)
    return out


__all__ = ["generate_embed_docs"]
