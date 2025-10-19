# Data Model: Tenant Context Security Refactor

**Feature**: 004-tenant-security-refactor  
**Date**: 2025-10-19  
**Status**: Phase 1 Design

## Overview

This document defines the data structures, domain models, and state transitions for secure tenant context management. All models maintain hexagonal architecture principles (domain layer free of framework dependencies).

## Domain Models

### 1. TenantContext (Domain Entity)

**Purpose**: Immutable value object containing tenant-scoping information extracted from JWT claims.

**Location**: `src/domain/tenants/tenant_context.py`

```python
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

@dataclass(frozen=True)
class TenantContext:
    """
    Immutable tenant context extracted from authenticated JWT token.
    
    Constitutional Compliance:
    - Principle I: No FastAPI/Starlette imports (pure Python)
    - Principle III: Explicit tenant_id for all operations
    """
    
    tenant_id: UUID
    """Tenant identifier from JWT claims"""
    
    user_id: UUID
    """User identifier from JWT 'sub' claim"""
    
    roles: List[str]
    """User roles from JWT 'roles' claim (e.g., ['tenant_admin', 'user'])"""
    
    is_superadmin: bool
    """Derived from roles: True if 'superadmin' in roles"""
    
    session_tenant_id: Optional[UUID] = None
    """
    Active tenant for superadmin UI switching (from session).
    Overrides JWT tenant_id if present and user is superadmin.
    """
    
    @property
    def effective_tenant_id(self) -> UUID:
        """
        Returns the tenant_id to use for data filtering.
        
        Logic:
        - Superadmin: session_tenant_id if set, else tenant_id
        - Standard users: Always tenant_id (session ignored)
        """
        if self.is_superadmin and self.session_tenant_id:
            return self.session_tenant_id
        return self.tenant_id
    
    def can_access_tenant(self, requested_tenant_id: UUID) -> bool:
        """
        Determines if user can access resources in requested tenant.
        
        Authorization Rules:
        - Superadmin: Can access any tenant
        - Tenant Admin: Can access own tenant only
        - Other roles: Can access own tenant only
        """
        if self.is_superadmin:
            return True
        return self.tenant_id == requested_tenant_id
    
    def __str__(self) -> str:
        return f"TenantContext(tenant={self.tenant_id}, user={self.user_id}, roles={self.roles})"
```

**Validation Rules**:

- `tenant_id`: Must be valid UUID (non-null)
- `user_id`: Must be valid UUID (non-null)
- `roles`: Non-empty list of role strings
- `is_superadmin`: Derived from roles (not user-settable)
- `session_tenant_id`: Optional UUID (null for standard users)

### 2. TenantAccessPolicy (Policy Domain Model)

**Purpose**: Encapsulates authorization logic for tenant access decisions.

**Location**: `src/domain/tenants/policies.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AccessDecision(Enum):
    """Policy evaluation result"""
    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"

@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation with rationale for audit logging"""
    
    decision: AccessDecision
    """Final access decision"""
    
    reason: str
    """Human-readable explanation (for audit logs)"""
    
    rule_applied: str
    """Policy rule that produced decision (e.g., 'superadmin_global_access')"""
    
    tenant_id: UUID
    """Tenant context at time of evaluation"""
    
    user_id: UUID
    """User context at time of evaluation"""

class TenantAccessPolicy:
    """
    Domain service for evaluating tenant access policies.
    
    Constitutional Compliance:
    - Principle III: RBAC + Policy Engine (deny > allow precedence)
    - Principle VI: Auth logic reusable (no domain-specific rules here)
    """
    
    @staticmethod
    def evaluate_cross_tenant_access(
        tenant_ctx: TenantContext,
        requested_tenant_id: UUID
    ) -> PolicyEvaluationResult:
        """
        Evaluates if user can access requested tenant.
        
        Policy Rules:
        1. Superadmin: ALLOW (global access)
        2. Same tenant: ALLOW (user accesses own tenant)
        3. Different tenant: DENY (tenant isolation)
        """
        # Rule 1: Superadmin global access
        if tenant_ctx.is_superadmin:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                reason="Superadmin has global cross-tenant access",
                rule_applied="superadmin_global_access",
                tenant_id=requested_tenant_id,
                user_id=tenant_ctx.user_id
            )
        
        # Rule 2: Same tenant access
        if tenant_ctx.tenant_id == requested_tenant_id:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                reason="User accessing own tenant",
                rule_applied="same_tenant_access",
                tenant_id=requested_tenant_id,
                user_id=tenant_ctx.user_id
            )
        
        # Rule 3: Cross-tenant denial
        return PolicyEvaluationResult(
            decision=AccessDecision.DENY,
            reason=f"User tenant_id {tenant_ctx.tenant_id} != requested tenant_id {requested_tenant_id}",
            rule_applied="cross_tenant_isolation",
            tenant_id=requested_tenant_id,
            user_id=tenant_ctx.user_id
        )
    
    @staticmethod
    def evaluate_admin_route_access(
        tenant_ctx: TenantContext
    ) -> PolicyEvaluationResult:
        """
        Evaluates if user can access /api/v1/admin/* routes.
        
        Policy Rules:
        1. Superadmin: ALLOW (platform administration)
        2. Tenant Admin: ALLOW (tenant-scoped admin operations)
        3. Other roles: DENY (no admin access)
        """
        if tenant_ctx.is_superadmin:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                reason="Superadmin can access platform admin routes",
                rule_applied="superadmin_admin_access",
                tenant_id=tenant_ctx.tenant_id,
                user_id=tenant_ctx.user_id
            )
        
        if "tenant_admin" in tenant_ctx.roles:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                reason="Tenant admin can access tenant-scoped admin routes",
                rule_applied="tenant_admin_access",
                tenant_id=tenant_ctx.tenant_id,
                user_id=tenant_ctx.user_id
            )
        
        return PolicyEvaluationResult(
            decision=AccessDecision.DENY,
            reason=f"User roles {tenant_ctx.roles} do not include admin permissions",
            rule_applied="admin_role_required",
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id
        )
```

