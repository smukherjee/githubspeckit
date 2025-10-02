"""FastAPI application factory and health endpoint (implements part of FR-015).

Currently includes only a minimal health/status endpoint returning migration state
and key rotation version placeholders.
"""
from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Modern Backend", version="0.1.0")

    @app.get("/v1/health", tags=["system"])
    async def health():  # pragma: no cover - simple serialization
        # Placeholder values; will be wired to real services later.
        return {
            "status": "ok",
            "migrations_applied": True,
            "key_rotation_version": 1,
        }

    return app

__all__ = ["create_app"]
