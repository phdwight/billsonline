"""Image service - compress uploaded bill photos for compact storage.

Photos of physical bills don't need full resolution: they are downscaled,
EXIF-rotated upright, stripped of metadata, and re-encoded as JPEG so a
typical phone photo (3-10 MB) stores at roughly 100-300 KB.
"""
from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

# iPhones shoot HEIC/HEIF by default; teach Pillow to decode it.
register_heif_opener()

# Longest side of the stored image, in pixels. Enough to read meter digits
# and bill line items, far smaller than a raw phone photo.
MAX_DIMENSION = 1600
JPEG_QUALITY = 72
# Reject absurdly large uploads before decoding (bytes).
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


class ImageError(ValueError):
    """Raised when an upload cannot be processed as an image."""


def compress_image(raw: bytes) -> tuple[bytes, int, int]:
    """Compress an uploaded image to a small JPEG.

    Returns (jpeg_bytes, width, height).
    Raises ImageError for oversized or non-image payloads.
    """
    if not raw:
        raise ImageError("The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ImageError("The image is too large (max 15 MB).")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageError("The uploaded file is not a supported image.") from exc

    # Apply EXIF orientation so the stored pixels are upright, then drop metadata.
    img = ImageOps.exif_transpose(img)

    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # JPEG has no alpha channel; flatten transparency onto white.
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue(), img.width, img.height
