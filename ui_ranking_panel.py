"""
UI Ranking Panel Module
Provides data for displaying ranking information in the UI.
"""
from __future__ import annotations
from typing import Dict, Any, List
from ranking_manager import RANKING_MANAGER
from world_event_system import REGISTRY

def get_all_event_rankings() -> Dict[str, List[tuple]]:
    """
    すべてのイベントのランキングを取得する。
    :return: {event_id: [(player_id, score), ...]}
    """
    rankings = {}
    for event_id in REGISTRY.all_events().keys():
        rankings[event_id] = RANKING_MANAGER.get_ranking(event_id)
    return rankings

def get_event_ranking(event_id: str, top_n: int = 10) -> List[tuple]:
    """
    指定されたイベントのランキングを取得する。
    :param event_id: イベントID
    :param top_n: 上位何位を取得するか
    :return: ランキングリスト [(player_id, score), ...]
    """
    return RANKING_MANAGER.get_ranking(event_id)[:top_n]

def get_ranking_as_dict(event_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    ランキングを辞書のリストで取得する（UI向け）。
    :param event_id: イベントID
    :param top_n: 上位何位を取得するか
    :return: [{"player_id": str, "score": int}, ...]
    """
    ranking = RANKING_MANAGER.get_ranking(event_id)[:top_n]
    return [{"player_id": pid, "score": score} for pid, score in ranking]