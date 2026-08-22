"""
Reward Manager Module
Handles granting of rewards for world events.
"""

from __future__ import annotations

import random
from typing import Any

from ecs.entity import Entity  # Assuming Entity is defined elsewhere


class RewardManager:
    def __init__(self):
        pass

    def grant_event_rewards(self, player: Entity, event_data: Any) -> None:
        """
        イベントに関連する報酬をプレイヤーに付与する。
        :param player: 報酬を受け取るプレイヤー
        :param event_data: WorldEventDataオブジェクト
        """
        # 特別通貨の付与
        if "special_currency" in event_data.rewards:
            currency_id = event_data.rewards["special_currency"]
            amount = event_data.rewards.get("currency_amount", 100)  # デフォルト量
            self._grant_currency(player, currency_id, amount)

        # アイテムドロップ
        if "item_drops" in event_data.rewards:
            for item_id, drop_chance in event_data.rewards["item_drops"].items():
                if random.random() < drop_chance:
                    self._grant_item(player, item_id, 1)

    def _grant_currency(self, player: Entity, currency_id: str, amount: int) -> None:
        """プレイヤーに通貨を付与する（実装は省略）"""
        # TODO: 実際の通貨システムと連携

    def _grant_item(self, player: Entity, item_id: str, quantity: int) -> None:
        """プレイヤーにアイテムを付与する（実装は省略）"""
        # TODO: 実際のアイテムシステムと連携


REWARD_MANAGER = RewardManager()
