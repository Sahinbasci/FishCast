"""FishCast Firebase service.

Firebase Admin SDK initialization, Firestore client, Auth token verification.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_firestore_client: Any = None
_initialized = False


def initialize_firebase() -> None:
    """Firebase Admin SDK'yı initialize eder.

    GOOGLE_APPLICATION_CREDENTIALS env var veya default credentials kullanır.
    Production'da Cloud Run service account otomatik auth sağlar.
    """
    global _initialized
    if _initialized:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check for explicit credentials file
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            # Use default credentials (Cloud Run, local gcloud auth)
            try:
                firebase_admin.initialize_app()
            except ValueError:
                # Already initialized
                pass

        _initialized = True
        logger.info("Firebase Admin SDK initialized")
    except Exception as e:
        logger.warning("Firebase initialization failed: %s — running without Firebase", e)
        _initialized = False


def get_firestore_db() -> Any:
    """Firestore client döner.

    Returns:
        Firestore client veya None (Firebase yoksa).
    """
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    if not _initialized:
        initialize_firebase()

    try:
        from firebase_admin import firestore
        _firestore_client = firestore.client()
        return _firestore_client
    except Exception as e:
        logger.warning("Firestore client oluşturulamadı: %s", e)
        return None


async def verify_firebase_token(token: str) -> Optional[dict[str, Any]]:
    """Firebase Auth token'ı doğrular.

    Uses check_revoked=True to reject revoked tokens.
    Catches specific Firebase Auth exceptions for clear logging.

    Args:
        token: Firebase ID token (Bearer token'dan parsed).

    Returns:
        Decoded token dict (uid, email, etc.) veya None (geçersizse).
    """
    if not _initialized:
        initialize_firebase()

    try:
        from firebase_admin import auth
        # D2: Run sync verify_id_token in thread pool to avoid blocking event loop
        decoded = await asyncio.to_thread(auth.verify_id_token, token, check_revoked=True)
        return decoded
    except Exception as e:
        # Categorize error for clear logging
        err_type = type(e).__name__
        if "ExpiredIdTokenError" in err_type:
            logger.warning("Token suresi dolmus")
        elif "RevokedIdTokenError" in err_type:
            logger.warning("Token iptal edilmis")
        elif "InvalidIdTokenError" in err_type or "CertificateFetchError" in err_type:
            logger.warning("Gecersiz token formati: %s", err_type)
        else:
            logger.warning("Token dogrulama hatasi: %s — %s", err_type, e)
        return None


async def get_auth_user(authorization: Optional[str]) -> Optional[dict[str, Any]]:
    """Authorization header'dan kullanıcı bilgisi çıkarır.

    Args:
        authorization: "Bearer <token>" formatında header değeri.

    Returns:
        Decoded token dict veya None.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    return await verify_firebase_token(token)
