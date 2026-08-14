"""Lazy Firebase Admin SDK bootstrap for protected administration endpoints."""
from functools import lru_cache
import firebase_admin
from firebase_admin import credentials
from app.config import settings

@lru_cache(maxsize=1)
def get_firebase_app():
    if firebase_admin._apps:
        return firebase_admin.get_app()
    if not settings.firebase_service_account:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT is not configured on the backend.")
    options = {}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket
    return firebase_admin.initialize_app(credentials.Certificate(str(settings.firebase_service_account)), options or None)