## Adapter Models (FastAPI Layer)

### 3. SessionTenantContext (Adapter Model)

**Purpose**: Session storage for superadmin tenant switching.

**Location**: `src/adapters/api/models/session.py`

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class SessionTenantContext(BaseModel):
    """
    Session-stored tenant context for superadmin UI.
    
    Storage: Redis or encrypted cookie (configurable)
    Lifetime: Session duration (cleared on logout)
    """
    
    active_tenant_id: UUID = Field(
        ...,
        description="Tenant ID selected by superadmin for current session"
    )
    
    switched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when tenant was switched"
    )
    
    previous_tenant_id: UUID | None = Field(
        None,
        description="Previous active tenant (for audit trail)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "active_tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "switched_at": "2025-10-19T12:34:56Z",
                "previous_tenant_id": "987e6543-e21b-43d2-c654-426614174999"
            }
        }
```

### 4. TenantSwitchRequest (API Request Model)

**Purpose**: Request body for superadmin tenant switching endpoint.

**Location**: `src/adapters/api/schemas/tenant_context.py`

```python
from pydantic import BaseModel, Field, validator
from uuid import UUID

class TenantSwitchRequest(BaseModel):
    """
    POST /api/v1/admin/context/tenant request body.
    
    Validation:
    - tenant_id must be valid UUID
    - Tenant must exist (validated in endpoint)
    """
    
    tenant_id: UUID = Field(
        ...,
        description="Target tenant ID to switch to"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }

class TenantSwitchResponse(BaseModel):
    """
    POST /api/v1/admin/context/tenant response body.
    """
    
    active_tenant_id: UUID = Field(
        ...,
        description="Currently active tenant ID"
    )
    
    tenant_name: str = Field(
        ...,
        description="Human-readable tenant name"
    )
    
    switched_at: datetime = Field(
        ...,
        description="Timestamp of tenant switch"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "active_tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_name": "Acme Corp",
                "switched_at": "2025-10-19T12:34:56Z"
            }
        }
```

## State Transitions

### 1. Tenant Context Extraction Flow

```
┌─────────────────────────────────────────────────────────────┐
│ HTTP Request                                                │
│ Authorization: Bearer <jwt>                                  │
│ [Session-ID: <cookie>]                                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ AuthenticationMiddleware (EXISTING)                          │
│ - Validates JWT signature                                    │
│ - Verifies expiration                                        │
│ - Sets request.state.user                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ TenantContextMiddleware (NEW)                                │
│ 1. Extract JWT claims: tenant_id, user_id, roles            │
│ 2. Check session for active_tenant_id (superadmin only)     │
│ 3. Create TenantContext(                                     │
│      tenant_id=jwt.tenant_id,                                │
│      session_tenant_id=session.active_tenant_id OR None      │
│    )                                                          │
│ 4. Set request.state.tenant_context                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ AuthorizationMiddleware (NEW)                                │
│ 1. Extract requested tenant_id from path params             │
│ 2. Evaluate TenantAccessPolicy                              │
│ 3. If DENY: raise HTTPException(403)                        │
│ 4. If ALLOW: Log audit event + continue                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Endpoint Handler                                             │
│ - Access request.state.tenant_context.effective_tenant_id   │
│ - Pass to repository layer                                   │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP Response                                                │
└─────────────────────────────────────────────────────────────┘
```

### 2. Superadmin Tenant Switching Flow

```
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/admin/context/tenant                            │
│ Body: {"tenant_id": "target-tenant-uuid"}                    │
│ Authorization: Bearer <superadmin-jwt>                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Middleware Stack (auth + tenant context)                     │
│ - Validates JWT                                              │
│ - Extracts superadmin tenant context                         │
│ - Authorizes: is_superadmin == True                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Endpoint: switch_tenant()                                    │
│ 1. Validate target tenant exists (DB query)                 │
│ 2. Update session: active_tenant_id = target_tenant_id      │
│ 3. Log audit event: auth.tenant_switch                      │
│ 4. Return TenantSwitchResponse                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Subsequent Requests (same session)                           │
│ - TenantContextMiddleware reads session.active_tenant_id    │
│ - Sets tenant_ctx.session_tenant_id                          │
│ - effective_tenant_id returns session tenant                 │
└─────────────────────────────────────────────────────────────┘
```

### 3. Logout / Session Termination

```
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/auth/logout                                     │
│ Authorization: Bearer <jwt>                                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Logout Endpoint                                              │
│ 1. Invalidate JWT (add to blocklist)                        │
│ 2. Clear session: session.clear()                           │
│    - Removes active_tenant_id                                │
│    - Removes all session data                                │
│ 3. Log audit event: auth.logout                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Next Request (new login required)                            │
│ - No JWT: 401 Unauthorized                                   │
│ - No session: Fresh tenant context from new JWT              │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

