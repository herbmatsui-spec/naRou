import yaml
import os
from typing import Any, Dict, Optional


class DataCache:
    """YAMLおよび設定データのメモリキャッシュ機構 (Step 9.1)"""
    _cache: Dict[str, Any] = {}

    @classmethod
    def get_data(cls, file_path: str) -> Any:
        if file_path in cls._cache:
            return cls._cache[file_path]
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                cls._cache[file_path] = data
                return data
        except Exception:
            return None

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        cached = DataCache.get_data(self.config_path)
        if cached is not None:
            return cached
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get("settings", {}).get(key, default)

    def get_player_config(self) -> Dict[str, Any]:
        """プレイヤー初期設定を取得"""
        return self.config.get("player", {})

    def get_pet_config(self) -> Dict[str, Any]:
        """ペット初期設定を取得"""
        return self.config.get("pet", {})

    def get_settings(self) -> Dict[str, Any]:
        """全設定を取得"""
        return self.config.get("settings", {})


# グローバルインスタンス
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """グローバル ConfigManager インスタンスを取得"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
