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
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        cached = DataCache.get_data(self.config_path)
        if cached is not None:
            return cached
        return {}

    def get(self, key, default=None):
        return self.config.get("settings", {}).get(key, default)
