"""
Ranking Manager Module
Handles ranking calculations and rewards for world events.
"""
from __future__ import annotations
from typing import Dict, List, Any

class RankingManager:
    def __init__(self):
        # ランキングデータ: {event_id: {player_id: score}}
        self.rankings: Dict[str, Dict[str, int]] = {}

    def add_points(self, event_id: str, player_id: str, points: int) -> None:
        """指定されたイベントとプレイヤーにポイントを加算する"""
        if event_id not in self.rankings:
            self.rankings[event_id] = {}
        self.rankings[event_id][player_id] = self.rankings[event_id].get(player_id, 0) + points

    def calculate_points(self, event_data: Any, action_type: str, amount: int = 1) -> int:
        """
        イベントデータとアクションタイプからポイントを計算する。
        :param event_data: WorldEventDataオブジェクト
        :param action_type: アクションタイプ（例: "alien_soldier"）
        :param amount: アクションの数（デフォルト1）
        :return: 計算されたポイント
        """
        if not hasattr(event_data, 'rankings') or not event_data.rankings:
            return 0
        point_sources = event_data.rankings.get("point_sources", {})
        points_per_action = point_sources.get(action_type, 0)
        return points_per_action * amount

    def add_points_from_action(self, event_id: str, player_id: str, event_data: Any, action_type: str, amount: int = 1) -> None:
        """イベントデータとアクションからポイントを計算して加算する"""
        points = self.calculate_points(event_data, action_type, amount)
        if points > 0:
            self.add_points(event_id, player_id, points)

    def get_ranking(self, event_id: str) -> List[tuple]:
        """指定されたイベントのランキングをポイントの降順で返す"""
        if event_id not in self.rankings:
            return []
        # (player_id, score) のタプルのリストをスコア降順でソート
        return sorted(self.rankings[event_id].items(), key=lambda x: x[1], reverse=True)

    def get_player_score(self, event_id: str, player_id: str) -> int:
        """プレイヤーの指定イベントにおける現在のスコアを取得"""
        return self.rankings.get(event_id, {}).get(player_id, 0)

def clear_event_ranking(self, event_id: str) -> None:
        """イベント終了時にランキングデータをクリア"""
        if event_id in self.rankings:
            del self.rankings[event_id]


# グローバルインスタンス（エラー回避のため追加）
RANKING_MANAGER = RankingManager()