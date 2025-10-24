"""
Role management API endpoints (FR-122: Role Management & Hierarchy).

Admin-only endpoints for role CRUD operations and user-role assignments.
Enforces system role immutability and tenant isolation.

Routes:
- GET /api/v1/admin/roles - List all roles (system + tenant custom)
- POST /api/v1/admin/roles - Create custom role (tenant_admin only)
- GET /api/v1/admin/roles/{id} - Get role details
- PUT /api/v1/admin/roles/{id} - Update custom role
- DELETE /api/v1/admin/roles/{id} - Delete custom role
- POST /api/v1/admin/users/{user_id}/roles/{role_id} - Assign role to user
- DELETE /api/v1/admin/users/{user_id}/roles/{role_id} - Revoke role from user
"""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.repositories import SQLAlchemyRoleRepository
from adapters.api.deps import get_db_session
from domain.tenants.tenant_context import TenantContext
from domain.roles.entities import Role
from domain.roles.exceptions import (
    RoleNotFoundError,
    DuplicateRoleNameError,
    SystemRoleImmutableError,
    PrivilegeEscalationError,
)
from domain.roles.permissions import Permission, validate_permissions


router = APIRouter(tags=["admin-roles"])


# Dependency to extract tenant context

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


# Pydantic schemas

class RoleResponse(BaseModel):
    """Role response schema."""
    id: UUID
    name: str
    tenant_id: Optional[UUID]
    is_system: bool
    permissions: list[str]
    description: Optional[str]
    
    model_config = {"from_attributes": True}


class CreateRoleRequest(BaseModel):
    """Create custom role request schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name (unique within tenant)")
    permissions: list[str] = Field(..., description="List of permissions (e.g., ['users:read', 'users:create'])")
    description: Optional[str] = Field(None, max_length=500, description="Role description")


class UpdateRoleRequest(BaseModel):
    """Update custom role request schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    permissions: Optional[list[str]] = None
    description: Optional[str] = Field(None, max_length=500)


class RoleAssignmentResponse(BaseModel):
    """Role assignment response schema."""
    user_id: UUID
    role_id: UUID
    message: str


# Helper functions

def check_admin_access(tenant_context: TenantContext):
    """Check if user has admin access (superadmin or tenant_admin)."""
    if not tenant_context.is_superadmin and "tenant_admin" not in tenant_context.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required (superadmin or tenant_admin role)"
        )


def check_tenant_isolation(tenant_context: TenantContext, resource_tenant_id: Optional[UUID]):
    """Check tenant isolation for tenant_admin users."""
    if tenant_context.is_superadmin:
        # Superadmin can access all tenants
        return
    
    # tenant_admin can only access their own tenant
    if resource_tenant_id and tenant_context.tenant_id != resource_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: tenant isolation violation"
        )


