"""Embed rate limit precedence utility (stub for TEST-ULF-13 / FR-058 C-046).

This will compute the HTTP response headers exposing the effective rate limit
values ensuring the embed-specific bucket takes precedence over any global
rate limiting when provided.
"""
from __future__ import annotations

from typing import Optional, Dict


def compute_embed_rate_limit_headers(global_remaining: int, embed_remaining: Optional[int]) -> Dict[str, str]:
  """Return a header dict honoring precedence rules (FR-058 C-046).

  Precedence:
  - If embed_remaining is provided (not None), treat it as authoritative scope 'embed'.
  - Else use global_remaining with scope 'global'.
  Only minimal headers required for Phase 2.
  """
  if embed_remaining is not None:
    return {
      "X-RateLimit-Remaining": str(embed_remaining),
      "X-RateLimit-Scope": "embed",
    }
  return {
    "X-RateLimit-Remaining": str(global_remaining),
    "X-RateLimit-Scope": "global",
  }


__all__ = ["compute_embed_rate_limit_headers"]
