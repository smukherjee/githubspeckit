"""Photo storage abstraction for profile photos.

Provides interface for storing and retrieving profile photos with support
for multiple storage backends (local filesystem, S3, etc.).
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


class PhotoStorage(ABC):
    """Abstract interface for photo storage operations."""

    @abstractmethod
    async def save_photo(
        self, user_id: str, variant: str, photo_bytes: bytes
    ) -> str:
        """Save a photo variant and return its URL.

        Args:
            user_id: User ID (used for organizing storage)
            variant: Photo variant name (display, thumbnail, avatar)
            photo_bytes: Photo data as bytes

        Returns:
            URL to access the saved photo
        """
        pass

    @abstractmethod
    async def delete_photos(self, user_id: str) -> None:
        """Delete all photo variants for a user.

        Args:
            user_id: User ID whose photos should be deleted
        """
        pass

    @abstractmethod
    async def photo_exists(self, user_id: str, variant: str) -> bool:
        """Check if a photo variant exists.

        Args:
            user_id: User ID
            variant: Photo variant name

        Returns:
            True if photo exists, False otherwise
        """
        pass


class LocalFileStorage(PhotoStorage):
    """Local filesystem storage implementation.

    Stores photos in a directory structure:
    {base_path}/{user_id}/{variant}.jpg

    URLs are generated as:
    {base_url}/{user_id}/{variant}.jpg
    """

    def __init__(self, base_path: str, base_url: str):
        """Initialize local file storage.

        Args:
            base_path: Root directory for storing photos (e.g., 'data/photos')
            base_url: Base URL for accessing photos (e.g., '/media/photos')
        """
        self.base_path = Path(base_path)
        self.base_url = base_url.rstrip("/")

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save_photo(
        self, user_id: str, variant: str, photo_bytes: bytes
    ) -> str:
        """Save photo to local filesystem.

        Creates user directory if it doesn't exist.
        Overwrites existing photo if present.
        """
        user_dir = self.base_path / user_id
        user_dir.mkdir(exist_ok=True)

        # Remove old photos for this variant to prevent accumulation
        for old_photo in user_dir.glob(f"{variant}_*.jpg"):
            old_photo.unlink(missing_ok=True)
        # Also remove the old non-timestamped version for compatibility
        old_path = user_dir / f"{variant}.jpg"
        old_path.unlink(missing_ok=True)

        # Generate timestamp-based filename for cache-busting
        from datetime import datetime, timezone
        import hashlib
        timestamp = int(datetime.now(timezone.utc).timestamp())
        content_hash = hashlib.md5(photo_bytes).hexdigest()[:8]  # First 8 chars of MD5
        photo_path = user_dir / f"{variant}_{timestamp}_{content_hash}.jpg"

        # Write photo atomically (write to temp, then rename)
        temp_path = photo_path.with_suffix(".tmp")
        temp_path.write_bytes(photo_bytes)
        temp_path.replace(photo_path)

        # Generate URL
        url = f"{self.base_url}/{user_id}/{photo_path.name}"
        return url

    async def delete_photos(self, user_id: str) -> None:
        """Delete all photos for a user.

        Removes user directory and all contained files.
        """
        user_dir = self.base_path / user_id
        if user_dir.exists() and user_dir.is_dir():
            for photo_file in user_dir.glob("*.jpg"):
                photo_file.unlink()
            # Remove directory if empty
            try:
                user_dir.rmdir()
            except OSError:
                # Directory not empty (has other files), leave it
                pass

    async def photo_exists(self, user_id: str, variant: str) -> bool:
        """Check if photo file exists."""
        user_dir = self.base_path / user_id
        if not user_dir.exists():
            return False
        
        # Check for timestamped variants
        for photo_file in user_dir.glob(f"{variant}_*.jpg"):
            return True
        
        # Check for old non-timestamped version (backward compatibility)
        old_path = user_dir / f"{variant}.jpg"
        return old_path.exists()


class S3Storage(PhotoStorage):
    """S3 storage implementation (placeholder for future).

    AWS S3 or compatible object storage for production deployments.
    """

    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str):
        """Initialize S3 storage (not yet implemented)."""
        raise NotImplementedError("S3 storage not yet implemented. Use LocalFileStorage for now.")

    async def save_photo(self, user_id: str, variant: str, photo_bytes: bytes) -> str:
        """Save photo to S3."""
        raise NotImplementedError()

    async def delete_photos(self, user_id: str) -> None:
        """Delete photos from S3."""
        raise NotImplementedError()

    async def photo_exists(self, user_id: str, variant: str) -> bool:
        """Check if photo exists in S3."""
        raise NotImplementedError()


def get_photo_storage(config_path: str = "config/descriptor.toml") -> PhotoStorage:
    """Factory function to get configured photo storage instance.

    Reads configuration from descriptor.toml photo_storage section.
    Note: descriptor.toml uses sections like [photo_storage.STORAGE_TYPE]
    with .default values.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured PhotoStorage instance

    Raises:
        ValueError: If storage type is invalid or required config is missing
    """
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    
    # Extract photo_storage config (structured as [photo_storage.KEY] with .default)
    photo_storage_config = config.get("photo_storage", {})
    
    # Get values from default fields
    storage_type = photo_storage_config.get("STORAGE_TYPE", {}).get("default", "local")
    local_path = photo_storage_config.get("LOCAL_BASE_PATH", {}).get("default", "data/photos")

    if storage_type == "local":
        # For local storage, base_url is hardcoded to match FastAPI mount point
        base_url = "/media/photos"
        
        return LocalFileStorage(base_path=local_path, base_url=base_url)

    elif storage_type == "s3":
        raise NotImplementedError("S3 storage not yet implemented")

    else:
        raise ValueError(
            f"Invalid storage_type '{storage_type}'. Must be 'local' or 's3'"
        )
