"""GodInfo: deity definitions with YAML + JSON fallback support.

Extracted from entity.py (Steps 83-88).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GodInfo:
    """神々の定義 (ステップ83〜88, 外部YAMLデータ連携 & JSONフォールバック)"""

    _cached_fallback: dict[str, Any] | None = None

    @classmethod
    def get_fallback_gods(cls) -> dict[str, Any]:
        """フォールバック用神データを外部JSONからロード (Steps 27-31)"""
        if cls._cached_fallback is not None:
            return cls._cached_fallback
        json_path = Path(__file__).resolve().parent / "data" / "gods_fallback.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    cls._cached_fallback = json.load(f)
                    return cls._cached_fallback
            except Exception as e:
                logger.warning("Failed to load gods_fallback.json: %s", e)
        cls._cached_fallback = {}
        return cls._cached_fallback

    @classmethod
    def get_all(cls) -> dict[str, Any]:
        from data_validation import load_yaml_validated

        try:
            data = load_yaml_validated("data/gods.yaml")
        except FileNotFoundError:
            data = None
        if data and isinstance(data, dict):
            return data
        return cls.get_fallback_gods()

    class _GodDict(dict):
        def __getitem__(self, key):
            return GodInfo.get_all().get(key, GodInfo.get_fallback_gods().get(key))

        def get(self, key, default=None):
            return GodInfo.get_all().get(key, default)

        def keys(self):
            return GodInfo.get_all().keys()

        def values(self):
            return GodInfo.get_all().values()

        def items(self):
            return GodInfo.get_all().items()

        def __contains__(self, key):
            return key in GodInfo.get_all()


GodInfo.GODS = GodInfo._GodDict()
