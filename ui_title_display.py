"""
UI Title Display Module
Provides data for displaying title information in the UI.
"""

from __future__ import annotations

from typing import Any

from entity import Entity
from title_manager import TITLE_MANAGER


def get_player_titles(player: Entity) -> list[dict[str, Any]]:
    """
    プレイヤーが保有する称号の詳細情報を取得する。
    :param player: プレイヤーエンティティ
    :return: [{"title": str, "description": str, "event_id": str}, ...]
    """
    # ここでは簡易実装：実際には称号に関連するイベントや説明を保持する必要がある
    title_ids = TITLE_MANAGER.get_player_titles(player)
    # タイトルIDから詳細を取得するためには、イベントデータを参照する必要がある
    # ここではプレースホルダーとしてタイトルIDのみを返す
    return [{"title": tid, "description": "", "event_id": ""} for tid in title_ids]


def get_player_event_titles(player: Entity, event_data: Any) -> list[dict[str, Any]]:
    """
    プレイヤーが特定イベントで獲得した称号を取得する。
    :param player: プレイヤーエンティティ
    :param event_data: WorldEventDataオブジェクト
    :return: [{"title": str, "description": str}, ...]
    """
    newly_granted = TITLE_MANAGER.check_and_grant_titles(player, event_data, {})  # statsは仮
    # 実際には、イベントデータから称号の説明を取得する
    return [{"title": title, "description": ""} for title in newly_granted]
