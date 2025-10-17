# Data Model: User Profile Details

**Feature**: User Profile Details with Photo Upload  
**Date**: 2025-10-17  
**Status**: Design Complete

## Overview

This document defines the database schema and domain models for storing optional user profile information (name, phone, address, profile photos) with WhatsApp-style photo optimization.

## Database Schema

### New Table: `user_details`

Stores optional profile information linked one-to-one with `users` table.

```sql
CREATE TABLE user_details (
    user_id UUID PRIMARY KEY,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,  -- Max 500 chars enforced in application
    photo_display_url VARCHAR(512),    -- 640x640px variant
    photo_thumbnail_url VARCHAR(512),  -- 96x96px variant
    photo_avatar_url VARCHAR(512),     -- 48x48px variant
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    
    CONSTRAINT fk_user_details_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_details_created_by FOREIGN KEY (created_by)
        REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_user_details_updated_by FOREIGN KEY (updated_by)
        REFERENCES users(user_id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX ix_user_details_created_at ON user_details(created_at);
CREATE INDEX ix_user_details_updated_at ON user_details(updated_at);

-- Comments
COMMENT ON TABLE user_details IS 'Optional user profile information (name, phone, address, photo)';
COMMENT ON COLUMN user_details.full_name IS 'Display name (max 100 chars)';
COMMENT ON COLUMN user_details.phone IS 'Phone number, international format accepted (max 20 chars)';
COMMENT ON COLUMN user_details.address IS 'Multi-line address, unstructured (max 500 chars app-enforced)';
COMMENT ON COLUMN user_details.photo_display_url IS 'Profile photo URL (640x640px, ~200KB JPEG)';
COMMENT ON COLUMN user_details.photo_thumbnail_url IS 'Thumbnail URL (96x96px, ~15KB JPEG)';
COMMENT ON COLUMN user_details.photo_avatar_url IS 'Small avatar URL (48x48px, ~5KB JPEG)';
```

### Existing Table: `users` (No Changes)

User details links to existing `users` table via `user_id` foreign key.

```sql
-- Existing schema (for reference)
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    status user_status NOT NULL DEFAULT 'invited',
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    
    CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    CONSTRAINT uk_users_tenant_email UNIQUE (tenant_id, email)
);
```

**Tenant Isolation**: `user_details` inherits tenant scoping from `users` table via JOIN:

```sql
-- All queries must join with users to enforce tenant_id filtering
SELECT ud.* FROM user_details ud
INNER JOIN users u ON ud.user_id = u.user_id
WHERE u.tenant_id = :current_tenant_id;
```

## Domain Models

### Python Dataclasses (Domain Layer)

**UserDetails Entity**:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class UserDetails:
    """
    User profile details (optional personal information).
    
    All fields except user_id are optional (nullable in DB).
    Photo URLs point to processed variants (display, thumbnail, avatar).
    Tenant isolation inherited from linked User entity.
    """
    user_id: str  # FK to users.user_id
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_display_url: Optional[str] = None    # 640x640px
    photo_thumbnail_url: Optional[str] = None  # 96x96px
    photo_avatar_url: Optional[str] = None     # 48x48px
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    def has_photo(self) -> bool:
        """Check if user has uploaded a photo."""
        return self.photo_display_url is not None
    
    def get_avatar_url(self, size: str = 'display') -> Optional[str]:
        """
        Get photo URL for specified size.
        
        Args:
            size: 'display' (640px), 'thumbnail' (96px), or 'avatar' (48px)
        
        Returns:
            Photo URL or None if no photo uploaded
        """
        if size == 'display':
            return self.photo_display_url
        elif size == 'thumbnail':
            return self.photo_thumbnail_url
        elif size == 'avatar':
            return self.photo_avatar_url
        else:
            raise ValueError(f"Invalid size: {size}")
```

### SQLAlchemy Model (Adapter Layer)

**UserDetailsModel** (maps to `user_details` table):

```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from adapters.persistence.base import Base

class UserDetailsModel(Base):
    """SQLAlchemy model for user_details table."""
    __tablename__ = 'user_details'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    photo_display_url = Column(String(512), nullable=True)
    photo_thumbnail_url = Column(String(512), nullable=True)
    photo_avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    user = relationship('UserModel', foreign_keys=[user_id], back_populates='details')
    created_by_user = relationship('UserModel', foreign_keys=[created_by])
    updated_by_user = relationship('UserModel', foreign_keys=[updated_by])
```

**UserModel Extension** (add relationship to `users` table):

```python
# In existing UserModel class
class UserModel(Base):
    __tablename__ = 'users'
    # ... existing columns ...
    
    # NEW: Add relationship to user_details
    details = relationship('UserDetailsModel', uselist=False, back_populates='user', cascade='all, delete-orphan')
