import os

import pytest

# The save HMAC key is now mandatory (save_system.SaveSystem._get_hmac_key).
# Provide a fixed test-only key so the existing save/load suite keeps running
# without depending on a real deployment secret. This key is never used outside
# the test suite.
_TEST_SAVE_HMAC_KEY = "I/o21oUqC6AWwBUVSFBsMhYrz/nr3i3yO3+gJplnUm4="


@pytest.fixture(autouse=True)
def _require_save_hmac_key(monkeypatch):
    monkeypatch.setenv("SAVE_HMAC_KEY", _TEST_SAVE_HMAC_KEY)
