"""Pydantic schemas for user profile API endpoints.

Defines request/response models for profile management.
"""
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile (PUT /api/v1/users/{user_id}/profile)."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate full_name: max 100 characters."""
        if v is not None:
            # Convert empty string to None
            if v == "":
                return None
            if len(v) > 100:
                raise ValueError("full_name must not exceed 100 characters")
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone: 7-20 characters (flexible format)."""
        if v is not None:
            # Convert empty string to None
            if v == "":
                return None
            if len(v) < 7:
                raise ValueError("phone must be at least 7 characters")
            if len(v) > 20:
                raise ValueError("phone must not exceed 20 characters")
        return v
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address: max 500 characters."""
        if v is not None:
            # Convert empty string to None
            if v == "":
                return None
            if len(v) > 500:
                raise ValueError("address must not exceed 500 characters")
        return v


class UserProfileResponse(BaseModel):
    """Response model for user profile (GET /api/v1/users/{user_id}/profile)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_display_url: Optional[str] = None
    photo_thumbnail_url: Optional[str] = None
    photo_avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PhotoUploadResponse(BaseModel):
    """Response model for photo upload (POST /api/v1/users/{user_id}/profile/photo)."""
    
    status: str = "processing"
    message: str = "Photo upload accepted and processing in background"
