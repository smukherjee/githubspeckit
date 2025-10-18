"""Profile management API router.

Endpoints for user profile details CRUD and photo upload.
"""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.api.auth_deps import get_current_user, AuthenticatedUser
from schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    PhotoUploadResponse
)
from services.profile_service import ProfileService
from adapters.media import PhotoProcessor, get_photo_storage


router = APIRouter(prefix="/v1/users", tags=["profiles"])


@router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]
):
    """Get user profile details (GET /api/v1/users/{user_id}/profile).
    
    RBAC:
    - Users can view own profile
    - Tenant admins can view profiles in same tenant
    - Superadmin can view all profiles
    
    Returns:
        UserProfileResponse: Profile details with photo URLs
        
    Raises:
        HTTPException 403: If user not authorized to view profile
        HTTPException 404: If profile not found
    """
    service = ProfileService(session)
    
    # Determine role (priority: superadmin > tenant_admin > user)
    from uuid import UUID as UUIDType
    if "superadmin" in current_user.roles:
        role = "superadmin"
    elif "tenant_admin" in current_user.roles:
        role = "tenant_admin"
    else:
        role = "user"
    
    try:
        profile = await service.get_profile(
            user_id=user_id,
            current_user_id=UUIDType(current_user.user_id),
            current_user_role=role,
            current_user_tenant_id=UUIDType(current_user.tenant_id) if current_user.tenant_id else None
        )
        
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return profile
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{user_id}/profile", response_model=UserProfileResponse)
async def update_profile(
    user_id: UUID,
    update_request: UserProfileUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]
):
    """Create or update user profile details (PUT /api/v1/users/{user_id}/profile).
    
    RBAC:
    - Users can edit own profile
    - Tenant admins can edit profiles in same tenant
    
    Args:
        user_id: Target user ID
        update_request: Profile update data
        
    Returns:
        UserProfileResponse: Updated profile
        
    Raises:
        HTTPException 403: If user not authorized to edit profile
        HTTPException 422: If validation fails
    """
    service = ProfileService(session)
    
    # Determine role
    from uuid import UUID as UUIDType
    if "superadmin" in current_user.roles:
        role = "superadmin"
    elif "tenant_admin" in current_user.roles:
        role = "tenant_admin"
    else:
        role = "user"
    
    try:
        profile = await service.update_profile(
            user_id=user_id,
            update_request=update_request,
            current_user_id=UUIDType(current_user.user_id),
            current_user_role=role,
            current_user_tenant_id=UUIDType(current_user.tenant_id) if current_user.tenant_id else None
        )
        return profile
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{user_id}/profile/photo", response_model=PhotoUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_profile_photo(
    user_id: UUID,
    photo: Annotated[UploadFile, File(...)],
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]
):
    """Upload user profile photo (POST /api/v1/users/{user_id}/profile/photo).
    
    Accepts multipart/form-data with 'photo' field.
    Processes photo in background to generate 3 variants:
    - Display: 640x640px
    - Thumbnail: 96x96px
    - Avatar: 48x48px
    
    RBAC:
    - Users can upload photo for own profile
    - Tenant admins can upload for profiles in same tenant
    
    Args:
        user_id: Target user ID
        photo: Image file (JPEG, PNG, WebP, GIF)
        
    Returns:
        PhotoUploadResponse: 202 Accepted with processing status
        
    Raises:
        HTTPException 403: If user not authorized to upload photo
        HTTPException 400: If file type invalid
        HTTPException 413: If file size exceeds limit
    """
    # Determine role
    from uuid import UUID as UUIDType
    if "superadmin" in current_user.roles:
        role = "superadmin"
    elif "tenant_admin" in current_user.roles:
        role = "tenant_admin"
    else:
        role = "user"
    
    service = ProfileService(session)
    
    # Check RBAC (using edit permissions for photo upload)
    can_edit = await service._can_edit_profile(
        target_user_id=user_id,
        current_user_id=UUIDType(current_user.user_id),
        current_user_role=role,
        current_user_tenant_id=UUIDType(current_user.tenant_id) if current_user.tenant_id else None
    )
    
    if not can_edit:
        raise HTTPException(status_code=403, detail="You do not have permission to upload photo for this user")
    
    # Validate file type
    content_type = photo.content_type or ""
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (load from config descriptor)
    from domain.config.loader import load_config
    config = load_config({
        "APP_NAME": ("modern-backend", False),  # Required key
        "PASSWORD_MIN_LENGTH": (12, False),  # Required key
        "PASSWORD_COMPLEXITY_STRICT": (False, False),  # Required key
        "MAX_UPLOAD_SIZE_MB": (10, False),  # Photo upload config
    })
    max_size_mb = config.entries["MAX_UPLOAD_SIZE_MB"].value
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Read file to check size
    file_bytes = await photo.read()
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size {len(file_bytes)} bytes exceeds limit of {max_size_bytes} bytes"
        )
    
    # Queue background task to process and save photo
    background_tasks.add_task(
        process_and_save_photo,
        user_id=str(user_id),
        actor_id=current_user.user_id,
        file_bytes=file_bytes
    )
    
    return PhotoUploadResponse(
        status="processing",
        message="Photo upload accepted and processing in background"
    )


