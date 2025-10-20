"""
Admin router package (FR-004 tenant security refactor).

**Route Tier**: ADMIN (/api/v1/admin/*)
**Authorization**: Superadmin or tenant admin (scoped to own tenant)

This package contains admin-level routes for platform operations:
- context.py: Tenant context switching (superadmin only)
- platform.py: Platform-level operations (future)

Status: Phase 3.4 - Endpoint Implementation (T035)
"""

from fastapi import APIRouter

# Import admin sub-routers
from .context import router as context_router
from .tenants import router as tenants_router
from .users import router as users_router

# Main admin router
router = APIRouter(prefix="/admin", tags=["admin"])

# Mount sub-routers
router.include_router(context_router)
router.include_router(tenants_router)
router.include_router(users_router)

__all__ = ["router"]
