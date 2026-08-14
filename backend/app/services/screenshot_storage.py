"""Persistent screenshot storage for browser captures.

Screenshots are uploaded to Firebase Cloud Storage when the Admin SDK is
configured. The returned URL is stable enough for history/result pages and the
object path is retained so it can be deleted with its analysis record.
"""
from __future__ import annotations

from datetime import timedelta
from urllib.parse import quote
import uuid

from app.config import settings


def upload_screenshot(data: bytes, filename: str) -> tuple[str, str] | None:
    """Upload bytes and return ``(download_url, object_path)``.

    Returns ``None`` when Firebase Storage is not configured, allowing local
    development to continue using the existing mounted reports directory.
    """
    if not settings.firebase_service_account or not settings.firebase_storage_bucket:
        return None

    try:
        from firebase_admin import storage
        from app.services.firebase_admin import get_firebase_app

        get_firebase_app()
        object_path = f"screenshots/{uuid.uuid4().hex}-{filename}"
        blob = storage.bucket().blob(object_path)
        blob.upload_from_string(data, content_type="image/png")

        # Firebase Storage download URLs use a token stored in object metadata.
        token = uuid.uuid4().hex
        metadata = dict(blob.metadata or {})
        metadata["firebaseStorageDownloadTokens"] = token
        blob.metadata = metadata
        blob.patch()
        bucket_name = blob.bucket.name
        # Prefer a signed URL. It works even when Firebase Storage download
        # rules require authentication, while still keeping the object private.
        try:
            download_url = blob.generate_signed_url(
                version="v4", expiration=timedelta(days=365), method="GET"
            )
        except Exception:
            # Token URLs remain compatible with Firebase's web Storage client.
            download_url = (
                f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/"
                f"{quote(object_path, safe='')}?alt=media&token={token}"
            )
        return download_url, object_path
    except Exception:
        # Keep the scan usable and retain the local capture for diagnostics if
        # a deployment has a temporary Firebase/network configuration issue.
        return None


def delete_screenshot(object_path: str | None) -> None:
    if not object_path or not settings.firebase_service_account or not settings.firebase_storage_bucket:
        return
    from firebase_admin import storage
    from app.services.firebase_admin import get_firebase_app

    get_firebase_app()
    storage.bucket().blob(object_path).delete()
