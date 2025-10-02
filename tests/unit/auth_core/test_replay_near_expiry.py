import time
from datetime import timedelta
from auth_core.jwt import JWTService, JWTKeySet


# TEST-AUTH-07B: Replay detection near expiry boundary (FR-028, C-020)

def test_replay_near_expiry_placeholder():
    # Construct minimal key set
    ks = JWTKeySet(active_kid="k1", keys={"k1": "secret"})
    svc = JWTService(keys=ks, issuer="test", audience="aud", default_exp_minutes=0)  # default 0 so we'll override
    token = svc.issue(sub="u1", tenant_id="t1", roles=[], expires_in=timedelta(seconds=1))
    time.sleep(0.6)  # near expiry but should still decode
    payload = svc.decode(token, audience="aud")
    assert payload["sub"] == "u1"
    # second decode to simulate potential replay window (placeholder until replay store wired here)
    payload2 = svc.decode(token, audience="aud")
    assert payload2["sub"] == "u1"
