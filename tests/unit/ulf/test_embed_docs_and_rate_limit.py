from pathlib import Path
from adapters.docs.embed_docs_generator import generate_embed_docs
from adapters.docs.embed_docs_freshness import assert_embed_docs_fresh
from services.embed_rate_limit import compute_embed_rate_limit_headers


def test_embed_docs_freshness(tmp_path: Path):
    """TEST-ULF-11: Newly generated docs should be considered fresh."""
    out = generate_embed_docs(tmp_path / "embed.md")
    assert out.exists()
    # Expect freshness check to pass (return True) once implemented
    assert assert_embed_docs_fresh(out, max_age_seconds=5) is True


def test_embed_docs_freshness_stale(tmp_path: Path):
    """Edge case: stale timestamp should be detected as not fresh."""
    out = generate_embed_docs(tmp_path / "embed.md")
    # Overwrite with an old timestamp to simulate staleness
    out.write_text("""# Embed Exchange (stub)\n\nGenerated: 2000-01-01T00:00:00Z\n""")
    try:
        fresh = assert_embed_docs_fresh(out, max_age_seconds=1)
    except NotImplementedError:
        # Expected until implementation lands; force failure to keep test red
        assert False, "Freshness function not implemented yet"
    else:
        assert fresh is False, "Stale docs should be reported as not fresh"


def test_embed_rate_limit_precedence():
    """TEST-ULF-13: Embed-specific remaining should override global in headers."""
    try:
        headers = compute_embed_rate_limit_headers(global_remaining=5, embed_remaining=2)
    except NotImplementedError:
        assert False, "Rate limit precedence function not implemented yet"
    else:
        assert headers.get("X-RateLimit-Remaining") == "2"
        assert headers.get("X-RateLimit-Scope") == "embed"

    # Fallback when no embed-specific bucket is provided
    try:
        headers2 = compute_embed_rate_limit_headers(global_remaining=7, embed_remaining=None)
    except NotImplementedError:
        assert False, "Rate limit precedence function not implemented yet"
    else:
        assert headers2.get("X-RateLimit-Remaining") == "7"
        assert headers2.get("X-RateLimit-Scope") == "global"