```

## Pydantic Schemas (API Layer)

### Request/Response Models

**UserDetailsResponse** (GET endpoint response):

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserDetailsResponse(BaseModel):
    """User profile details response."""
    user_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_display_url: Optional[str] = None
    photo_thumbnail_url: Optional[str] = None
    photo_avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {'from_attributes': True}  # Enable from_orm
```

**UserDetailsUpdateRequest** (PUT endpoint request):

```python
from pydantic import BaseModel, field_validator
from typing import Optional

class UserDetailsUpdateRequest(BaseModel):
    """User profile details update request."""
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) == 0:
            raise ValueError("Full name cannot be empty string")
        return v.strip() if v else None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        # Basic validation: 7-20 chars, mostly digits
        if len(v) < 7 or len(v) > 20:
            raise ValueError("Phone must be 7-20 characters")
        digit_count = sum(c.isdigit() for c in v)
        if digit_count < 7:
            raise ValueError("Phone must contain at least 7 digits")
        return v
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 500:
            raise ValueError("Address must not exceed 500 characters")
        return v
```

**PhotoUploadResponse** (POST photo endpoint response):

```python
class PhotoUploadResponse(BaseModel):
    """Photo upload response (async processing)."""
    message: str = "Photo upload started"
    status: str = "processing"  # or "complete"
    photo_display_url: Optional[str] = None    # Available when status=complete
    photo_thumbnail_url: Optional[str] = None
    photo_avatar_url: Optional[str] = None
```

## Repository Interface (Domain Layer)

**UserDetailsRepository** (abstract interface):

```python
from abc import ABC, abstractmethod
from typing import Optional
from domain.users.models import UserDetails

class UserDetailsRepository(ABC):
    """Repository interface for user profile details."""
    
    @abstractmethod
    async def get(self, user_id: str) -> Optional[UserDetails]:
        """Retrieve profile details for a user."""
        pass
    
    @abstractmethod
    async def upsert(self, details: UserDetails) -> UserDetails:
        """Create or update profile details."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """Delete profile details (cascade from user deletion)."""
        pass
    
    @abstractmethod
    async def delete_photo(self, user_id: str) -> None:
        """Remove photo URLs from profile."""
        pass
```

**SQLAlchemy Implementation** (adapter layer):

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from adapters.persistence.models import UserDetailsModel
from domain.users.models import UserDetails

