import json
import os
from functools import lru_cache
from typing import Any, Dict

import firebase_admin
from firebase_admin import auth as fb_auth, credentials


class AuthService:
    """
    Firebase Admin wrapper to verify Firebase ID tokens.

    Initialization strategy:
    - If FIREBASE_CREDENTIALS_JSON is set (raw JSON or base64): use it.
    - Else if GOOGLE_APPLICATION_CREDENTIALS path is set and exists: use it.
    - Else: initialize with default credentials (will work on GCP environments).

    Env flags:
    - FIREBASE_CHECK_REVOKED: "true"/"false" whether to check revoked tokens (default false)
    """

    def __init__(self) -> None:
        self._ensure_initialized()
        self.check_revoked = os.getenv("FIREBASE_CHECK_REVOKED", "false").lower() in ("1", "true", "yes", "on")

    @staticmethod
    def _ensure_initialized() -> None:
        if firebase_admin._apps:  # already initialized
            return

        # Try base64-encoded JSON from env
        cred_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
        if cred_base64:
            try:
                import base64
                cred_json = base64.b64decode(cred_base64).decode("utf-8")
                data = json.loads(cred_json)
                cred = credentials.Certificate(data)
                firebase_admin.initialize_app(cred)
                return
            except Exception:
                # Fallback to other methods
                pass

        # Try file path from GOOGLE_APPLICATION_CREDENTIALS
        path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if path and os.path.isfile(path):
            cred = credentials.Certificate(path)
            firebase_admin.initialize_app(cred)
            return

        # Fallback: default credentials (GCP runtime)
        firebase_admin.initialize_app()

    @lru_cache(maxsize=1024)
    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify the Firebase ID token and return decoded claims.
        We enable simple LRU caching to avoid repeated verification of the same token during bursts.
        """
        decoded = fb_auth.verify_id_token(id_token, check_revoked=self.check_revoked)
        return decoded


