"""
設定ファイル読み込みユーティリティ (config_loader)
複数のYAMLファイルを統合読み込みし、フォールバック機能を提供する。
"""

from __future__ import annotations

import logging
import os
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """複数の設定ファイルを統合読み込みするローダー"""

    def __init__(self, registry: Any = None):
        self.registry = registry

    def load_all(
        self,
        main_path: str,
        fallback_path: str = "",
        pet_path: str = "",
    ) -> dict[str, Any]:
        """
        メイン、フォールバック、ペット用の3つのYAMLを読み込み統合する。

        Args:
            main_path: メイン設定ファイル (procedural_scenarios.yaml)
            fallback_path: フォールバック設定ファイル
            pet_path: ペットクエストテンプレートファイル

        Returns:
            統合された設定辞書
        """
        result: dict[str, Any] = {}

        # 1. メイン設定読み込み
        main_data = self._load_yaml(main_path)
        if main_data:
            result.update(main_data)

        # 2. フォールバック設定読み込み (メインにないキーを補完)
        if fallback_path and os.path.exists(fallback_path):
            fallback_data = self._load_yaml(fallback_path)
            if fallback_data:
                result = self._merge_configs(result, fallback_data)

        # 3. ペットクエストテンプレート読み込み
        if pet_path and os.path.exists(pet_path):
            pet_data = self._load_yaml(pet_path)
            if pet_data:
                result["pet_quest_templates"] = pet_data.get("pet_quest_templates", [])

        return result

    def _load_yaml(self, path: str) -> dict[str, Any] | None:
        """単一YAMLファイルを安全に読み込む"""
        try:
            if not os.path.exists(path):
                logger.debug("Config file not found: %s", path)
                return None
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            logger.info("Loaded config: %s", path)
            return data
        except Exception as e:
            logger.warning("Failed to load config %s: %s", path, e)
            return None

    def _merge_configs(
        self, primary: dict[str, Any], secondary: dict[str, Any]
    ) -> dict[str, Any]:
        """
        2つの設定辞書を深くマージする。
        primary のキーを優先し、secondary のみにあるキーを補完する。
        """
        result = primary.copy()

        for key, value in secondary.items():
            if key not in result:
                result[key] = value
            elif isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = self._merge_configs(result[key], value)
            elif isinstance(value, list) and isinstance(result[key], list):
                # リストの場合は結合（重複除去）
                seen = set()
                merged = []
                for item in result[key] + value:
                    # dict の場合は id で重複判定
                    if isinstance(item, dict) and "id" in item:
                        if item["id"] not in seen:
                            seen.add(item["id"])
                            merged.append(item)
                    else:
                        # 単純値の場合は値で重複判定
                        item_str = str(item)
                        if item_str not in seen:
                            seen.add(item_str)
                            merged.append(item)
                result[key] = merged

        return result