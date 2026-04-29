"""
Firebase Realtime Database integration for meal timing broadcasts.
Used in production alongside the existing WebSocket manager.
In local development, this is a no-op. The WebSocket manager handles local real-time.
"""
import os


def is_firebase_env() -> bool:
    return os.getenv("FIREBASE_CONFIG") is not None or os.getenv("FUNCTION_TARGET") is not None


def broadcast_meal_timing_update(timing_data: dict) -> bool:
    """
    Write meal timing update to Firebase Realtime Database /meal-timings node.
    Connected React clients listening via onValue() will receive this instantly.
    In local dev, the WebSocket manager handles real-time — this is a no-op.
    """
    if not is_firebase_env():
        return True  # Local: WebSocket handles this, nothing to do here
    try:
        import firebase_admin
        from firebase_admin import db as rtdb
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        ref = rtdb.reference("/meal-timings")
        ref.set(timing_data)
        return True
    except Exception as e:
        print(f"Firebase Realtime Database write failed: {e}")
        return False
