"""Deprecation utility (IMPL-XCUT-06).

Provides helper to mark responses as deprecated with standard headers.
Header: Deprecation: true and optional Sunset and Link per RFC 8594 style.
"""
from __future__ import annotations
from typing import Any, Optional
from fastapi import Response


def set_deprecation(response: Response, sunset: Optional[str] = None, link: Optional[str] = None) -> None:
    response.headers["Deprecation"] = "true"
    if sunset:
        response.headers["Sunset"] = sunset
    if link:
        response.headers["Link"] = f"<{link}>; rel=deprecation"


class DeprecationMiddleware:
    """Example middleware to attach deprecation headers to specific paths.
    For demonstration we mark /v1/feature-flags as deprecated list endpoint.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:  # pragma: no cover - passthrough wrapper small
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        async def send_wrapper(message: Any) -> None:
            if message.get("type") == "http.response.start" and scope.get("path") == "/v1/feature-flags":
                headers = message.setdefault("headers", [])
                headers.append((b"deprecation", b"true"))
            await send(message)
        await self.app(scope, receive, send_wrapper)

__all__ = ["set_deprecation", "DeprecationMiddleware"]
