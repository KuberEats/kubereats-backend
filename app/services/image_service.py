import uuid
from functools import lru_cache

from fastapi import HTTPException, UploadFile, status
from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage

from app.core.config import get_settings

# Allowed image content types mapped to their file extension.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


class ImageService:
    """Uploads menu images to GCP Cloud Storage and returns public URLs.

    Authentication uses Application Default Credentials: on GKE this is
    Workload Identity, on-prem it is the service-account key file pointed to by
    the GOOGLE_APPLICATION_CREDENTIALS environment variable.
    """

    def __init__(self):
        settings = get_settings()
        self._bucket_name = settings.gcs_bucket
        self._client = storage.Client(project=settings.gcp_project or None)
        self._bucket = self._client.bucket(self._bucket_name)

    def upload_menu_image(self, file: UploadFile, merchant_id: int) -> str:
        ext = ALLOWED_CONTENT_TYPES.get(file.content_type or "")
        if ext is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported image type. Allowed: JPEG, PNG, WebP.",
            )

        content = file.file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file.",
            )
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image exceeds the 5 MB size limit.",
            )

        key = f"{merchant_id}/{uuid.uuid4().hex}.{ext}"
        try:
            blob = self._bucket.blob(key)
            blob.upload_from_string(content, content_type=file.content_type)
        except GoogleAPIError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload image to storage.",
            ) from exc

        # Bucket grants allUsers objectViewer, so this public URL is readable
        # directly by the browser without signing.
        return f"https://storage.googleapis.com/{self._bucket_name}/{key}"


@lru_cache
def get_image_service() -> ImageService:
    """Cached singleton so the storage client is reused across requests."""
    return ImageService()
