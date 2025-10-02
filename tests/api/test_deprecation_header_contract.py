from fastapi.testclient import TestClient
from adapters.api.app import create_app

def test_deprecation_header_present_on_feature_flags_list():
    app = create_app()
    client = TestClient(app)
    r = client.get("/v1/feature-flags")
    # Middleware injects Deprecation header for this route per design (TEST-API-DEPRECATION-CONTRACT)
    assert "Deprecation" in r.headers
    # minimal semantic assertion: header value not empty
    assert r.headers["Deprecation"].strip() != ""
