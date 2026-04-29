"""
Firestore synchronization layer.
In production (Firebase Cloud Functions), data written to SQLAlchemy is also
mirrored to Firebase Firestore for the production database layer.
In local development, this is a complete no-op.

The 12 Firestore collections mirror the 12 SQLAlchemy models:
users, organizations, attendance, student_attendance, food_cooked,
waste, inventory, predictions, food_feedback, menu, meal_timings, notifications
"""
import os
from datetime import date, datetime


def is_firebase_env() -> bool:
    return os.getenv("FIREBASE_CONFIG") is not None or os.getenv("FUNCTION_TARGET") is not None


def get_firestore_client():
    """Get initialized Firestore client."""
    try:
        import firebase_admin
        from firebase_admin import firestore
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        return firestore.client()
    except Exception as e:
        print(f"Firestore client initialization failed: {e}")
        return None


def _serialize(obj):
    """Serialize Python objects to Firestore-compatible types."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def sync_to_firestore(collection: str, document_id: str, data: dict, org_code: str = None) -> bool:
    """
    Mirror a record to Firestore. All documents include organization_code for multi-tenant isolation.
    Returns True on success, False on failure. Local dev always returns True (no-op).
    """
    if not is_firebase_env():
        return True  # No-op in local development
    try:
        db = get_firestore_client()
        if db is None:
            return False
        serialized = _serialize(data)
        if org_code:
            serialized["organization_code"] = org_code
        db.collection(collection).document(document_id).set(serialized, merge=True)
        return True
    except Exception as e:
        print(f"Firestore sync failed for {collection}/{document_id}: {e}")
        return False


def delete_from_firestore(collection: str, document_id: str) -> bool:
    """Delete a document from Firestore."""
    if not is_firebase_env():
        return True
    try:
        db = get_firestore_client()
        if db is None:
            return False
        db.collection(collection).document(document_id).delete()
        return True
    except Exception as e:
        print(f"Firestore delete failed for {collection}/{document_id}: {e}")
        return False
