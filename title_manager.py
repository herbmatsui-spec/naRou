"""
Title Manager Module
Handles granting of titles for world events.
"""

from __future__ import annotations

from typing import Any

from entity import Entity


class TitleManager:
    def __init__(self):
        # プレイヤーが保有する称号: {player_id: set_of_title_ids}
        self.player_titles: dict[str, set] = {}

    def check_and_grant_titles(
        self, player: Entity, event_data: Any, stats: dict[str, Any]
    ) -> list[str]:
        """
        イベントデータとプレイヤーの統計情報に基づいて称号を付与し、新規獲得した称号のリストを返す。
        :param player: プレイヤー
        :param event_data: WorldEventDataオブジェクト
        :param stats: プレイヤーのイベント中の統計情報 (e.g., {"points": 1500})
        :return: 新規獲得した称号のタイトル名リスト
        """
        newly_granted = []
        player_id = getattr(
            player, "id", str(id(player))
        )  # プレイヤーIDを取得（仮実装）
        if player_id not in self.player_titles:
            self.player_titles[player_id] = set()

        for title_info in event_data.titles:
            title_id = title_info.get("title", "")  # タイトル名をIDとして使用（簡易版）
            condition = title_info.get("condition", "")
            # 条件の簡易評価（実際にはより複雑な条件評価エンジンが必要）
            if self._evaluate_condition(condition, stats):
                if title_id not in self.player_titles[player_id]:
                    self.player_titles[player_id].add(title_id)
                    newly_granted.append(title_info.get("title", ""))
        return newly_granted

    def _evaluate_condition(self, condition: str, stats: dict[str, Any]) -> bool:
        """
        条件文字列を評価する簡易関数。
        実際には式評価エンジンを使用すべきだが、ここではデモ用に簡易実装。
        例: "points >= 1000"
        """
        # ここでは非常に簡易的な実装を行う
        if "points >=" in condition:
            try:
                threshold = int(condition.split(">=")[1].strip())
                return stats.get("points", 0) >= threshold
            except ValueError:
                return False
        # 他の条件タイプについては実装省略
        return False

    def has_title(self, player: Entity, title_id: str) -> bool:
        """プレイヤーが特定の称号を持っているかをチェック"""
        player_id = getattr(player, "id", str(id(player)))
        return title_id in self.player_titles.get(player_id, set())

    def get_player_titles(self, player: Entity) -> list[str]:
        """プレイヤーが保有する称号のリストを取得"""
        player_id = getattr(player, "id", str(id(player)))
        return list(self.player_titles.get(player_id, set()))


TITLE_MANAGER = TitleManager()
