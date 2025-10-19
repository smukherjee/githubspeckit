"""
Session storage models for tenant context.

Pydantic models for Redis/cookie-based session management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SessionTenantContext(BaseModel):
    """
    Tenant context stored in session (Redis or encrypted cookie).
    
    Used for superadmin tenant switching - stores the active tenant
    the user has switched to (overrides JWT tenant_id).
    """
    
    active_tenant_id: UUID = Field(
        description="The tenant ID the user has switched to"
    )
    switched_at: datetime = Field(
        description="Timestamp when the switch occurred"
    )
    previous_tenant_id: Optional[UUID] = Field(
        default=None,
        description="The original JWT tenant_id before switching"
    )
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class TenantSwitchRequest(BaseModel):
    """Request to switch active tenant (superadmin only)."""
    
    target_tenant_id: UUID = Field(
        description="The tenant ID to switch to",
        alias="tenant_id"
    )
    
    class Config:
        populate_by_name = True


class TenantSwitchResponse(BaseModel):
    """Response after successful tenant switch."""
    
    active_tenant_id: UUID = Field(
        description="The tenant ID now active in the session"
    )
    tenant_name: Optional[str] = Field(
        default=None,
        description="Display name of the tenant (if available)"
    )
    switched_at: datetime = Field(
        description="Timestamp when the switch occurred"
    )
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
