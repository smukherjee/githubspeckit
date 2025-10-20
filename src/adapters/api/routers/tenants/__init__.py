"""
Tenant-scoped router package (FR-004 tenant security refactor).

**Route Tier**: TENANT-SCOPED (/api/v1/tenants/{tenant_id}/*)
**Authorization**: Scoped to explicit tenant_id in path

This package contains tenant-scoped routes where the tenant_id is explicitly
specified in the URL path parameter. Authorization middleware ensures users
can only access their own tenant unless they have superadmin role.

**Route Pattern**: `/api/v1/tenants/{tenant_id}/<resource>`

**Authorization Rules**:
- Standard users: Can only access own tenant (tenant_id == JWT tenant_id)
- Tenant admins: Can access own tenant (tenant_id == JWT tenant_id)
- Superadmin: Can access any tenant (cross-tenant access allowed)

**Modules**:
- users.py: User management within specific tenant

Status: Phase 3.4 - Endpoint Implementation (T037)
"""

from fastapi import APIRouter

# Import tenant-scoped sub-routers
from .users import router as users_router

# Main tenant-scoped router
router = APIRouter(prefix="/tenants", tags=["tenant-scoped"])

# Mount sub-routers
router.include_router(users_router)

__all__ = ["router"]
