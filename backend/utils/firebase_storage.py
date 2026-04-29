"""
Firebase Storage integration for ML model artifact persistence.
Used in production (Firebase Cloud Functions) to persist and load the ML model.
Falls back to local file system for local development.
"""
import os


def is_firebase_env() -> bool:
    """Check if running in Firebase Cloud Functions environment."""
    return os.getenv("FIREBASE_CONFIG") is not None or os.getenv("FUNCTION_TARGET") is not None


def upload_model_to_storage(local_model_path: str, storage_path: str = "ml/attendance_model.pkl") -> bool:
    """Upload the trained ML model to Firebase Storage."""
    if not is_firebase_env():
        print("Local environment: skipping Firebase Storage upload.")
        return True
    try:
        import firebase_admin
        from firebase_admin import storage as fb_storage
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        bucket = fb_storage.bucket()
        blob = bucket.blob(storage_path)
        blob.upload_from_filename(local_model_path)
        print(f"Model uploaded to Firebase Storage: gs://{bucket.name}/{storage_path}")
        return True
    except Exception as e:
        print(f"Firebase Storage upload failed: {e}")
        return False


def download_model_from_storage(local_model_path: str, storage_path: str = "ml/attendance_model.pkl") -> bool:
    """Download the ML model from Firebase Storage to local path."""
    if not is_firebase_env():
        return os.path.exists(local_model_path)
    try:
        import firebase_admin
        from firebase_admin import storage as fb_storage
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        bucket = fb_storage.bucket()
        blob = bucket.blob(storage_path)
        if not blob.exists():
            return False
        os.makedirs(os.path.dirname(local_model_path), exist_ok=True)
        blob.download_to_filename(local_model_path)
        print("Model downloaded from Firebase Storage.")
        return True
    except Exception as e:
        print(f"Firebase Storage download failed: {e}")
        return False


def upload_profile_image_to_storage(local_path: str, filename: str) -> str:
    """
    Upload a profile image to Firebase Storage.
    Returns the public URL. Falls back to local URL in dev environment.
    """
    if not is_firebase_env():
        app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        return f"{app_base_url}/uploads/{filename}"
    try:
        import firebase_admin
        from firebase_admin import storage as fb_storage
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        bucket = fb_storage.bucket()
        storage_path = f"uploads/profiles/{filename}"
        blob = bucket.blob(storage_path)
        blob.upload_from_filename(local_path, content_type="image/jpeg")
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Firebase Storage image upload failed: {e}")
        app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        return f"{app_base_url}/uploads/{filename}"
