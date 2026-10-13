"""
Reward Manager Module
Handles granting of rewards for world events.
"""

from __future__ import annotations

import random
from typing import Any

from ecs.components.components import EconomyComponent
from ecs.entity import Entity  # Assuming Entity is defined elsewhere
from item_system import Inventory, create_sample_item

# Reward key constants (matching test expectations)
KEY_GOLD = "gold"
KEY_PLATINUM = "platinum"
KEY_EXP = "exp"
KEY_PIETY = "piety"
KEY_FAME = "fame"
KEY_ITEMS = "items"
KEY_ITEM_DROPS = "item_drops"
KEY_ARTIFACT = "artifact"
KEY_SPECIAL_CURRENCY = "special_currency"
KEY_CURRENCY_AMOUNT = "currency_amount"


class RewardManager:
    def __init__(self):
        pass

    def grant_event_rewards(self, player: Entity, event_data: Any, engine: Any = None) -> list[str]:
        """
        イベントに関連する報酬をプレイヤーに付与する。
        :param player: 報酬を受け取るプレイヤー
        :param event_data: WorldEventDataオブジェクト
        :param engine: ログ出力用エンジン (省略可)
        :return: 生成されたログメッセージのリスト
        """
        logs = []
        rewards = event_data.rewards if hasattr(event_data, "rewards") else {}

        def log(msg: str):
            if engine and hasattr(engine, "log"):
                engine.log(msg)
            logs.append(msg)

        # Gold
        if KEY_GOLD in rewards:
            amount = rewards[KEY_GOLD]
            if amount > 0:
                player.gold = getattr(player, "gold", 0) + amount
                log(f"金が{amount}G増加した。")

        # Platinum
        if KEY_PLATINUM in rewards:
            amount = rewards[KEY_PLATINUM]
            if amount > 0:
                player.platinum = getattr(player, "platinum", 0) + amount
                log(f"プラチナが{amount}P増加した。")

        # Experience
        if KEY_EXP in rewards:
            amount = rewards[KEY_EXP]
            if amount > 0:
                player.exp = getattr(player, "exp", 0) + amount
                log(f"経験値が{amount}増加した。")

        # Piety
        if KEY_PIETY in rewards:
            amount = rewards[KEY_PIETY]
            if amount > 0:
                player.piety = getattr(player, "piety", 0) + amount
                log(f"信仰が{amount}増加した。")

        # Fame (faction reputation)
        if KEY_FAME in rewards:
            amount = rewards[KEY_FAME]
            if amount > 0:
                if not hasattr(player, "faction_reputation"):
                    player.faction_reputation = {}
                player.faction_reputation["world"] = player.faction_reputation.get("world", 0) + amount
                log(f"名声が{amount}増加した。")

        # Items (direct item grants)
        if KEY_ITEMS in rewards:
            inv = player.components.get(Inventory) if hasattr(player, "components") else None
            if inv:
                for item_name, count in rewards[KEY_ITEMS].items():
                    for _ in range(count):
                        item = create_sample_item(item_name)
                        if item:
                            ok, _ = inv.add_item(item)
                            if ok:
                                log(f"{item.name} を手に入れた。")
            else:
                log("インベントリがないためアイテムを付与できません。")

        # Item drops (with drop chance)
        if KEY_ITEM_DROPS in rewards:
            inv = player.components.get(Inventory) if hasattr(player, "components") else None
            if inv:
                for item_name, drop_chance in rewards[KEY_ITEM_DROPS].items():
                    if random.random() < drop_chance:
                        item = create_sample_item(item_name)
                        if item:
                            ok, _ = inv.add_item(item)
                            if ok:
                                log(f"{item.name} を手に入れた。")
            else:
                log("インベントリがないためアイテムを付与できません。")

        # Artifact (special named item)
        if KEY_ARTIFACT in rewards:
            inv = player.components.get(Inventory) if hasattr(player, "components") else None
            if inv:
                item_name = rewards[KEY_ARTIFACT]
                item = create_sample_item(item_name)
                if item:
                    ok, _ = inv.add_item(item)
                    if ok:
                        log(f"{item.name} を手に入れた。")
            else:
                log("インベントリがないためアイテムを付与できません。")

        # Legacy special currency
        if KEY_SPECIAL_CURRENCY in rewards:
            currency_id = rewards[KEY_SPECIAL_CURRENCY]
            amount = rewards.get(KEY_CURRENCY_AMOUNT, 100)
            if amount > 0:
                if currency_id == "platinum":
                    player.platinum = getattr(player, "platinum", 0) + amount
                    log(f"プラチナが{amount}P増加した。")
                else:
                    # Unknown currency falls back to gold
                    player.gold = getattr(player, "gold", 0) + amount
                    log(f"金が{amount}G増加した。")

        return logs


REWARD_MANAGER = RewardManager()
