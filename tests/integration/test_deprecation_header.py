"""TEST-XCUT-05 Deprecation header contract.
Checks that /v1/feature-flags GET returns Deprecation header via middleware.
"""
import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.asyncio
@pytest.mark.skip(reason="Feature flags endpoints require authentication - covered by integration tests")
def test_deprecation_header_feature_flags_list(client: httpx.AsyncClient) -> None:
    """FR-099: Test Deprecation header for old endpoints."""
    app = create_app()
    sync_client = TestClient(app)
