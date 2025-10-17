"""Photo processing for profile photos.

Handles image validation, EXIF stripping, resizing, and compression for
profile photos. Generates 3 variants optimized for different use cases.
"""
from io import BytesIO
from typing import Dict, Optional
import magic
from PIL import Image


class PhotoProcessor:
    """Processes uploaded photos into optimized variants.

    Variants:
    - display: 640x640px, JPEG quality 85 (~50-100KB)
    - thumbnail: 96x96px, JPEG quality 80 (~10-20KB)
    - avatar: 48x48px, JPEG quality 75 (~5-10KB)

    Total size budget: ~200KB for all 3 variants
    """

    # Variant specifications
    VARIANTS = {
        "display": {"size": (640, 640), "quality": 85},
        "thumbnail": {"size": (96, 96), "quality": 80},
        "avatar": {"size": (48, 48), "quality": 75},
    }

    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",  # Will be converted to JPEG
    }

    # Max file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self):
        """Initialize photo processor."""
        self.magic = magic.Magic(mime=True)

    async def validate_photo(self, photo_bytes: bytes) -> tuple[bool, Optional[str]]:
        """Validate photo file type and size.

        Args:
            photo_bytes: Raw photo data

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, error_message) if invalid
        """
        # Check file size
        if len(photo_bytes) > self.MAX_FILE_SIZE:
            size_mb = len(photo_bytes) / (1024 * 1024)
            return False, f"File too large: {size_mb:.1f}MB (max 10MB)"

        # Check MIME type using python-magic
        mime_type = self.magic.from_buffer(photo_bytes)

        if mime_type not in self.ALLOWED_MIME_TYPES:
            return False, f"Invalid file type: {mime_type}. Must be JPEG, PNG, WebP, or GIF"

        # Try to open with PIL to ensure it's a valid image
        try:
            img = Image.open(BytesIO(photo_bytes))
            img.verify()  # Verify it's a valid image
        except Exception as e:
            return False, f"Invalid or corrupted image: {str(e)}"

        return True, None

    async def process_photo(self, photo_bytes: bytes) -> Dict[str, bytes]:
        """Process photo into all variants.

        Steps for each variant:
        1. Open image with PIL
        2. Convert to RGB (handles PNG transparency, GIF frames, etc.)
        3. Strip EXIF data (privacy + security)
        4. Resize to target dimensions (maintains aspect ratio with crop)
        5. Compress to JPEG with quality setting
        6. Return bytes

        Args:
            photo_bytes: Raw photo data (already validated)

        Returns:
            Dictionary mapping variant name to processed bytes:
            {
                "display": bytes,
                "thumbnail": bytes,
                "avatar": bytes
            }

        Raises:
            ValueError: If photo processing fails
        """
        try:
            # Open original image
            img = Image.open(BytesIO(photo_bytes))

            # Convert to RGB (handles RGBA, P, etc.)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Process each variant
            variants = {}
            for variant_name, spec in self.VARIANTS.items():
                variant_bytes = await self._create_variant(img, spec)
                variants[variant_name] = variant_bytes

            return variants

        except Exception as e:
            raise ValueError(f"Photo processing failed: {str(e)}")

    async def _create_variant(
        self, img: Image.Image, spec: Dict
    ) -> bytes:
        """Create a single photo variant.

        Args:
            img: Source PIL Image (RGB mode)
            spec: Variant specification (size, quality)

        Returns:
            Processed image as JPEG bytes
        """
        # Make a copy to avoid modifying original
        variant_img = img.copy()

        # Resize with aspect ratio preservation and center crop
        variant_img = self._resize_and_crop(variant_img, spec["size"])

        # Convert to JPEG bytes (EXIF automatically stripped)
        output = BytesIO()
        variant_img.save(
            output,
            format="JPEG",
            quality=spec["quality"],
            optimize=True,  # Enable JPEG optimization
            progressive=True,  # Progressive JPEG for better loading
        )

        return output.getvalue()

    def _resize_and_crop(
        self, img: Image.Image, target_size: tuple[int, int]
    ) -> Image.Image:
        """Resize and center-crop image to exact dimensions.

        Uses cover fit (fills entire target, crops excess):
        1. Resize so smallest dimension matches target
        2. Center crop to exact target size

        Example:
            800x600 → 640x640 target
            1. Resize to 853x640 (height matches)
            2. Crop to 640x640 (remove 106px left, 107px right)

        Args:
            img: Source image
            target_size: Target (width, height)

        Returns:
            Resized and cropped image
        """
        img_width, img_height = img.size
        target_width, target_height = target_size

        # Calculate scale to fill target (cover fit)
        scale = max(
            target_width / img_width,
            target_height / img_height
        )

        # Resize with scale
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        img_resized = img.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS  # High-quality downsampling
        )

        # Center crop to exact target size
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        img_cropped = img_resized.crop((left, top, right, bottom))

        return img_cropped
