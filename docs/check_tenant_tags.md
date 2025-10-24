# Tenant Tags Analysis

## Current Structure:

### 1. "tenants" tag (Legacy CRUD)
**Router:** `tenants_crud.py`
**Prefix:** `/v1/tenants`
**Mounted at:** `/api` → Full path: `/api/v1/tenants`
**Tag:** `["tenants"]`

**Endpoints:**
- POST /api/v1/tenants - Create tenant
- GET /api/v1/tenants - List tenants  
- DELETE /api/v1/tenants/{tenant_id} - Soft delete tenant
- POST /api/v1/tenants/{tenant_id}/restore - Restore tenant

### 2. "tenant-scoped" tag (Scoped Operations)
**Router:** `tenants/__init__.py` + sub-routers
**Prefix:** `/tenants` (parent)
**Mounted at:** `/api/v1` → Full path: `/api/v1/tenants/{tenant_id}/*`
**Tag:** `["tenant-scoped"]`

**Endpoints:**
- GET /api/v1/tenants/{tenant_id}/users - List users in tenant
- GET /api/v1/tenants/{tenant_id}/audit - List audit events in tenant

## Question: Is this duplication?

**NO!** These are semantically different:

- **"tenants"** = Operations ON tenants (CRUD the tenant object itself)
- **"tenant-scoped"** = Operations WITHIN a tenant (users, audit in a specific tenant)

## Should they be consolidated?

### Option 1: Keep Separate (RECOMMENDED ✅)
**Reason:** Clear distinction between:
- Managing tenants (create, list, delete tenants)
- Operating within a tenant (list users/audit in that tenant)

### Option 2: Consolidate under "Tenant Management"
Change both to use the same tag:
```python
# tenants_crud.py
router = APIRouter(prefix="/v1/tenants", tags=["Tenant Management"])

# tenants/users.py and tenants/audit.py
router = APIRouter(prefix="/{tenant_id}/users", tags=["Tenant Management"])
```

**Result:** All tenant-related operations in ONE section

### Option 3: Use Hierarchical Tags
```python
# tenants_crud.py
tags=["Tenants - Management"]

# tenants/users.py
tags=["Tenants - Scoped Operations"]
```

**Result:** Clear hierarchy, still separate sections

## My Recommendation

**KEEP CURRENT STRUCTURE** ✅

The distinction is valuable:
- "tenants" = I want to manage tenant objects
- "tenant-scoped" = I want to work within a specific tenant

This is clear and logical for frontend developers.

