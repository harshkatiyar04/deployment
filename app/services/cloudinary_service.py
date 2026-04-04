import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from typing import Optional
from app.db.config import cloudinary_settings
import logging

logger = logging.getLogger(__name__)

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

async def upload_raw(file: UploadFile, folder: str = "zenk/docs") -> Optional[str]:
    """
    Upload a non-image file (PDF, etc) to Cloudinary.
    Returns the secure URL.
    """
    try:
        content = await file.read()
        result = cloudinary.uploader.upload(
            content,
            folder=folder,
            resource_type="raw"
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary raw upload error: {e}")
        return None
    finally:
        await file.seek(0)
