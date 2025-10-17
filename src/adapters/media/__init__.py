"""Media adapters for photo storage and processing."""

from .storage import PhotoStorage, LocalFileStorage, get_photo_storage
from .photo_processor import PhotoProcessor

__all__ = [
    "PhotoStorage",
    "LocalFileStorage",
    "get_photo_storage",
    "PhotoProcessor",
]
