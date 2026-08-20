"""
UI Event Panel Module
Provides data for displaying event information in the UI.
"""

from __future__ import annotations

from typing import Any

from entity import Entity  # For type hinting
from ranking_manager import RANKING_MANAGER
from title_manager import TITLE_MANAGER
from world_event_system import EVENT_SCHEDULER


def get_current_event_info(current_turn: int) -> dict[str, Any]:
    """
    現在のアクティブイベント情報を取得する。
    :param current_turn: 現在のターン数
    :return: イベント情報の辞書
    """
    event_data = EVENT_SCHEDULER.get_current_seasonal_event(current_turn)
    if not event_data:
        return {"active": False}

    # イベントの残りターンを計算（簡易実装）
    remaining_turns = 0
    if hasattr(event_data, "end_turn") and event_data.end_turn is not None:
        remaining_turns = max(0, event_data.end_turn - current_turn)
    elif hasattr(event_data, "duration"):
        # ダURATIONから推定（実際には開始ターンが必要）
        remaining_turns = event_data.duration  # プレースホルダー

    return {
        "active": True,
        "id": event_data.id,
        "name": event_data.name,
        "description": event_data.description,
        "remaining_turns": remaining_turns,
        "quarter": getattr(event_data, "quarter", None),
        "effects": event_data.effects,
    }


def get_event_ranking(event_id: str, top_n: int = 10) -> list:
    """
    指定されたイベントのランキングを取得する。
    :param event_id: イベントID
    :param top_n: 上位何位を取得するか
    :return: ランキングリスト [(player_id, score), ...]
    """
    return RANKING_MANAGER.get_ranking(event_id)[:top_n]


def get_player_event_score(event_id: str, player_id: str) -> int:
    """
    プレイヤーの指定イベントにおけるスコアを取得する。
    :param event_id: イベントID
    :param player_id: プレイヤーID
    :return: スコア
    """
    return RANKING_MANAGER.get_player_score(event_id, player_id)


def get_player_event_titles(player: Entity, event_data: Any) -> list:
    """
    プレイヤーが獲得したイベント固有の称号を取得する。
    :param player: プレイヤーエンティティ
    :param event_data: WorldEventDataオブジェクト
    :return: 称号リスト
    """
    # ここでは簡易的に、プレイヤーの統計がないため空リストを返す
    # 実際には、プレイヤーのイベント統計を渡す必要がある
    return TITLE_MANAGER.get_player_titles(player)
