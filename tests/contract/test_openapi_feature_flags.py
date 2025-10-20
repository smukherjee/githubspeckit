import pytest


# Skip all tests - API routes commented out
pytestmark = pytest.mark.skip(reason="API routes hidden from OpenAPI docs - feature-flags and policies endpoints commented out in app.py")

@pytest.mark.contract
@pytest.mark.skip(reason="Feature flags API routes hidden from OpenAPI docs - endpoints commented out in app.py")
def test_feature_flags_contract_placeholder():
    pytest.skip("Feature flags endpoint contract tests not implemented yet")
