from __future__ import annotations

import logging
import os
from typing import Any

import yaml
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    Fernet = None  # type: ignore
    HAS_CRYPTOGRAPHY = False

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

logger = logging.getLogger(__name__)


class DataCache:
    """YAMLおよび設定データのメモリキャッシュ機構 (Step 9.1)"""

    _cache: dict[str, Any] = {}

    @classmethod
    def get_data(cls, file_path: str) -> Any:
        if file_path in cls._cache:
            return cls._cache[file_path]
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                cls._cache[file_path] = data
                return data
        except FileNotFoundError:
            logger.warning("File not found for DataCache: %s", file_path)
            return None
        except yaml.YAMLError as e:
            logger.error("YAML parsing error in %s: %s", file_path, e)
            return None
        except Exception as e:
            logger.exception("Unexpected error loading %s: %s", file_path, e)
            return None

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()


class ConfigManager:
    """ConfigManager with optional encryption for sensitive settings (Step 66)."""

    _fernet: Any | None = None

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        # Opt-in telemetry flag (proposal #1-B). Default OFF; explicit consent required.
        self.telemetry_enabled = bool(
            self.config.get("settings", {}).get("telemetry_enabled", False)
        )

    @classmethod
    def _get_fernet(cls) -> Any:
        """Return Fernet instance from env key or generate ephemeral (dev)."""
        if not HAS_CRYPTOGRAPHY or Fernet is None:
            return None
        if cls._fernet:
            return cls._fernet
        key_b64 = os.environ.get("CONFIG_ENCRYPTION_KEY")
        if key_b64:
            try:
                cls._fernet = Fernet(key_b64.encode())
            except Exception as e:
                # If key is invalid, ignore and generate dev key
                logger.warning("Failed to initialize Fernet key from CONFIG_ENCRYPTION_KEY: %s", e)
        if not cls._fernet:
            # Dev: ephemeral key (won't persist across restarts)
            cls._fernet = Fernet(Fernet.generate_key())
        return cls._fernet

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a string value."""
        f = self._get_fernet()
        if f is None:
            return value
        return f.encrypt(value.encode()).decode()

    def _decrypt_value(self, token: str) -> str:
        """Decrypt a string value."""
        f = self._get_fernet()
        if f is None:
            return token
        return f.decrypt(token.encode()).decode()

    def set_sensitive(self, key: str, value: str) -> None:
        """Store a sensitive setting encrypted."""
        self.config.setdefault("secure", {})[key] = self._encrypt_value(value)

    def get_sensitive(self, key: str, default: str = "") -> str:
        """Retrieve a sensitive setting (decrypted)."""
        token = self.config.get("secure", {}).get(key)
        if token:
            try:
                return self._decrypt_value(token)
            except Exception as e:
                logger.warning("Failed to decrypt sensitive config for key '%s': %s", key, e)
                return default
        return default

    def _load_config(self) -> dict[str, Any]:
        from data_validation import load_yaml_validated

        try:
            return load_yaml_validated(self.config_path)
        except FileNotFoundError:
            logger.warning("Config file not found: %s", self.config_path)
            return {}
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to load config from %s: %s", self.config_path, e)
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get("settings", {}).get(key, default)

    def get_player_config(self) -> dict[str, Any]:
        """プレイヤー初期設定を取得"""
        return self.config.get("player", {})

    def get_pet_config(self) -> dict[str, Any]:
        """ペット初期設定を取得"""
        return self.config.get("pet", {})

    def get_settings(self) -> dict[str, Any]:
        """全設定を取得"""
        return self.config.get("settings", {})

    def get_telemetry_enabled(self) -> bool:
        """Return whether telemetry is opted-in."""
        return self.telemetry_enabled

    def set_telemetry_enabled(self, value: bool) -> None:
        """Update telemetry opt-in state and persist to settings."""
        self.telemetry_enabled = bool(value)
        self.config.setdefault("settings", {})["telemetry_enabled"] = (
            self.telemetry_enabled
        )


# Pydantic validation model
class ConfigModel(BaseModel):
    settings: dict = {}
    player: dict = {}
    pet: dict = {}

    def validate(self) -> bool:
        try:
            self.__class__(**self.dict())
            return True
        except ValidationError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Config validation error: {e}")
            return False


# グローバルインスタンス
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """グローバル ConfigManager インスタンスを取得"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