@router.delete("/{user_id}/profile/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_photo(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]
):
    """Delete user profile photo (DELETE /api/v1/users/{user_id}/profile/photo).
    
    Sets all photo URLs to NULL.
    
    RBAC:
    - Users can delete own photo
    - Tenant admins can delete photo for profiles in same tenant
    
    Args:
        user_id: Target user ID
        
    Returns:
        204 No Content
        
    Raises:
        HTTPException 403: If user not authorized to delete photo
    """
    service = ProfileService(session)
    
    # Determine role
    from uuid import UUID as UUIDType
    if "superadmin" in current_user.roles:
        role = "superadmin"
    elif "tenant_admin" in current_user.roles:
        role = "tenant_admin"
    else:
        role = "user"
    
    try:
        await service.delete_photo(
            user_id=user_id,
            current_user_id=UUIDType(current_user.user_id),
            current_user_role=role,
            current_user_tenant_id=UUIDType(current_user.tenant_id) if current_user.tenant_id else None
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# Background task functions

async def process_and_save_photo(
    user_id: str,
    actor_id: str,
    file_bytes: bytes
):
    """Background task to process photo and save variants.
    
    This runs asynchronously after the HTTP response is sent.
    Creates its own database session to avoid session scope issues.
    
    Steps:
    1. Validate photo file type and size
    2. Process into 3 variants (display, thumbnail, avatar)
    3. Save variants to storage
    4. Update user_details with photo URLs
    
    Args:
        user_id: User ID (string UUID)
        actor_id: ID of user performing the action (for audit fields)
        file_bytes: Raw photo bytes
    """
    try:
        # Initialize processor and storage
        processor = PhotoProcessor()
        storage = get_photo_storage()
        
        # Validate photo
        is_valid, error_msg = await processor.validate_photo(file_bytes)
        if not is_valid:
            # Log error (photo was already accepted, can't return error to client)
            print(f"Photo validation failed for user {user_id}: {error_msg}")
            return
        
        # Process photo into variants
        variants = await processor.process_photo(file_bytes)
        
        # Save each variant and collect URLs
        photo_urls = {}
        for variant_name, variant_bytes in variants.items():
            url = await storage.save_photo(user_id, variant_name, variant_bytes)
            photo_urls[variant_name] = url
        
        # Create new database session for background task
        from adapters.api.deps import get_session_maker
        session_maker = get_session_maker()
        
        async with session_maker() as session:
            try:
                # Update user_details with photo URLs
                service = ProfileService(session)
                await service.update_photo_urls(
                    user_id=user_id,
                    actor_id=actor_id,
                    display_url=photo_urls.get("display"),
                    thumbnail_url=photo_urls.get("thumbnail"),
                    avatar_url=photo_urls.get("avatar")
                )
                await session.commit()
            except Exception as db_error:
                await session.rollback()
                raise db_error
        
        print(f"Photo processing complete for user {user_id}: {photo_urls}")
        
    except Exception as e:
        # Log error but don't crash the background task
        print(f"Photo processing failed for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
