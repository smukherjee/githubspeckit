"""Profile service with business logic and RBAC enforcement.

Coordinates profile management operations with authorization checks.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.models import UserDetailsModel, UserModel
from schemas.user_profile import UserProfileResponse, UserProfileUpdateRequest


class ProfileService:
    """Service for managing user profile details with RBAC."""
    
    def __init__(self, session: AsyncSession):
        """Initialize profile service.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get_profile(
        self,
        user_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
        current_user_tenant_id: Optional[UUID]
    ) -> Optional[UserProfileResponse]:
        """Get user profile with RBAC enforcement.
        
        Args:
            user_id: Target user ID
            current_user_id: Current authenticated user ID
            current_user_role: Current user's role
            current_user_tenant_id: Current user's tenant ID (None for superadmin)
        
        Returns:
            UserProfileResponse if authorized and exists, None otherwise
            
        Raises:
            PermissionError: If user not authorized to view profile
        """
        # Check RBAC: Users can view own profile, tenant_admin can view same tenant, superadmin can view all
        if not await self._can_access_profile(
            user_id, current_user_id, current_user_role, current_user_tenant_id
        ):
            raise PermissionError("You do not have permission to view this profile")
        
        # Query profile with user tenant info for additional validation
        stmt = (
            select(UserDetailsModel)
            .join(UserModel, UserDetailsModel.user_id == UserModel.user_id)
            .where(UserDetailsModel.user_id == user_id)
        )
        
        result = await self.session.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if profile is None:
            return None
        
        return UserProfileResponse.model_validate(profile)
    
    async def update_profile(
        self,
        user_id: UUID,
        update_request: UserProfileUpdateRequest,
        current_user_id: UUID,
        current_user_role: str,
        current_user_tenant_id: Optional[UUID]
    ) -> UserProfileResponse:
        """Update (or create) user profile with RBAC enforcement.
        
        Args:
            user_id: Target user ID
            update_request: Profile update data
            current_user_id: Current authenticated user ID
            current_user_role: Current user's role
            current_user_tenant_id: Current user's tenant ID
            
        Returns:
            Updated UserProfileResponse
            
        Raises:
            PermissionError: If user not authorized to edit profile
        """
        # Check RBAC: Users can edit own profile, tenant_admin can edit same tenant
        if not await self._can_edit_profile(
            user_id, current_user_id, current_user_role, current_user_tenant_id
        ):
            raise PermissionError("You do not have permission to edit this profile")
        
        # Check if profile exists
        stmt = select(UserDetailsModel).where(UserDetailsModel.user_id == user_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        
        if existing:
            # Update existing profile
            update_data = update_request.model_dump(exclude_unset=True)
            update_data['updated_at'] = now
            update_data['updated_by'] = current_user_id
            
            stmt = (
                update(UserDetailsModel)
                .where(UserDetailsModel.user_id == user_id)
                .values(**update_data)
                .returning(UserDetailsModel)
            )
            result = await self.session.execute(stmt)
            profile = result.scalar_one()
        else:
            # Create new profile
            profile = UserDetailsModel(
                user_id=user_id,
                full_name=update_request.full_name,
                phone=update_request.phone,
                address=update_request.address,
                created_at=now,
                updated_at=now,
                created_by=current_user_id,
                updated_by=current_user_id
            )
            self.session.add(profile)
            await self.session.flush()
        
        await self.session.commit()
        await self.session.refresh(profile)
        
        return UserProfileResponse.model_validate(profile)
    
    async def delete_photo(
        self,
        user_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
        current_user_tenant_id: Optional[UUID]
    ) -> None:
        """Delete user profile photo with RBAC enforcement.
        
        Args:
            user_id: Target user ID
            current_user_id: Current authenticated user ID
            current_user_role: Current user's role
            current_user_tenant_id: Current user's tenant ID
            
        Raises:
            PermissionError: If user not authorized to delete photo
        """
        # Check RBAC: Users can delete own photo, tenant_admin can delete same tenant
        if not await self._can_edit_profile(
            user_id, current_user_id, current_user_role, current_user_tenant_id
        ):
            raise PermissionError("You do not have permission to delete this photo")
        
        # Set photo URLs to NULL
        stmt = (
            update(UserDetailsModel)
            .where(UserDetailsModel.user_id == user_id)
            .values(
                photo_display_url=None,
                photo_thumbnail_url=None,
                photo_avatar_url=None,
                updated_at=datetime.now(timezone.utc),
                updated_by=current_user_id
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def _can_access_profile(
        self,
        target_user_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
        current_user_tenant_id: Optional[UUID]
    ) -> bool:
        """Check if current user can view target user's profile.
        
        Rules:
        - User can view own profile
        - Tenant admin can view profiles in same tenant
        - Superadmin can view all profiles
        """
        # Users can view their own profile
        if target_user_id == current_user_id:
            return True
        
        # Superadmin can view all
        if current_user_role == "superadmin":
            return True
        
        # Tenant admin can view same tenant
        if current_user_role == "tenant_admin" and current_user_tenant_id:
            # Check if target user is in same tenant
            stmt = select(UserModel).where(UserModel.user_id == target_user_id)
            result = await self.session.execute(stmt)
            target_user = result.scalar_one_or_none()
            
            if target_user and target_user.tenant_id == current_user_tenant_id:
                return True
        
        return False
    
    async def _can_edit_profile(
        self,
        target_user_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
        current_user_tenant_id: Optional[UUID]
    ) -> bool:
        """Check if current user can edit target user's profile.
        
        Rules (aligned with user update RBAC):
        - Superadmin: Can edit any user's profile across all tenants
        - Tenant admin: Can edit profiles in same tenant only
        - Regular user: Can edit only their own profile
        """
        # Superadmin can edit any profile
        if current_user_role == "superadmin":
            return True
        
        # Users can edit their own profile
        if target_user_id == current_user_id:
            return True
        
        # Tenant admin can edit same tenant
        if current_user_role == "tenant_admin" and current_user_tenant_id:
            # Check if target user is in same tenant
            stmt = select(UserModel).where(UserModel.user_id == target_user_id)
            result = await self.session.execute(stmt)
            target_user = result.scalar_one_or_none()
            
            if target_user and target_user.tenant_id == current_user_tenant_id:
                return True
        
        return False

    async def update_photo_urls(
        self,
        user_id: str,
        actor_id: str,
        display_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> None:
        """Update photo URLs in user_details (called from background task).
        
        This is used by the photo processing background task after
        successfully processing and storing photo variants.
        
        Args:
            user_id: User ID (string UUID)
            actor_id: ID of the user performing the action (for audit fields)
            display_url: URL for display variant (640x640)
            thumbnail_url: URL for thumbnail variant (96x96)
            avatar_url: URL for avatar variant (48x48)
        """
        from uuid import UUID as UUIDType
        
        user_uuid = UUIDType(user_id)
        actor_uuid = UUIDType(actor_id)
        
        # Check if profile exists
        stmt = select(UserDetailsModel).where(UserDetailsModel.user_id == user_uuid)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing profile
            stmt = (
                update(UserDetailsModel)
                .where(UserDetailsModel.user_id == user_uuid)
                .values(
                    photo_display_url=display_url,
                    photo_thumbnail_url=thumbnail_url,
                    photo_avatar_url=avatar_url,
                    updated_at=datetime.now(timezone.utc),
                    updated_by=actor_uuid
                )
            )
            await self.session.execute(stmt)
        else:
            # Create new profile with just photo URLs
            new_details = UserDetailsModel(
                user_id=user_uuid,
                photo_display_url=display_url,
                photo_thumbnail_url=thumbnail_url,
                photo_avatar_url=avatar_url,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=actor_uuid,
                updated_by=actor_uuid
            )
            self.session.add(new_details)
        
        await self.session.commit()
