"""
Firebase Authentication token verification.
Used in production (Firebase Cloud Functions) as an additional auth layer.
In local development, the existing JWT + bcrypt system handles authentication.
"""
import os


def is_firebase_env() -> bool:
    return os.getenv("FIREBASE_CONFIG") is not None or os.getenv("FUNCTION_TARGET") is not None


def verify_firebase_token(id_token_str: str) -> dict:
    """
    Verify a Firebase ID token and return decoded user info.
    Returns None if verification fails or in local dev environment.
    """
    if not is_firebase_env():
        return None  # Local dev: use existing JWT verification
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        decoded_token = fb_auth.verify_id_token(id_token_str)
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "provider": decoded_token.get("firebase", {}).get("sign_in_provider", "password")
        }
    except Exception as e:
        print(f"Firebase token verification failed: {e}")
        return None
