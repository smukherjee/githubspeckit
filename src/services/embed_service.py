from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional
import hmac
import hashlib
import base64

from domain.featureflags.models import FeatureFlagRepository


@dataclass
class EmbedToken:
    token: str
    tenant_id: str
    user_id: str
    expires_at: datetime


class EmbedService:
    def __init__(self, secret: bytes = b"dev-secret", allowed_origins: Optional[List[str]] = None, audit_service: Any = None) -> None:
        self._secret = secret
        self._allowed_origins = set(allowed_origins or [])
        # lightweight repo usage for feature gate checks if needed
        self._flags = FeatureFlagRepository()
        self._audit = audit_service

    def validate_origin(self, origin: str) -> bool:
        if not self._allowed_origins:
            # dev-mode permissive: allow localhost patterns
            return origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")
        # exact match for now; future: support wildcard or regex entries
        return origin in self._allowed_origins

    def issue_embed_token(self, tenant_id: str, user_id: str, ttl_seconds: int = 300) -> EmbedToken:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        payload = f"{tenant_id}|{user_id}|{int(expires_at.timestamp())}".encode("utf-8")
        sig = hmac.new(self._secret, payload, hashlib.sha256).digest()
        # encode payload and signature separately to avoid delimiter collisions
        payload_b64 = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
        sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
        token = f"{payload_b64}.{sig_b64}"
        et = EmbedToken(token=token, tenant_id=tenant_id, user_id=user_id, expires_at=expires_at)
        if self._audit:
            try:
                self._audit.emit(actor=user_id or "system", action="embed.issue", target={"tenant_id": tenant_id, "user_id": user_id})
            except Exception:
                pass
        return et

    def verify_embed_token(self, token: str) -> bool:
        try:
            # token format: payload_b64.sig_b64 (both urlsafe base64 with padding trimmed)
            parts = token.split(".", 1)
            if len(parts) != 2:
                return False
            payload_b64, sig_b64 = parts
            # restore padding
            def _b64decode_padded(s: str) -> bytes:
                pad = -len(s) % 4
                return base64.urlsafe_b64decode(s + ("=" * pad))

            payload = _b64decode_padded(payload_b64)
            sig = _b64decode_padded(sig_b64)
            expected = hmac.new(self._secret, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, sig):
                return False
            tenant_id, user_id, ts = payload.decode("utf-8").split("|")
            if datetime.now(timezone.utc) >= datetime.fromtimestamp(int(ts), timezone.utc):
                return False
            return True
        except Exception:
            return False


__all__ = ["EmbedService", "EmbedToken"]
