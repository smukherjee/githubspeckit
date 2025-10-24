"""
Schemathesis-based contract tests for V1.0 OpenAPI specification.

This module uses schemathesis to auto-generate API contract tests from the
OpenAPI spec (contracts/openapi-v1.0.yaml). Schemathesis generates test cases
by analyzing the spec and fuzzing with valid/invalid data.

**Test Coverage**:
- All endpoints defined in OpenAPI spec
- Request/response schema validation
- HTTP status code validation
- Content-type validation
- Security scheme validation (where applicable)

**Running Tests**:
```bash
# Start the server first
uvicorn src.adapters.api.app:app --reload --port 8000

# Run schemathesis CLI in another terminal
schemathesis run contracts/openapi-v1.0.yaml \\
    --base-url http://localhost:8000 \\
    --checks all \\
    --hypothesis-max-examples 10 \\
    --exclude-by-tag admin  # Skip admin endpoints (require auth)

# For CI/CD integration
schemathesis run contracts/openapi-v1.0.yaml \\
    --base-url http://localhost:8000 \\
    --junit-xml reports/schemathesis-junit.xml \\
    --hypothesis-max-examples 5
```

**Note**: These tests complement manually-written contract tests. Schemathesis
provides broader coverage through property-based testing, while manual tests
target specific business scenarios (e.g., email uniqueness).

**Implementation Status**:
- ✅ OpenAPI V1.0 spec generated (contracts/openapi-v1.0.yaml)
- ✅ Schemathesis installed via pip
- ✅ CLI usage documented above
- ⏸️ pytest integration skipped (CLI is simpler for contract testing)

Status: Phase 3.4 - T048 (OpenAPI V1.0 Generation)
"""
import pytest


# This test file is a placeholder for schemathesis-based contract testing.
# The actual tests are run via the schemathesis CLI (see docstring above).
# We keep this file for documentation and to track the testing approach.


pytestmark = pytest.mark.skip(
    reason=(
        "Schemathesis tests are run via CLI, not pytest. "
        "See module docstring for usage instructions."
    )
)


def test_schemathesis_placeholder():
    """
    Placeholder test to document schemathesis usage.
    
    To run schemathesis contract tests:
    1. Start server: uvicorn src.adapters.api.app:app --port 8000
    2. Run tests: schemathesis run contracts/openapi-v1.0.yaml --base-url http://localhost:8000
    
    This provides auto-generated contract tests for all API endpoints.
    """
    pytest.skip("Use schemathesis CLI instead of pytest")

