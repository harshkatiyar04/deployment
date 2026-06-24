from __future__ import annotations

import os
import base64
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from app.services.cloudinary_service import upload_image, upload_raw

def _guess_upload_content_type(file: UploadFile) -> Optional[str]:
    if file.content_type and file.content_type != "application/octet-stream":
        return file.content_type
    name = (file.filename or "").lower()
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".pdf"):
        return "application/pdf"
    return file.content_type


async def save_kyc_file(*, signup_id: str, file: UploadFile) -> tuple[str, str, Optional[str]]:
    """Save KYC file to Cloudinary."""
    content_type = _guess_upload_content_type(file)
    is_image = content_type in ["image/jpeg", "image/png", "image/webp", "image/gif"]
    folder = f"zenk/kyc/{signup_id}"
    
    if is_image:
        url = await upload_image(file, folder=folder)
    else:
        url = await upload_raw(file, folder=folder)

    if not url:
        raise ValueError("Failed to upload KYC document to Cloudinary")

    # Return URL as stored_path for backward compatibility
    stored_filename = file.filename or "kyc_document"
    return stored_filename, url, content_type

async def save_kyc_files(*, signup_id: str, files: list[UploadFile]) -> list[tuple[str, str, Optional[str], str]]:
    """Save multiple KYC files to Cloudinary."""
    out: list[tuple[str, str, str | None, str]] = []
    for f in files:
        stored_filename, url, content_type = await save_kyc_file(signup_id=signup_id, file=f)
        out.append((stored_filename, url, content_type, f.filename or stored_filename))
    return out

async def save_kyc_file_base64(*, signup_id: str, filename: str, content_base64: str, content_type: Optional[str] = None) -> tuple[str, str, Optional[str]]:
    """Save base64 KYC file to Cloudinary."""
    import io
    
    try:
        file_content = base64.b64decode(content_base64)
    except Exception as e:
        raise ValueError(f"Invalid base64 content: {e}")


    import cloudinary.uploader

    if content_type:
        is_image = content_type in ["image/jpeg", "image/png", "image/webp"]
    elif filename.lower().endswith(".pdf"):
        is_image = False
    else:
        is_image = True
    folder = f"zenk/kyc/{signup_id}"
    
    try:
        upload_kwargs: dict = {
            "folder": folder,
            "resource_type": "image" if is_image else "raw",
        }
        if not is_image and filename.lower().endswith(".pdf"):
            upload_kwargs["format"] = "pdf"
        result = cloudinary.uploader.upload(file_content, **upload_kwargs)
        url = result.get("secure_url")
        if not url:
            raise ValueError("Cloudinary upload failed")
    except Exception as e:
        raise ValueError(f"Cloudinary upload error: {e}")

    return filename, url, content_type
