"""TEST-XCUT-10 Seed script error modes & summary.
Currently expects bootstrap() to return extended summary; starts failing until implemented.
"""
import pytest
from cli.bootstrap import bootstrap


def test_seed_summary_structure():
    res = bootstrap()
    # Will fail until bootstrap returns dict-like summary attributes
    assert hasattr(res, "summary"), "bootstrap result should expose summary attribute (failing until implemented)"
