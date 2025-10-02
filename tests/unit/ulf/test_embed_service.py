from services.embed_service import EmbedService


def test_embed_origin_validation_dev_mode():
    s = EmbedService(secret=b"s", allowed_origins=[])
    assert s.validate_origin("http://localhost:3000")
    assert not s.validate_origin("https://evil.com")


def test_issue_and_verify_token():
    s = EmbedService(secret=b"s", allowed_origins=["https://app.example.com"])
    token = s.issue_embed_token("t1", "u1", ttl_seconds=2)
    assert s.verify_embed_token(token.token)
    # disallowed origin should be rejected when allowlist is set
    assert not s.validate_origin("https://evil.com")
