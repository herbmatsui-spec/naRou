"""
Balance Tool Module
Provides tools for balancing world events based on collected data.
"""

from __future__ import annotations

from typing import Any

from community_goal_manager import COMMUNITY_GOAL_MANAGER
from feedback_system import FEEDBACK_SYSTEM
from world_event_system import RANKING_MANAGER, REGISTRY


class BalanceTool:
    def __init__(self):
        pass

    def get_event_statistics(self, event_id: str) -> dict[str, Any]:
        """
        イベントの統計情報を取得する。
        :param event_id: イベントID
        :return: 統計情報の辞書
        """
        event_data = REGISTRY.get(event_id)
        if not event_data:
            return {}

        stats = {
            "event_id": event_id,
            "event_name": event_data.name,
            "participant_count": 0,  # プレイヤー参加数 (ランキングにエントリーがあるプレイヤー数)
            "average_score": 0.0,
            "total_points_awarded": 0,
            "feedback_count": 0,
            "average_rating": None,
            "goal_achieved": False,
            "goal_progress": 0,
            "goal_target": 0,
        }

        # ランキングから参加数と平均スコアを計算
        ranking = RANKING_MANAGER.get_ranking(event_id)
        if ranking:
            stats["participant_count"] = len(ranking)
            total_score = sum(score for _, score in ranking)
            stats["average_score"] = total_score / len(ranking) if ranking else 0
            stats["total_points_awarded"] = total_score

        # フィードバック情報
        stats["feedback_count"] = len(FEEDBACK_SYSTEM.get_feedback_for_event(event_id))
        stats["average_rating"] = FEEDBACK_SYSTEM.get_average_rating(event_id)

        # コミュニティゴール情報
        if hasattr(event_data, "community_goal") and event_data.community_goal:
            goal_type = event_data.community_goal.get("type")
            if goal_type == "total_points":
                stats["goal_progress"] = COMMUNITY_GOAL_MANAGER.get_progress(event_id, goal_type)
                stats["goal_target"] = event_data.community_goal.get("target", 0)
                stats["goal_achieved"] = COMMUNITY_GOAL_MANAGER.is_goal_achieved(event_id)

        return stats

    def suggest_adjustments(self, event_id: str) -> dict[str, Any]:
        """
        イベントのバランス調整を提案する。
        :param event_id: イベントID
        :return: 調整提案の辞書
        """
        stats = self.get_event_statistics(event_id)
        suggestions = {}

        # 参加率に基づく調整
        if stats["participant_count"] < 5:
            suggestions["trigger_chance"] = "increase"  # 参加者が少なければ発生確率を上げる
        elif stats["participant_count"] > 50:
            suggestions["trigger_chance"] = "decrease"

        # 評価に基づく調整
        avg_rating = stats["average_rating"]
        if avg_rating is not None:
            if avg_rating < 3.0:
                suggestions["rewards"] = "increase"  # 評価が低ければ報酬を増やす
                suggestions["difficulty"] = "decrease"
            elif avg_rating > 4.0:
                suggestions["rewards"] = "decrease"  # 評価が高ければ報酬を減らしてもよい
                suggestions["difficulty"] = "increase"

        # ゴール達成率に基づく調整
        if stats.get("goal_achieved") is False and stats.get("goal_target", 0) > 0:
            progress = stats.get("goal_progress", 0)
            target = stats.get("goal_target", 0)
            if target > 0:
                ratio = progress / target
                if ratio < 0.5:
                    suggestions["goal_target"] = (
                        "decrease"  # ゴールが達成されにくければ目標を下げる
                    )
                elif ratio > 1.5:
                    suggestions["goal_target"] = "increase"

        return suggestions

    def apply_adjustments(self, event_id: str, adjustments: dict[str, Any]) -> bool:
        """
        提案された調整をイベントデータに適用する（実際にはYAMLファイルを更新する必要がある）。
        :param event_id: イベントID
        :param adjustments: 調整の辞書
        :return: 成功したかどうか
        """
        # ここではプレースホルダー：実際にはworld_events.yamlを読み書きする必要がある
        print(f"Adjustments for {event_id}: {adjustments}")
        # 実際の実装では、YAMLファイルをパースし、該当イベントのパラメータを更新し、ファイルに書き戻す
        return True


BALANCE_TOOL = BalanceTool()
