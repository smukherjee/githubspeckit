"""
Tenant-scoped policy management routes (V1.0).

**Route Tier**: TENANT-SCOPED (/api/v1/tenants/{tenant_id}/policies)
**Authorization**: Path tenant_id validated by AuthorizationMiddleware

Implements policy management operations scoped to a specific tenant.

**Authorization Flow**:
1. TenantContextMiddleware extracts JWT tenant_id → request.state.tenant_context
2. AuthorizationMiddleware evaluates: Can user access path tenant_id?
3. If DENY: 403 with X-Tenant-Isolation-Policy header
4. If ALLOW: Request proceeds to endpoint

Status: Phase 3.4 - T032 (Tenant-scoped policies endpoint)
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyPolicyRepository
from domain.tenants.tenant_context import TenantContext
from domain.policy.models import PolicyStatus

router = APIRouter(prefix="/{tenant_id}/policies", tags=["tenant-scoped-policies"])


class PolicyResponse(BaseModel):
    """Policy response model (tenant-scoped)."""
    id: str  # React-Admin requires 'id' field
    policy_id: str
    tenant_id: str
    version: int
    resource_type: str
    condition_expression: str
    effect: str  # ALLOW or DENY
    status: str
    created_at: str | None = None
    model_config = ConfigDict()


def get_tenant_context(request: Request) -> TenantContext:
    """Extract tenant context from request state (injected by middleware)."""
    if not hasattr(request.state, "tenant_context"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TENANT_CONTEXT_MISSING",
                    "message": "Tenant context not initialized (middleware not wired)",
                }
            },
        )
    return request.state.tenant_context


@router.get(
    "",
    response_model=List[PolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="List policies in specific tenant",
    description="""
    Retrieves all policies belonging to the specified tenant.
    
    **Authorization**:
    - Superadmin: Can access any tenant
    - Tenant Admin: Can access own tenant only (tenant_id == JWT tenant_id)
    - Other roles: 403 Forbidden
    
    **V1.0 API**: Tenant-scoped policy listing via path parameter.
    """,
)
async def list_tenant_policies(
    tenant_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
) -> List[PolicyResponse]:
    """
    List policies in specific tenant (tenant-scoped).
    
    Args:
        tenant_id: Target tenant UUID (from path parameter)
        tenant_context: Current tenant context from middleware
        db: Database session
        page: Page number for pagination
        per_page: Items per page
    
    Returns:
        List of PolicyResponse objects
    
    Raises:
        HTTPException 403: If user cannot access this tenant
        HTTPException 500: If database error occurs
    """
    try:
        repo = SQLAlchemyPolicyRepository(db)
        
        # Query policies for the tenant
        # Note: Authorization middleware already validated tenant access
        policies = await repo.list_by_tenant(tenant_id=str(tenant_id))
        
        # Convert to response models
        response_policies = [
            PolicyResponse(
                id=policy.policy_id,  # React-Admin compatibility
                policy_id=policy.policy_id,
                tenant_id=str(tenant_id),
                version=policy.version,
                resource_type=policy.resource_type,
                condition_expression=policy.condition_expression,
                effect=policy.effect,
                status=policy.status.value if hasattr(policy, 'status') else 'active',
                created_at=policy.created_at.isoformat() if policy.created_at else None,
            )
            for policy in policies
        ]
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return response_policies[start_idx:end_idx]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "POLICY_LIST_ERROR",
                    "message": f"Failed to list policies: {str(e)}",
                }
            },
        )
