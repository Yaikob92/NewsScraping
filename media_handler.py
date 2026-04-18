"""
Media Handler
Handles downloading media from Telegram and uploading it to Cloudinary.
"""

import logging
import io
import cloudinary
import cloudinary.uploader
import config

logger = logging.getLogger(__name__)

# Configure Cloudinary
if config.CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=config.CLOUDINARY_CLOUD_NAME,
        api_key=config.CLOUDINARY_API_KEY,
        api_secret=config.CLOUDINARY_API_SECRET,
        secure=True
    )
else:
    logger.warning("Cloudinary credentials not set. Image uploads will be skipped.")

async def upload_to_cloudinary(file_path_or_bytes, folder="telegram_media", public_id=None):
    """
    Uploads a file or bytes to Cloudinary and returns the secure URL.
    """
    if not config.CLOUDINARY_CLOUD_NAME:
        return None

    try:
        # If it's bytes, wrap it in BytesIO
        if isinstance(file_path_or_bytes, bytes):
            file_to_upload = io.BytesIO(file_path_or_bytes)
        else:
            file_to_upload = file_path_or_bytes

        upload_result = cloudinary.uploader.upload(
            file_to_upload,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type="auto"
        )
        return upload_result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        return None
