"""
Feedback System Module
Handles collecting and storing feedback after world events.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import json
import os
from datetime import datetime
from typing import Any


class FeedbackSystem:
    def __init__(self, storage_dir: str = "feedback"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def submit_feedback(
        self, event_id: str, player_id: str, feedback: dict[str, Any]
    ) -> bool:
        """
        フィードバックを送信し、保存する。
        :param event_id: イベントID
        :param player_id: プレイヤーID
        :param feedback: フィードバックの辞書 (例: {"rating": 5, "comment": "楽しかった"})
        :return: 成功したかどうか
        """
        try:
            feedback_data = {
                "event_id": event_id,
                "player_id": player_id,
                "timestamp": datetime.now().isoformat(),
                "feedback": feedback,
            }
            filename = f"{event_id}_{player_id}_{int(datetime.now().timestamp())}.json"
            filepath = os.path.join(self.storage_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Failed to submit feedback: {e}")
            logger.exception("Unhandled exception")
            return False

    def get_feedback_for_event(self, event_id: str) -> list:
        """
        指定されたイベントのフィードバックを取得する。
        :param event_id: イベントID
        :return: フィードバックのリスト
        """
        feedbacks = []
        if not os.path.exists(self.storage_dir):
            return feedbacks
        for filename in os.listdir(self.storage_dir):
            if filename.startswith(event_id + "_") and filename.endswith(".json"):
                try:
                    with open(
                        os.path.join(self.storage_dir, filename), encoding="utf-8"
                    ) as f:
                        data = json.load(f)
                        feedbacks.append(data)
                except Exception as e:
                    logger.exception("Unhandled exception")
                    print(f"Failed to read feedback file {filename}: {e}")
        return feedbacks

    def get_average_rating(self, event_id: str) -> float | None:
        """
        イベントの平均評価を計算する。
        :param event_id: イベントID
        :return: 平均評価 (1-5) またはNone
        """
        feedbacks = self.get_feedback_for_event(event_id)
        ratings = []
        for fb in feedbacks:
            rating = fb.get("feedback", {}).get("rating")
            if isinstance(rating, (int, float)):
                ratings.append(float(rating))
        if not ratings:
            return None
        return sum(ratings) / len(ratings)


FEEDBACK_SYSTEM = FeedbackSystem()
