r"""Integration check: upload a real image to GCS via ImageService.

Proves end-to-end that the configured bucket + service-account credentials
work and that the returned URL is publicly readable — WITHOUT needing the
database or a merchant JWT (it calls ImageService directly).

Run from the project root with the same env the service uses:

    # PowerShell
    $env:GCS_BUCKET="kubereats-menu-images"
    $env:GCP_PROJECT="project-7e4d63c9-6a51-487b-866"
    $env:GOOGLE_APPLICATION_CREDENTIALS="$HOME\merchant-gcs-sa-key.json"
    uv run python scripts/verify_gcs.py

Exit code 0 = success. Anything else = something to fix (the message says what).
"""

import base64
import io
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from fastapi import UploadFile  # noqa: E402
from starlette.datastructures import Headers  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.image_service import ImageService  # noqa: E402

# A minimal valid 1x1 PNG, so we don't depend on a test image on disk.
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNg"
    "AAIAAAUAAen63NgAAAAASUVORK5CYII="
)


def _make_upload() -> UploadFile:
    return UploadFile(
        filename="verify.png",
        file=io.BytesIO(_PNG_1X1),
        headers=Headers({"content-type": "image/png"}),
    )


def main() -> int:
    settings = get_settings()
    print(f"→ Bucket : {settings.gcs_bucket}")
    print(f"→ Project: {settings.gcp_project or '(inferred from credentials)'}")

    # 1. Upload through the real service code path.
    try:
        url = ImageService().upload_menu_image(_make_upload(), merchant_id=999)
    except Exception as exc:  # noqa: BLE001 - surface the raw cause to the user
        print(f"\n✗ Upload failed: {type(exc).__name__}: {exc}")
        print(
            "  Check: GOOGLE_APPLICATION_CREDENTIALS points at a valid key, the "
            "service account has roles/storage.objectAdmin on the bucket, and "
            "the bucket exists."
        )
        return 1
    print(f"\n✓ Uploaded: {url}")

    # 2. Confirm the object is publicly readable (allUsers objectViewer).
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            status = resp.status
    except Exception as exc:  # noqa: BLE001
        print(f"✗ URL not publicly readable: {type(exc).__name__}: {exc}")
        print(
            "  The upload worked but the object isn't public. Run:\n"
            "  gcloud storage buckets add-iam-policy-binding "
            f"gs://{settings.gcs_bucket} "
            "--member=allUsers --role=roles/storage.objectViewer"
        )
        return 2

    if status == 200:
        print(f"✓ Public URL returns HTTP {status} — anyone can load the image.")
        print("\nAll good. GCS integration verified end-to-end. ✅")
        return 0

    print(f"✗ Public URL returned HTTP {status} (expected 200).")
    return 3


if __name__ == "__main__":
    sys.exit(main())
