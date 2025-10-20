"""
Platform administration routes (FR-004 tenant security refactor).

**Route Tier**: ADMIN (/api/v1/admin/platform/*)
**Authorization**: Superadmin only

Future placeholder for platform-level operations:
- System configuration
- Cross-tenant analytics
- Platform health monitoring

Status: Phase 3.4 - Placeholder for future implementation
"""

from fastapi import APIRouter

# Placeholder router for future platform admin routes
router = APIRouter(prefix="/platform", tags=["admin"])

# Example placeholder endpoint (to be implemented in future phases)
# @router.get("/health")
# async def get_platform_health() -> dict:
#     """Get platform-wide health metrics."""
#     pass

__all__ = ["router"]
