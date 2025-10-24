# Admin Routes Structure Explanation

## Question
**"Why does the same API appear under 'admin' and 'admin-context'?"**

## Answer
They are **NOT the same API** - they are different endpoints grouped by **OpenAPI tags** for better documentation organization.

## Current Route Structure

```
/api/v1/admin/                           (prefix from app.py)
    │
    ├── __init__.py                      router = APIRouter(prefix="/admin", tags=["admin"])
    │
    ├── /context/                        router = APIRouter(prefix="/context", tags=["admin-context"])
    │   └── POST /tenant                 → Final URL: /api/v1/admin/context/tenant
    │                                     → OpenAPI Tag: "admin-context"
    │
    ├── /tenants/                        router = APIRouter(prefix="/tenants", tags=["admin-tenants"])
    │   └── (tenant CRUD endpoints)      → Final URL: /api/v1/admin/tenants/*
    │                                     → OpenAPI Tag: "admin-tenants"
    │
    └── /users/                          router = APIRouter(prefix="/users", tags=["admin-users"])
        └── (user CRUD endpoints)        → Final URL: /api/v1/admin/users/*
                                          → OpenAPI Tag: "admin-users"
```

## Why Separate Tags?

OpenAPI/Swagger **groups endpoints by TAGS**, not by URL paths.

### Current Implementation:

**File: `src/adapters/api/routers/admin/__init__.py`**
```python
router = APIRouter(prefix="/admin", tags=["admin"])  # Parent tag

# Sub-routers with their OWN tags
router.include_router(context_router)   # tags=["admin-context"]
router.include_router(tenants_router)   # tags=["admin-tenants"]
router.include_router(users_router)     # tags=["admin-users"]
```

**File: `src/adapters/api/routers/admin/context.py`**
```python
router = APIRouter(prefix="/context", tags=["admin-context"])  # OVERRIDES parent tag
```

When a sub-router has its own `tags`, it **overrides** the parent router's tags.

## In OpenAPI Documentation (/docs)

You'll see these sections:

### 📁 admin
- Empty or generic admin operations (if any were defined directly on the main router)
- Currently likely empty since all operations are in sub-routers

### 📁 admin-context
- `POST /api/v1/admin/context/tenant` - Switch tenant context (superadmin only)

### 📁 admin-tenants  
- `GET /api/v1/admin/tenants` - List tenants
- `POST /api/v1/admin/tenants` - Create tenant
- etc.

### 📁 admin-users
- `GET /api/v1/admin/users` - List admin users
- `POST /api/v1/admin/users` - Create admin user
- etc.

## Is This a Problem?

**No, this is intentional design!** 

### Benefits:
✅ Better organization in Swagger UI  
✅ Each functional area has its own documentation section  
✅ Context switching separate from tenant CRUD  
✅ Tenant management separate from user management  
✅ Easier to find specific endpoints  
✅ Follows REST API best practices for documentation  

### Why you might see "admin" as empty:
- The main admin router (`tags=["admin"]`) has no endpoints defined directly on it
- All endpoints are in sub-routers with their own tags
- This results in an empty "admin" section in OpenAPI docs

## How to Consolidate (if desired)

### Option 1: Use Same Tag for All Admin Routes

Change all sub-routers to use the same `"admin"` tag:

**context.py:**
```python
router = APIRouter(prefix="/context", tags=["admin"])  # Same tag as parent
```

**tenants.py:**
```python
router = APIRouter(prefix="/tenants", tags=["admin"])  # Same tag as parent
```

**users.py:**
```python
router = APIRouter(prefix="/users", tags=["admin"])  # Same tag as parent
```

### Option 2: Remove Tags from Sub-Routers

Let sub-routers inherit the parent tag:

**context.py:**
```python
router = APIRouter(prefix="/context")  # No tags - will inherit from parent
```

**tenants.py:**
```python
router = APIRouter(prefix="/tenants")  # No tags - will inherit from parent
```

**users.py:**
```python
router = APIRouter(prefix="/users")  # No tags - will inherit from parent
```

## Recommendation

**✅ KEEP THE CURRENT STRUCTURE**

The separate tags provide better organization and are standard practice for complex APIs. The "duplicate" appearance is actually showing:

1. **admin** - The parent router (which may have no endpoints itself)
2. **admin-context** - Context switching operations  
3. **admin-tenants** - Tenant management operations
4. **admin-users** - User management operations

This is a **FEATURE**, not a bug!

## Summary

- **"admin"** and **"admin-context"** are **different OpenAPI tags**
- They organize **different sets of endpoints**
- Not the same API appearing twice
- Standard FastAPI/OpenAPI behavior for nested routers with tags
- Provides better documentation structure

If you want a single "admin" group, use Option 1 or 2 above to consolidate tags.

---

**Related Files:**
- `src/adapters/api/routers/admin/__init__.py` - Main admin router
- `src/adapters/api/routers/admin/context.py` - Context switching endpoints
- `src/adapters/api/routers/admin/tenants.py` - Tenant management endpoints
- `src/adapters/api/routers/admin/users.py` - User management endpoints
