"""
AI Pet Coordination & Formation Engine
Manages pet positioning, tank-and-dps formations, flanking, and divine miracles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.entity import Entity


class PetTacticsCoordinator:
    """Coordinates spatial tactical formations between player and pet."""

    def __init__(self, blackboard: AIBlackboard):
        self.bb = blackboard

    def compute_formation_step(self, target_enemy: Entity) -> tuple[int, int] | None:
        """Position player behind pet if Mage, or lead the vanguard if Melee."""
        engine = self.bb.engine
        player = engine.player
        pet = getattr(engine, "pet", None)

        if not pet or getattr(pet, "hp", 0) <= 0:
            return None

        # If Mage: try to place pet between player and enemy
        if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
            # If pet is adjacent to enemy, retreat to stay behind pet
            pet_dist_to_enemy = max(abs(pet.x - target_enemy.x), abs(pet.y - target_enemy.y))
            player_dist_to_enemy = max(abs(player.x - target_enemy.x), abs(player.y - target_enemy.y))
            if player_dist_to_enemy <= pet_dist_to_enemy:
                # Fall back behind pet
                from naRou.ai_safety_grid import SafetyGridEvaluator
                evaluator = SafetyGridEvaluator(self.bb, radius=4)
                return evaluator.find_tactical_retreat_step()

        return None

    def compute_flanking_step(self, target_enemy: Entity) -> tuple[int, int] | None:
        """Find a position opposing pet relative to enemy (180 deg flank)."""
        engine = self.bb.engine
        player = engine.player
        pet = getattr(engine, "pet", None)

        if not pet or getattr(pet, "hp", 0) <= 0:
            return None

        # Vector from enemy to pet
        dx_enemy_to_pet = pet.x - target_enemy.x
        dy_enemy_to_pet = pet.y - target_enemy.y

        # Ideal flank tile is opposite to pet vector
        ideal_x = target_enemy.x - dx_enemy_to_pet
        ideal_y = target_enemy.y - dy_enemy_to_pet

        # If already near ideal, stay/attack
        if (player.x, player.y) == (ideal_x, ideal_y):
            return None

        # Try to step towards ideal flank
        from naRou.ai_escape import SafePathfinder
        path = SafePathfinder.get_safe_path(self.bb, ideal_x, ideal_y)
        if path and len(path) > 1:
            return (path[1].x - player.x, path[1].y - player.y)

        return None

    def decide_pet_rescue_action(self, target_enemy: Entity) -> tuple[str, Any] | None:
        """Intervene and draw aggro when pet is near death (< 25% HP)."""
        engine = self.bb.engine
        player = engine.player
        pet = getattr(engine, "pet", None)

        if not pet:
            return None

        pet_max_hp = getattr(pet, "max_hp", 100)
        pet_hp = getattr(pet, "hp", 0)
        if pet_hp <= 0 or (pet_hp / max(1, pet_max_hp)) > 0.25:
            return None

        # Attack enemy directly to intercept and kill
        dist_to_enemy = max(abs(player.x - target_enemy.x), abs(player.y - target_enemy.y))
        if dist_to_enemy == 1:
            return ("move", (target_enemy.x - player.x, target_enemy.y - player.y))

        # Close in
        from naRou.ai_escape import SafePathfinder
        path = SafePathfinder.get_safe_path(self.bb, target_enemy.x, target_enemy.y)
        if path and len(path) > 1:
            return ("move", (path[1].x - player.x, path[1].y - player.y))

        return None

    def decide_altar_offering(self) -> tuple[str, Any] | None:
        """Navigate to discovered altar and execute offering."""
        engine = self.bb.engine
        player = engine.player
        altar_pos = self.bb.discovered_altar_pos or getattr(engine, "altar_pos", None)

        if not altar_pos:
            return None

        # Check if offering items exist
        has_items = any(
            any(kw in itm.name for kw in ["肉", "鉱石", "パン", "ハーブ"])
            for itm in engine.inventory.items
        )
        if not has_items:
            return None

        ax, ay = altar_pos
        if player.x == ax and player.y == ay:
            return ("offer_altar", None)

        from naRou.ai_escape import SafePathfinder
        path = SafePathfinder.get_safe_path(self.bb, ax, ay)
        if path and len(path) > 1:
            return ("move", (path[1].x - player.x, path[1].y - player.y))

        return None

    def check_emergency_miracle_prayer(self) -> tuple[str, Any] | None:
        """Trigger divine miracle prayer when in mortal danger and piety is sufficient."""
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        piety = getattr(player, "piety", 0)

        if hp_ratio < 0.25 and piety >= 20:
            return ("pray", None)

        return None

    def support_pet_feeding(self) -> tuple[str, Any] | None:
        """Feed pet surplus meat/food to support growth and loyalty."""
        engine = self.bb.engine
        pet = getattr(engine, "pet", None)

        if not pet or getattr(pet, "hp", 0) <= 0:
            return None

        # Look for surplus meat
        for item in engine.inventory.items:
            if "肉" in item.name and not "腐" in item.name:
                return ("feed_pet", item)

        return None

    def decide_pet_action(self, target_enemy: Entity | None = None) -> tuple[str, Any] | None:
        """Evaluate and return highest priority pet/miracle/altar action."""
        # 1. Miracle prayer in crisis
        miracle = self.check_emergency_miracle_prayer()
        if miracle:
            return miracle

        # 2. Altar offering if safe and standing on/near altar
        if not target_enemy:
            altar_act = self.decide_altar_offering()
            if altar_act:
                return altar_act

        if target_enemy:
            # 3. Intervene if pet is dying
            rescue = self.decide_pet_rescue_action(target_enemy)
            if rescue:
                return rescue

            # 4. Tank/DPS formation positioning
            formation = self.compute_formation_step(target_enemy)
            if formation:
                return ("move", formation)

        return None
