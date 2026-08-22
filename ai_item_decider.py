"""
AI Inventory & Item Autonomous Decision Engine
Manages autonomous item usage: healing potions, safe food consumption, scrolls, rods, and auto-equipping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.item_system import Item


class ItemDecider:
    """Evaluates inventory items and decides autonomous usage/equipping."""

    def __init__(self, blackboard: AIBlackboard):
        self.bb = blackboard

    def find_best_healing_potion(self) -> Item | None:
        """Find the most appropriate healing potion in inventory when HP is critical."""
        engine = self.bb.engine
        player = engine.player

        hp_deficit = player.max_hp - player.hp
        if hp_deficit <= 0:
            return None

        candidates = []
        for item in engine.inventory.items:
            if "治療" in item.name or "ポーション" in item.name:
                candidates.append(item)

        if not candidates:
            return None

        # Return first healing potion available
        return candidates[0]

    def find_best_food_to_eat(self) -> Item | None:
        """Find non-spoiled safe food item when hunger is below 35."""
        engine = self.bb.engine
        hunger = getattr(engine.survival, "hunger", 100)
        if hunger > 35:
            return None

        # Priority keywords for safe food
        safe_keywords = ["パン", "レーション", "乾燥肉", "リンゴ", "肉"]
        for item in engine.inventory.items:
            # Skip spoiled food
            if "腐" in item.name:
                continue
            if any(kw in item.name for kw in safe_keywords):
                return item

        return None

    def find_emergency_teleport_item(self) -> Item | None:
        """Find teleport rod, scroll, or wish rod for emergency evacuation."""
        engine = self.bb.engine
        for item in engine.inventory.items:
            if any(kw in item.name for kw in ["テレポート", "願い"]):
                return item
        return None

    def find_better_equipment(self) -> Item | None:
        """Identify if any inventory weapon/armor is superior to currently equipped gear."""
        engine = self.bb.engine
        player = engine.player

        # Check weapons
        current_power = getattr(player, "power", 0)
        for item in engine.inventory.items:
            item_power = getattr(item, "power", 0)
            if item_power > current_power:
                return item

        # Check armor / defense
        current_def = getattr(player, "defense", 0)
        for item in engine.inventory.items:
            item_def = getattr(item, "defense", 0)
            if item_def > current_def:
                return item

        return None

    def find_status_cure_item(self) -> Item | None:
        """Find antidote / status recovery herb if player suffers from negative status."""
        engine = self.bb.engine
        player = engine.player

        is_poisoned = getattr(player, "is_poisoned", False) or getattr(player, "poison_turns", 0) > 0
        if not is_poisoned:
            return None

        for item in engine.inventory.items:
            if any(kw in item.name for kw in ["解毒", "毒消し", "キュア"]):
                return item

        return None

    def find_combat_scroll(self) -> Item | None:
        """Find offensive or protective scroll during engagement."""
        engine = self.bb.engine
        for item in engine.inventory.items:
            if "巻物" in item.name or "スクロール" in item.name:
                return item
        return None

    def decide_item_action(self) -> tuple[str, Any] | None:
        """Evaluate inventory and return the highest priority item action (or None)."""
        engine = self.bb.engine
        player = engine.player

        # 1. Critical HP: Potion
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        if hp_ratio < 0.40:
            potion = self.find_best_healing_potion()
            if potion:
                return ("use_item", potion)

        # 2. Status ailments: Antidote
        cure = self.find_status_cure_item()
        if cure:
            return ("use_item", cure)

        # 3. Hunger: Safe food
        food = self.find_best_food_to_eat()
        if food:
            return ("eat_food", food)

        # 4. Superior Equipment: Auto-Equip
        better_gear = self.find_better_equipment()
        if better_gear:
            return ("equip_item", better_gear)

        return None