**No Database Changes Required** ✅

This refactor uses existing schema:

- `users.tenant_id` (UUID, NOT NULL) - Already exists
- `tenants.id` (UUID, PRIMARY KEY) - Already exists
- JWT tokens already contain `tenant_id` claim

Session storage (Redis or encrypted cookies) is ephemeral - no persistent schema.

## Validation Rules

### TenantContext Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| `tenant_id` | Must be valid UUID | "Invalid tenant_id format" |
| `tenant_id` | Must not be null | "tenant_id is required" |
| `user_id` | Must be valid UUID | "Invalid user_id format" |
| `user_id` | Must not be null | "user_id is required" |
| `roles` | Must be non-empty list | "User must have at least one role" |
| `session_tenant_id` | If set, must be valid UUID | "Invalid session_tenant_id format" |

### Authorization Validation

| Scenario | Validation Rule | HTTP Status |
|----------|----------------|-------------|
| Standard user accesses own tenant | `tenant_ctx.tenant_id == requested_tenant_id` | 200 OK |
| Standard user accesses other tenant | Cross-tenant isolation | 403 Forbidden |
| Superadmin accesses any tenant | Always allow | 200 OK |
| Non-admin accesses /admin routes | Admin role required | 403 Forbidden |
| Tenant admin accesses other tenant /admin | Tenant isolation | 403 Forbidden |

## Audit Event Schema

All tenant context events logged in structured format:

```python
{
  "category": "security.tenant_context",  # or "auth.tenant_switch", "auth.cross_tenant.denied"
  "timestamp": "2025-10-19T12:34:56.789Z",
  "correlation_id": "req-123e4567",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "roles": ["tenant_admin", "user"],
  "endpoint": "/api/v1/tenants/other-tenant/users",
  "requested_tenant_id": "other-tenant-uuid",
  "authorized": false,
  "reason": "User tenant_id mismatch (not superadmin)",
  "policy_rule": "cross_tenant_isolation",
  "session_tenant_id": null
}
```

## Error Handling

### 403 Forbidden (Tenant Isolation Violation)

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Access denied: Cannot access resources in tenant 'other-tenant-uuid'",
    "details": {
      "user_tenant_id": "user-tenant-uuid",
      "requested_tenant_id": "other-tenant-uuid",
      "required_role": "superadmin"
    },
    "docs_url": "https://docs.githubspeckit.com/errors/tenant-isolation"
  },
  "trace_id": "req-123e4567"
}
```

### 400 Bad Request (Deprecated Query Parameter)

```json
{
  "error": {
    "code": "DEPRECATED_PARAMETER",
    "message": "Query parameter '?tenant_id=' is deprecated and will be removed on 2025-11-19",
    "details": {
      "parameter": "tenant_id",
      "sunset_date": "2025-11-19T00:00:00Z",
      "migration_guide": "https://docs.githubspeckit.com/migration/tenant-security"
    }
  },
  "trace_id": "req-123e4567"
}
```

## Performance Characteristics

| Operation | Latency (p95) | Notes |
|-----------|--------------|-------|
| JWT claim extraction | <3ms | In-memory parsing |
| Session read (Redis) | <5ms | Single key lookup |
| Session read (Cookie) | <1ms | Decrypt + deserialize |
| Policy evaluation | <1ms | Pure function (no I/O) |
| Total middleware overhead | <5ms | Meets performance budget ✅ |

---

**Data Model Complete**: All domain entities, policies, and state transitions defined.  
**Next**: Generate OpenAPI contracts (Phase 1 continuation)
