"""Cloud save client stub (Step 33).

Defines a minimal async-ready client interface for synchronising encrypted save
files to a remote store (Firebase / Supabase). Conflict resolution defers to the
existing ``SaveSystem`` migration layer. Real backend wiring is added later.

Usage:
    from cloud_save.client import CloudSaveClient
    client = CloudSaveClient(base_url="https://api.example.com")
    await client.push("player1", b"<encrypted-bytes>")
"""

from __future__ import annotations

import abc
import os


class CloudSaveClient(abc.ABC):
    """Abstract cloud save backend. Implementations talk to a real provider."""

    def __init__(self, base_url: str = "", api_key: str = "") -> None:
        self.base_url = base_url or os.environ.get("CLOUD_SAVE_URL", "")
        self.api_key = api_key or os.environ.get("CLOUD_SAVE_KEY", "")

    @abc.abstractmethod
    def push(self, user_id: str, payload: bytes) -> bool:
        """Upload encrypted save payload for *user_id*."""

    @abc.abstractmethod
    def pull(self, user_id: str) -> bytes | None:
        """Download encrypted save payload for *user_id* or None."""

    @abc.abstractmethod
    def delete(self, user_id: str) -> bool:
        """Permanently remove a user's cloud data (GDPR request)."""


class LocalCloudSaveClient(CloudSaveClient):
    """Development stub that stores blobs under ``cloud_save/.data``."""

    def __init__(self, base_url: str = "", api_key: str = "") -> None:
        super().__init__(base_url, api_key)
        self.root = os.path.join(os.path.dirname(__file__), ".data")
        os.makedirs(self.root, exist_ok=True)

    def push(self, user_id: str, payload: bytes) -> bool:
        path = os.path.join(self.root, f"{user_id}.save")
        with open(path, "wb") as fh:
            fh.write(payload)
        return True

    def pull(self, user_id: str) -> bytes | None:
        path = os.path.join(self.root, f"{user_id}.save")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()

    def delete(self, user_id: str) -> bool:
        path = os.path.join(self.root, f"{user_id}.save")
        if os.path.exists(path):
            os.remove(path)
        return True


def get_client(kind: str = "local") -> CloudSaveClient:
    """Factory returning the configured client (local for dev)."""
    if kind == "local":
        return LocalCloudSaveClient()
    raise ValueError(f"Unknown cloud save backend: {kind}")
