"""TEST-SEC-19: Replay detection explicit store coverage (FR-033 C-020).

Ensures replay store records JTI and rejects reuse.
"""
from quality.replay_store import InMemoryReplayStore


def test_replay_store_rejects_reuse():
    store = InMemoryReplayStore()
    jti = "abc123"
    assert store.register(jti, ttl_seconds=5) is True
    assert store.register(jti, ttl_seconds=5) is False, "Expected replay reuse rejection"
