"""
Community Goal Manager Module
Handles community goals and rewards for world events.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from entity import Entity  # For type hinting

class CommunityGoalManager:
    def __init__(self):
        # コミュニティゴールの状態: {event_id: {goal_type: current_value}}
        self.community_progress: Dict[str, Dict[str, int]] = {}
        # ゴールが達成されたかどうかのフラグ: {event_id: bool}
        self.goal_achieved: Dict[str, bool] = {}

    def add_progress(self, event_id: str, goal_type: str, amount: int = 1) -> bool:
        """
        コミュニティゴールに進捗を追加し、ゴール達成時にはTrueを返す。
        :param event_id: イベントID
        :param goal_type: ゴールタイプ (例: "total_points", "total_items")
        :param amount: 加算する量
        :return: ゴールが今回の追加で達成されたかどうか
        """
        if event_id not in self.community_progress:
            self.community_progress[event_id] = {}
        current = self.community_progress[event_id].get(goal_type, 0)
        new_value = current + amount
        self.community_progress[event_id][goal_type] = new_value

        # ゴール目標を取得
        from world_event_system import REGISTRY
        event_data = REGISTRY.get(event_id)
        if not event_data or not hasattr(event_data, 'community_goal'):
            return False
        goal_info = event_data.community_goal
        if goal_info.get("type") != goal_type:
            return False
        target = goal_info.get("target", 0)
        if new_value >= target and not self.goal_achieved.get(event_id, False):
            self.goal_achieved[event_id] = True
            return True
        return False

    def is_goal_achieved(self, event_id: str) -> bool:
        """ゴールが達成されているかを確認する"""
        return self.goal_achieved.get(event_id, False)

    def get_progress(self, event_id: str, goal_type: str) -> int:
        """現在の進捗値を取得する"""
        return self.community_progress.get(event_id, {}).get(goal_type, 0)

    def get_goal_reward(self, event_id: str) -> Any:
        """達成時の報酬を取得する"""
        from world_event_system import REGISTRY
        event_data = REGISTRY.get(event_id)
        if event_data and hasattr(event_data, 'community_goal'):
            return event_data.community_goal.get("reward")
        return None

    def reset_event(self, event_id: str) -> None:
        """イベント終了時に進捗とフラグをリセット"""
        if event_id in self.community_progress:
            del self.community_progress[event_id]
        if event_id in self.goal_achieved:
            del self.goal_achieved[event_id]


COMMUNITY_GOAL_MANAGER = CommunityGoalManager()