"""Documentation generation adapters.

This module provides adapters for generating and managing documentation,
following the hexagonal architecture pattern.
"""

from .embed_docs_generator import generate_embed_docs
from .embed_docs_freshness import assert_embed_docs_fresh

__all__ = [
    "generate_embed_docs",
    "assert_embed_docs_fresh",
]