class SQLAlchemyUserDetailsRepository(UserDetailsRepository):
    """SQLAlchemy implementation of UserDetailsRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get(self, user_id: str) -> Optional[UserDetails]:
        """Get profile details."""
        result = await self.session.execute(
            select(UserDetailsModel).where(UserDetailsModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
    
    async def upsert(self, details: UserDetails) -> UserDetails:
        """Create or update profile."""
        model = await self.session.get(UserDetailsModel, details.user_id)
        if model:
            # Update existing
            model.full_name = details.full_name
            model.phone = details.phone
            model.address = details.address
            model.photo_display_url = details.photo_display_url
            model.photo_thumbnail_url = details.photo_thumbnail_url
            model.photo_avatar_url = details.photo_avatar_url
            model.updated_at = details.updated_at
            model.updated_by = details.updated_by
        else:
            # Create new
            model = UserDetailsModel(**self._to_dict(details))
            self.session.add(model)
        
        await self.session.flush()
        return self._to_domain(model)
    
    async def delete(self, user_id: str) -> None:
        """Delete profile (or cascade from user deletion)."""
        model = await self.session.get(UserDetailsModel, user_id)
        if model:
            await self.session.delete(model)
    
    async def delete_photo(self, user_id: str) -> None:
        """Remove photo URLs."""
        await self.session.execute(
            update(UserDetailsModel)
            .where(UserDetailsModel.user_id == user_id)
            .values(
                photo_display_url=None,
                photo_thumbnail_url=None,
                photo_avatar_url=None
            )
        )
    
    @staticmethod
    def _to_domain(model: UserDetailsModel) -> UserDetails:
        """Convert SQLAlchemy model to domain entity."""
        return UserDetails(
            user_id=str(model.user_id),
            full_name=model.full_name,
            phone=model.phone,
            address=model.address,
            photo_display_url=model.photo_display_url,
            photo_thumbnail_url=model.photo_thumbnail_url,
            photo_avatar_url=model.photo_avatar_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=str(model.created_by) if model.created_by else None,
            updated_by=str(model.updated_by) if model.updated_by else None,
        )
    
    @staticmethod
    def _to_dict(details: UserDetails) -> dict:
        """Convert domain entity to dict for SQLAlchemy."""
        return {
            'user_id': details.user_id,
            'full_name': details.full_name,
            'phone': details.phone,
            'address': details.address,
            'photo_display_url': details.photo_display_url,
            'photo_thumbnail_url': details.photo_thumbnail_url,
            'photo_avatar_url': details.photo_avatar_url,
            'created_at': details.created_at,
            'updated_at': details.updated_at,
            'created_by': details.created_by,
            'updated_by': details.updated_by,
        }
```

## Entity Relationships

```text
tenants (1) ──── (N) users (1) ──── (1) user_details
                      │
                      └── created_by, updated_by ──> users (self-reference)
```

**Cascade Behavior**:

- DELETE user → CASCADE delete user_details
- DELETE tenant → CASCADE delete users → CASCADE delete user_details
- UPDATE user_details.created_by/updated_by ON DELETE → SET NULL

## Validation Rules

### Field Constraints

| Field | Type | Max Length | Nullable | Validation |
|-------|------|------------|----------|------------|
| user_id | UUID | - | ❌ No | Must exist in users table |
| full_name | String | 100 chars | ✅ Yes | Trim whitespace, non-empty after trim |
| phone | String | 20 chars | ✅ Yes | 7-20 chars, ≥7 digits |
| address | Text | 500 chars | ✅ Yes | App-enforced limit |
| photo_display_url | String | 512 chars | ✅ Yes | Valid URL format |
| photo_thumbnail_url | String | 512 chars | ✅ Yes | Valid URL format |
| photo_avatar_url | String | 512 chars | ✅ Yes | Valid URL format |
| created_at | Timestamp | - | ❌ No | Auto-set on insert |
| updated_at | Timestamp | - | ❌ No | Auto-update on modify |
| created_by | UUID | - | ✅ Yes | Must exist in users table if not null |
| updated_by | UUID | - | ✅ Yes | Must exist in users table if not null |

### Business Rules

1. **Optional Fields**: All profile fields (name, phone, address, photo) are optional
2. **Partial Updates**: Users can update any subset of fields
3. **Photo Atomic**: All 3 photo URLs updated together (display, thumbnail, avatar)
4. **No Empty Strings**: Empty strings converted to NULL (normalize representation)
5. **Phone Format**: Flexible acceptance, but must contain ≥7 digits
6. **Address Multi-line**: Supports line breaks, various formats (no rigid parsing)

## State Transitions

User details has no state machine (stateless CRUD). Photo upload follows async workflow:

```text
1. Upload request (POST /photo) → 202 Accepted
2. Background processing → Resize, compress, store
3. Database update → Set photo URLs
4. Status: processing → complete
```

## Indexes & Performance

### Required Indexes

```sql
-- Primary key (automatic)
PRIMARY KEY (user_id)

-- Audit trail queries
CREATE INDEX ix_user_details_created_at ON user_details(created_at);
CREATE INDEX ix_user_details_updated_at ON user_details(updated_at);
```

### Tenant Isolation Query Pattern

```sql
-- Always join with users to enforce tenant_id
SELECT ud.* 
FROM user_details ud
INNER JOIN users u ON ud.user_id = u.user_id
WHERE u.tenant_id = :tenant_id AND u.user_id = :user_id;
```

**No direct index on tenant_id needed** in user_details table since it's always accessed via JOIN with users (which already has indexed tenant_id).

## Migration Script

**Alembic Migration** (pseudo-code):

```python
# alembic/versions/20251017_1030_add_user_details_table.py
def upgrade() -> None:
    op.create_table(
        'user_details',
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('photo_display_url', sa.String(512), nullable=True),
        sa.Column('photo_thumbnail_url', sa.String(512), nullable=True),
        sa.Column('photo_avatar_url', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('user_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.user_id'], ondelete='SET NULL'),
    )
    op.create_index('ix_user_details_created_at', 'user_details', ['created_at'])
    op.create_index('ix_user_details_updated_at', 'user_details', ['updated_at'])

def downgrade() -> None:
    op.drop_index('ix_user_details_updated_at')
    op.drop_index('ix_user_details_created_at')
    op.drop_table('user_details')
```

## Summary

- **Table**: `user_details` with 1:1 relationship to `users`
- **Fields**: All optional (name, phone, address, 3 photo URLs)
- **Tenant Isolation**: Inherited via JOIN with users table (no direct tenant_id column)
- **Audit Trail**: created_at, updated_at, created_by, updated_by
- **Photo Storage**: 3 URLs (display 640px, thumbnail 96px, avatar 48px)
- **Cascade**: DELETE user → DELETE user_details automatically
- **Validation**: Pydantic at API layer, app-enforced constraints
