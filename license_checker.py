#!/usr/bin/env python3
"""License checker (Steps 67-68).

Validates Steam DRM ownership or custom license token.
Designed for offline-first: caches last successful check for 7 days.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

CACHE_FILE = Path("license_cache.json")
CACHE_TTL = 7 * 24 * 3600  # 7 days


class LicenseChecker:
    """Verify license via Steam DRM or custom token."""

    def __init__(self, app_id: str = "", secret: str = ""):
        self.app_id = app_id or os.environ.get("STEAM_APP_ID", "")
        self.secret = secret or os.environ.get("LICENSE_SECRET", "")
        self._cached: dict | None = None

    def validate(self) -> bool:
        """Return True if license is valid (uses cache if recent)."""
        # Check cache first
        cached = self._load_cache()
        if cached and time.time() - cached.get("ts", 0) < CACHE_TTL:
            return cached.get("valid", False)

        # Steam DRM path
        if self.app_id:
            ok = self._check_steam()
            self._save_cache({"valid": ok, "ts": time.time()})
            return ok

        # Custom token path
        if self.secret:
            ok = self._check_token()
            self._save_cache({"valid": ok, "ts": time.time()})
            return ok

        # No license configured -> allow in dev
        return True

    def _check_steam(self) -> bool:
        """Verify ownership via Steam API (requires steamworks SDK or steamcmd)."""
        # In production: use steamworks API or steamcmd + app_info
        # Here we check for Steam environment as a proxy
        return bool(os.environ.get("SteamAppId") or os.environ.get("STEAM_USER"))

    def _check_token(self) -> bool:
        """Verify HMAC-signed license token."""
        token = os.environ.get("LICENSE_TOKEN", "")
        if not token:
            return False
        try:
            payload_b64, sig_b64 = token.rsplit(".", 1)
            payload = base64.urlsafe_b64decode(payload_b64 + "==")
            sig = base64.urlsafe_b64decode(sig_b64 + "==")
            expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).digest()
            return hmac.compare_digest(sig, expected)
        except Exception:
            # TODO: handle exception properly
            return False
            logger.exception("Unhandled exception")

    def _load_cache(self) -> dict | None:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except Exception:
                # TODO: handle exception properly
                logger.exception("Unhandled exception")
                pass
        return None

    def _save_cache(self, data: dict) -> None:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            pass


def get_license_checker() -> LicenseChecker:
    """Factory returning LicenseChecker bound to env config."""
    return LicenseChecker()


if __name__ == "__main__":
    checker = LicenseChecker()
    print("License valid:", checker.validate())
