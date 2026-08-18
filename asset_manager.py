"""
Asset Manager Module
Manages assets (images, sounds, stories) for world events.
"""
from __future__ import annotations
import os
from typing import Dict, Optional

class AssetManager:
    def __init__(self, base_path: str = "assets"):
        self.base_path = base_path
        self.event_assets_path = os.path.join(base_path, "events")
        # アセットのキャッシュ
        self._asset_cache: Dict[str, str] = {}

    def get_event_asset_path(self, event_id: str, asset_type: str, asset_name: str) -> Optional[str]:
        """
        イベント固有のアセットパスを取得する。
        :param event_id: イベントID
        :param asset_type: アセットタイプ (例: "image", "sound", "story")
        :param asset_name: アセット名 (ファイル名)
        :return: フルパスまたはNone
        """
        path = os.path.join(self.event_assets_path, event_id, asset_type, asset_name)
        if os.path.exists(path):
            return path
        return None

    def get_event_image_path(self, event_id: str, image_name: str) -> Optional[str]:
        """イベント画像のパスを取得する"""
        return self.get_event_asset_path(event_id, "image", image_name)

    def get_event_sound_path(self, event_id: str, sound_name: str) -> Optional[str]:
        """イベントサウンドのパスを取得する"""
        return self.get_event_asset_path(event_id, "sound", sound_name)

    def get_event_story_path(self, event_id: str, story_name: str) -> Optional[str]:
        """イベントストーリーのパスを取得する"""
        return self.get_event_asset_path(event_id, "story", story_name)

    def list_event_assets(self, event_id: str) -> Dict[str, List[str]]:
        """
        イベントのすべてのアセットをリストする。
        :param event_id: イベントID
        :return: {asset_type: [asset_names, ...]}
        """
        event_dir = os.path.join(self.event_assets_path, event_id)
        if not os.path.isdir(event_dir):
            return {}
        assets = {}
        for asset_type in os.listdir(event_dir):
            type_dir = os.path.join(event_dir, asset_type)
            if os.path.isdir(type_dir):
                assets[asset_type] = [f for f in os.listdir(type_dir) if os.path.isfile(os.path.join(type_dir, f))]
        return assets

ASSET_MANAGER = AssetManager()