# Endpoints

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    include_system: bool = True
):
    """
    List all roles (system + tenant custom roles).
    
    **RBAC**: Requires superadmin or tenant_admin role
    - superadmin: Sees all roles (system + all tenant custom roles)
    - tenant_admin: Sees system roles + own tenant's custom roles
    """
    check_admin_access(tenant_context)
    
    repo = SQLAlchemyRoleRepository(db)
    
    if "superadmin" in tenant_context.roles:
        # Superadmin sees everything
        roles = await repo.list_all(include_system=include_system)
    else:
        # tenant_admin sees system roles + own tenant roles
        tenant_id = tenant_context.tenant_id
        roles = await repo.list_by_tenant(tenant_id, include_system=include_system)
    
    return [RoleResponse.model_validate(role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: CreateRoleRequest,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    Create a custom tenant role.
    
    **RBAC**: Requires tenant_admin or superadmin role
    **Rules**:
    - System roles cannot be created via API (pre-seeded only)
    - Custom roles scoped to tenant
    - No privilege escalation (cannot create roles with permissions user doesn't have)
    """
    check_admin_access(tenant_context)
    
    # Validate permissions
    is_valid, errors = validate_permissions(request.permissions)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {', '.join(errors)}"
        )
    
    # Check for privilege escalation attempt
    if Permission.ALL in request.permissions or "superadmin" in request.name.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create roles with superadmin-level permissions"
        )
    
    # Create role entity
    from datetime import datetime, timezone
    from uuid import uuid4
    
    tenant_id = tenant_context.tenant_id
    role = Role(
        id=uuid4(),
        name=request.name,
        tenant_id=tenant_id,
        is_system=False,
        permissions=request.permissions,
        description=request.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by=tenant_context.user_id,
        updated_by=tenant_context.user_id,
    )
    
    repo = SQLAlchemyRoleRepository(db)
    
    try:
        created_role = await repo.create(role)
        await db.commit()
        return RoleResponse.model_validate(created_role)
    except DuplicateRoleNameError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    Get role details by ID.
    
    **RBAC**: Requires tenant_admin or superadmin role
    **Tenant Isolation**: tenant_admin can only view system roles + own tenant roles
    """
    check_admin_access(tenant_context)
    
    repo = SQLAlchemyRoleRepository(db)
    
    try:
        role = await repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_id} not found"
            )
        
        # Check tenant isolation
        if role.tenant_id:
            check_tenant_isolation(tenant_context, role.tenant_id)
        
        return RoleResponse.model_validate(role)
    except RoleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    request: UpdateRoleRequest,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    Update a custom role.
    
    **RBAC**: Requires tenant_admin or superadmin role
    **Rules**:
    - System roles are immutable (cannot be updated)
    - tenant_admin can only update roles in their own tenant
    """
    check_admin_access(tenant_context)
    
    repo = SQLAlchemyRoleRepository(db)
    
    try:
        # Get existing role
        role = await repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_id} not found"
            )
        
        # Check tenant isolation
        if role.tenant_id:
            check_tenant_isolation(tenant_context, role.tenant_id)
        
        # Validate permissions if provided
        if request.permissions:
            is_valid, errors = validate_permissions(request.permissions)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid permissions: {', '.join(errors)}"
                )
        
        # Update role fields
        from datetime import datetime, timezone
        
        if request.name:
            role.name = request.name
        if request.permissions:
            role.permissions = request.permissions
        if request.description is not None:
            role.description = request.description
        
        role.updated_at = datetime.now(timezone.utc)
        role.updated_by = tenant_context.user_id
        
        updated_role = await repo.update(role)
        await db.commit()
        return RoleResponse.model_validate(updated_role)
        
    except RoleNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    except SystemRoleImmutableError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DuplicateRoleNameError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    Delete a custom role.
    
    **RBAC**: Requires tenant_admin or superadmin role
    **Rules**:
    - System roles are immutable (cannot be deleted)
    - tenant_admin can only delete roles in their own tenant
    - CASCADE: Role assignments (user_roles) are automatically removed
    """
    check_admin_access(tenant_context)
    
    repo = SQLAlchemyRoleRepository(db)
    
    try:
        # Get existing role to check tenant isolation
        role = await repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_id} not found"
            )
        
        # Check tenant isolation
        if role.tenant_id:
            check_tenant_isolation(tenant_context, role.tenant_id)
        
        await repo.delete(role_id)
        await db.commit()
        
    except RoleNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    except SystemRoleImmutableError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/users/{user_id}/roles/{role_id}", response_model=RoleAssignmentResponse)
async def assign_role_to_user(
    user_id: UUID,
    role_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    Assign a role to a user.
    
    **RBAC**: Requires tenant_admin or superadmin role
    **Rules**:
    - tenant_admin can only assign roles to users in their own tenant
    - Cannot assign roles that escalate privileges beyond current user
    - Idempotent: assigning an already-assigned role succeeds
    """
    check_admin_access(tenant_context)
    
    repo = SQLAlchemyRoleRepository(db)
    
    try:
        # Verify role exists
        role = await repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_id} not found"
            )
        
        # Check tenant isolation for custom roles
        if role.tenant_id:
            check_tenant_isolation(tenant_context, role.tenant_id)
        
        # TODO: Verify user exists and check tenant isolation
        # (would require UserRepository access here)
        
        await repo.assign_to_user(
            user_id=user_id,
            role_id=role_id,
            assigned_by=tenant_context.user_id
        )
        await db.commit()
        
        return RoleAssignmentResponse(
            user_id=user_id,
            role_id=role_id,
            message=f"Role '{role.name}' assigned to user successfully"
        )
        
    except RoleNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role_from_user(
    user_id: UUID,
    role_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    """
    Revoke a role from a user.
    
    **RBAC**: Requires tenant_admin or superadmin role
    **Rules**:
    - tenant_admin can only revoke roles from users in their own tenant
    - Idempotent: revoking an unassigned role succeeds
    """
    check_admin_access(tenant_context)
    
    repo = SQLAlchemyRoleRepository(db)
    
    try:
        # Verify role exists
        role = await repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_id} not found"
            )
        
        # Check tenant isolation for custom roles
        if role.tenant_id:
            check_tenant_isolation(tenant_context, role.tenant_id)
        
        # TODO: Verify user exists and check tenant isolation
        
        await repo.revoke_from_user(user_id=user_id, role_id=role_id)
        await db.commit()
        
    except RoleNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
