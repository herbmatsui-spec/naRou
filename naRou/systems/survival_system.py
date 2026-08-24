"""Survival system: hunger, sleep, karma, ether disease."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
    from naRou.item_system import Item

from .combat_core import STATUS_POISON, StatusEffect


class SurvivalSystem:
    """サバイバル・空腹・信仰・カルマ・エーテル病"""

    def __init__(self):
        self.hunger = 8000
        self.sleepiness = 0
        self.karma = 20
        self.gold = 500
        self.platinum = 5
        self.ether_disease = 0
        self.mutations: list[str] = []
        self.god = "なし"
        self.piety = 0
        self.tax_pending = 0  # 未払い税金

    def pass_turn(self, player: Entity) -> list[str]:
        logs = []
        self.hunger -= 1
        self.sleepiness += 1
        if self.hunger <= 0:
            self.hunger = 0
            player.hp -= 2
            logs.append("★飢えが体を蝕んでいる！(-2 HP)")
        elif self.hunger < 1000:
            if random.random() < 0.1:
                logs.append("空腹で倒れそうだ…何か食べないと。")
        return logs

    def eat(self, player: Entity, food_item: Item) -> list[str]:
        logs = []
        is_rotten = "腐った" in food_item.name
        self.hunger = min(10000, self.hunger + food_item.nutrition)
        if is_rotten:
            logs.append(f"腐った {food_item.name} を食べた！ 激しい吐き気に襲われる！")
            # 猛毒付与
            if not hasattr(player, "status_effects"):
                player.status_effects = []
            player.status_effects.append(StatusEffect(STATUS_POISON, 1500, power=4))
        else:
            logs.append(f"{player.name}は {food_item.name} を食べた。")
            if food_item.nutrition > 2000:
                player.attributes.strength += 1
                player.recalculate_stats()
                logs.append("力がみなぎってきた！(筋力+1)")
        return logs

    def sleep(self, player: Entity) -> list[str]:
        self.sleepiness = 0
        player.hp = player.max_hp
        player.mp = player.max_mp
        player.stamina = player.max_stamina
        return ["ぐっすり眠った。HP・MP・スタミナが全快した！"]
