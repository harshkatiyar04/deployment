import cloudinary
import cloudinary.uploader
import cloudinary.utils
from fastapi import UploadFile
from typing import Optional
from app.db.config import cloudinary_settings
import logging
import re

logger = logging.getLogger(__name__)

_CLOUDINARY_DELIVERY_RE = re.compile(
    r"^https?://res\.cloudinary\.com/[^/]+/(?P<rtype>image|video|raw)/upload/(?:v\d+/)?(?P<public_id>.+?)(?:\.(?P<ext>pdf|jpe?g|png|webp|gif))?(?:\?.*)?$",
    re.IGNORECASE,
)

# Configure Once
if cloudinary_settings.cloud_name:
    cloudinary.config(
        cloud_name=cloudinary_settings.cloud_name,
        api_key=cloudinary_settings.api_key,
        api_secret=cloudinary_settings.api_secret,
        secure=True
    )

async def upload_image(file: UploadFile, folder: str = "zenk/chat") -> Optional[str]:
    """
    Upload an image file to Cloudinary.
    Returns the secure URL of the uploaded image.
    """
    try:
        # We read the content and upload
        content = await file.read()
        result = cloudinary.uploader.upload(
            content,
            folder=folder,
            resource_type="image"
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        return None
    finally:
        await file.seek(0) # Reset file pointer for any other use cases

async def upload_video(file: UploadFile, folder: str = "zenk/support") -> Optional[str]:
    """Upload a video file to Cloudinary."""
    try:
        content = await file.read()
        result = cloudinary.uploader.upload(
            content,
            folder=folder,
            resource_type="video",
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary video upload error: {e}")
        return None
    finally:
        await file.seek(0)


async def upload_raw(file: UploadFile, folder: str = "zenk/docs") -> Optional[str]:
    """
    Upload a non-image file (PDF, etc) to Cloudinary.
    Returns the secure URL.
    """
    try:
        content = await file.read()
        name = (file.filename or "").lower()
        upload_kwargs: dict = {"folder": folder, "resource_type": "raw"}
        if name.endswith(".pdf"):
            upload_kwargs["format"] = "pdf"
        result = cloudinary.uploader.upload(content, **upload_kwargs)
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary raw upload error: {e}")
        return None
    finally:
        await file.seek(0)


def parse_cloudinary_url(url: str) -> tuple[str, str, str | None] | None:
    """Return (resource_type, public_id, format_ext) from a Cloudinary delivery URL."""
    match = _CLOUDINARY_DELIVERY_RE.match((url or "").strip().rstrip("/"))
    if not match:
        return None
    return match.group("rtype").lower(), match.group("public_id"), (match.group("ext") or "").lower() or None


def _delivery_url_variants(stored_url: str, *, format_ext: str | None = None) -> list[str]:
    """Build alternate delivery URLs (strip version, toggle extension)."""
    url = stored_url.strip().rstrip("/")
    variants: list[str] = [url]
    no_version = re.sub(r"/upload/v\d+/", "/upload/", url, count=1)
    if no_version != url:
        variants.append(no_version)

    parsed = parse_cloudinary_url(url)
    if not parsed:
        return list(dict.fromkeys(variants))

    _rtype, public_id, ext = parsed
    ext = format_ext or ext
    prefix_match = re.match(
        r"^(https?://res\.cloudinary\.com/[^/]+/[^/]+/upload/(?:v\d+/)?)",
        url,
        re.I,
    )
    if prefix_match:
        prefix = re.sub(r"/upload/v\d+/", "/upload/", prefix_match.group(1))
        bare = f"{prefix}{public_id}"
        variants.append(bare)
        if ext:
            variants.append(f"{bare}.{ext}")
        elif format_ext:
            variants.append(f"{bare}.{format_ext}")

    return list(dict.fromkeys(v for v in variants if v))


def build_signed_download_url(
    public_id: str,
    *,
    resource_type: str = "raw",
    format_ext: str | None = None,
) -> str | None:
    """Signed Cloudinary download URL (works when plain delivery 404s)."""
    if not cloudinary_settings.cloud_name or not cloudinary_settings.api_secret:
        return None
    try:
        fmt = format_ext or ("pdf" if resource_type == "raw" else "")
        return cloudinary.utils.private_download_url(
            public_id,
            fmt,
            resource_type=resource_type,
            attachment=False,
        )
    except Exception as exc:
        logger.warning("Cloudinary signed URL failed for %s: %s", public_id, exc)
        return None


async def fetch_cloudinary_bytes(stored_url: str, *, format_hint: str | None = None) -> bytes:
    """
    Fetch asset bytes from Cloudinary using signed URLs and delivery URL variants.
    Raises ValueError when the asset cannot be retrieved.
    """
    import httpx

    parsed = parse_cloudinary_url(stored_url)
    candidates = _delivery_url_variants(stored_url, format_ext=format_hint)

    if parsed:
        resource_type, public_id, ext = parsed
        fmt = format_hint or ext
        for rt in (resource_type, "raw", "image"):
            signed = build_signed_download_url(
                public_id,
                resource_type=rt,
                format_ext=fmt or ("pdf" if rt == "raw" else None),
            )
            if signed:
                candidates.insert(0, signed)

    candidates = list(dict.fromkeys(candidates))
    last_status: int | None = None

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        for candidate in candidates:
            try:
                response = await client.get(candidate)
                last_status = response.status_code
                if response.status_code == 200 and response.content:
                    return response.content
            except httpx.HTTPError as exc:
                logger.debug("Cloudinary candidate failed %s: %s", candidate, exc)

    if last_status == 404:
        raise ValueError("Document not found in Cloudinary storage")
    raise ValueError("Could not retrieve document from Cloudinary")
