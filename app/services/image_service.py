import uuid
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

# Allowed image content types mapped to their file extension.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


class ImageService:
    """Uploads menu images to MinIO (S3-compatible) and returns public URLs."""

    def __init__(self):
        settings = get_settings()
        self._bucket = settings.minio_bucket
        self._public_url = (
            settings.minio_public_url or settings.minio_endpoint
        ).rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

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
            self._ensure_bucket()
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=file.content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload image to storage.",
            ) from exc

        return f"{self._public_url}/{self._bucket}/{key}"


@lru_cache
def get_image_service() -> ImageService:
    """Cached singleton so the boto3 client is reused across requests."""
    return ImageService()
