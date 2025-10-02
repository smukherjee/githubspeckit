"""JWT service skeleton (IMPL-AUTH-04) supporting TEST-AUTH-03.

Minimal responsibilities now:
- Issue access tokens (HS256) with standard + custom claims.
- Decode/validate audience & expiration.
- Support key id (kid) selection from an in-memory key set.

Future (not yet implemented):
- Rotation grace (TEST-AUTH-05)
- Revocation / replay cache hooks (TEST-AUTH-07)
- Session version & role downgrade invalidation (FR-021)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import uuid

from jose import jwt


ALGORITHM = "HS256"


@dataclass
class JWTKeySet:
    """In-memory key set with rotation grace handling (C-028 / TEST-AUTH-05).

    - ``keys`` always contains all currently valid secrets (active + grace).
    - ``retired`` maps retiring kid -> grace_end (UTC) after which the key MUST
      be unusable for validation.
    - ``active_kid`` points to the key used for new issuance.

    Rotation semantics:
      1. Call ``rotate(new_kid, new_secret, now, grace_minutes)``.
      2. Previous active kid (if any) is marked retired with grace window.
      3. Validation accepts retired key ONLY until grace_end.
      4. ``prune(now)`` removes any fully expired retired keys.
    """

    active_kid: str
    keys: Dict[str, str]  # kid -> secret value
    retired: Dict[str, datetime] = field(default_factory=dict)  # kid -> grace_end

    def get_active_secret(self) -> str:
        if self.active_kid not in self.keys:
            raise KeyError(f"active kid {self.active_kid} not in key set")
        return self.keys[self.active_kid]

    def get_secret(self, kid: str, *, now: Optional[datetime] = None) -> str:
        if kid not in self.keys:
            raise KeyError(f"kid {kid} not in key set")
        # If key is retired ensure grace not expired
        if kid in self.retired:
            now = now or datetime.now(timezone.utc)
            grace_end = self.retired[kid]
            if now >= grace_end:
                raise KeyError(f"kid {kid} expired after grace window")
        return self.keys[kid]

    def rotate(self, *, new_kid: str, new_secret: str, now: Optional[datetime] = None, grace_minutes: int = 15) -> None:
        """Rotate to a new active key with grace overlap for previous key.

        If the new_kid already exists it raises ValueError (defensive). Grace
        window default aligns with C-004 (15 minutes) unless overridden by
        caller test.
        """
        now = now or datetime.now(timezone.utc)
        if new_kid in self.keys:
            raise ValueError(f"kid {new_kid} already present")
        # Mark previous active as retired
        if self.active_kid in self.keys:
            self.retired[self.active_kid] = now + timedelta(minutes=grace_minutes)
        self.keys[new_kid] = new_secret
        self.active_kid = new_kid

    def prune(self, *, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        expired = [kid for kid, end in self.retired.items() if now >= end]
        for kid in expired:
            # Remove key entirely after grace
            self.keys.pop(kid, None)
            self.retired.pop(kid, None)


class JWTService:
    def __init__(self, *, keys: JWTKeySet, issuer: str, audience: str, default_exp_minutes: int = 15):
        self.keys = keys
        self.issuer = issuer
        self.audience = audience
        self.default_exp_minutes = default_exp_minutes

    def issue(
        self,
        *,
        sub: str,
        tenant_id: str,
        roles: List[str],
        now: Optional[datetime] = None,
        expires_in: Optional[timedelta] = None,
        session_id: Optional[str] = None,
        session_version: Optional[int] = None,
        extra: Optional[Dict[str, str]] = None,
    ) -> str:
        now = now or datetime.now(timezone.utc)
        exp_delta = expires_in or timedelta(minutes=self.default_exp_minutes)
        exp = now + exp_delta
        kid = self.keys.active_kid
        claims = {
            "sub": sub,
            "tenant_id": tenant_id,
            "roles": roles,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "kid": kid,
            "jti": str(uuid.uuid4()),
        }
        if session_id:
            claims["sid"] = session_id
        if session_version is not None:
            # future FR-021 claim used by validator (token 'sv')
            claims["sv"] = session_version
        if extra:
            claims.update(extra)
        secret = self.keys.get_active_secret()
        token = jwt.encode(claims, secret, algorithm=ALGORITHM, headers={"kid": kid})
        return token

    def decode(self, token: str, *, audience: Optional[str] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
        # Extract kid from header first to pick correct key
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise ValueError("missing kid header")
        secret = self.keys.get_secret(kid, now=now)
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=audience or self.audience,
            issuer=self.issuer,
            options={"verify_aud": True},
        )
        # Prune any expired retired keys opportunistically
        self.keys.prune(now=now)
        return claims

__all__ = [
    "JWTService",
    "JWTKeySet",
]
