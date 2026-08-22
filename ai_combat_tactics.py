"""
Advanced Combat Tactics & Kiting Engine
Handles role-specific combat tactics, guaranteed kill priorities, AoE safety, and chokepoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.entity import Entity


class CombatTacticsManager:
    """Orchestrates tactical combat decisions for different agent archetypes."""

    def __init__(self, blackboard: AIBlackboard):
        self.bb = blackboard

    def decide_kite_action(self, target_enemy: Entity) -> tuple[str, Any]:
        """Determine optimal kiting action (retreat to safe tile, or cast ranged spell)."""
        engine = self.bb.engine
        player = engine.player
        kite_dist = self.bb.strategy_params.get("kite_dist", 3)

        dist = max(abs(target_enemy.x - player.x), abs(target_enemy.y - player.y))

        # If too close, retreat using safety grid
        if dist < kite_dist:
            from naRou.ai_safety_grid import SafetyGridEvaluator
            evaluator = SafetyGridEvaluator(self.bb, radius=5)
            step = evaluator.find_tactical_retreat_step()
            if step:
                return ("move", step)

        # At safe distance: cast ranged spell if MP available
        if player.mp >= 10:
            return ("cast_fireball", None)

        # Fallback self-defense melee if adjacent
        if dist == 1:
            return ("move", (target_enemy.x - player.x, target_enemy.y - player.y))

        return ("wait", None)

    def is_aoe_safe(self, target_x: int, target_y: int, radius: int = 2) -> bool:
        """Check if an AoE spell centered at (target_x, target_y) avoids player and pets."""
        engine = self.bb.engine
        player = engine.player

        # Check player distance to blast center
        player_dist = max(abs(player.x - target_x), abs(player.y - target_y))
        if player_dist <= radius:
            return False  # Self-damage hazard

        # Check pet distance to blast center
        pet = getattr(engine, "pet", None)
        if pet and getattr(pet, "hp", 0) > 0:
            pet_dist = max(abs(pet.x - target_x), abs(pet.y - target_y))
            if pet_dist <= radius:
                return False  # Friendly fire hazard

        return True

    def find_chokepoint_retreat(self) -> tuple[int, int] | None:
        """Find a move towards a narrow 1-tile wide hallway to fight enemies 1v1."""
        engine = self.bb.engine
        player = engine.player
        game_map = engine.game_map

        best_move = None
        min_hallway_openness = 99

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if not game_map.is_walkable(nx, ny) or engine.get_entity_at(nx, ny):
                continue

            # Check 4-way openness of candidate tile
            orthogonal_walkable = sum(
                1 for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                if 0 <= nx + ddx < len(game_map.tiles) and 0 <= ny + ddy < len(game_map.tiles[0])
                and game_map.is_walkable(nx + ddx, ny + ddy)
            )

            # Hallway is characterized by 2 walkable neighbors (straight or corner)
            if orthogonal_walkable <= 2:
                if orthogonal_walkable < min_hallway_openness:
                    min_hallway_openness = orthogonal_walkable
                    best_move = (dx, dy)

        return best_move

    def select_guaranteed_kill_target(self, enemies: list[Entity]) -> Entity | None:
        """Prioritize enemies that can be eliminated in 1 hit, or have lowest remaining HP."""
        if not enemies:
            return None

        player = self.bb.engine.player
        player_power = getattr(player, "power", 10)

        # 1. Look for guaranteed 1-hit kill
        for enemy in enemies:
            if getattr(enemy, "hp", 999) <= player_power:
                return enemy

        # 2. Otherwise pick lowest absolute HP enemy
        return min(enemies, key=lambda e: getattr(e, "hp", 999))

    def handle_surrounded_tactics(self, adjacent_enemies: list[Entity]) -> tuple[str, Any] | None:
        """Execute anti-surrounding maneuvers when 3+ enemies are adjacent."""
        if len(adjacent_enemies) < 3:
            return None

        # 1. Try to find an open escape tile leading away from crowd
        from naRou.ai_safety_grid import SafetyGridEvaluator
        evaluator = SafetyGridEvaluator(self.bb, radius=4)
        step = evaluator.find_tactical_retreat_step()
        if step:
            return ("move", step)

        # 2. Otherwise attack the guaranteed kill target
        target = self.select_guaranteed_kill_target(adjacent_enemies)
        if target:
            player = self.bb.engine.player
            return ("move", (target.x - player.x, target.y - player.y))

        return None

    def decide_boss_encounter_action(self, boss_enemy: Entity) -> tuple[str, Any]:
        """Special combat protocols when facing extreme threats (bosses, dragons)."""
        engine = self.bb.engine
        player = engine.player

        # 1. Ensure HP is high (> 80%), use potion if damaged
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        if hp_ratio < 0.80:
            for item in engine.inventory.items:
                if "治療" in item.name or "ポーション" in item.name:
                    return ("use_item", item)

        # 2. If Mage, maintain maximum distance and spell barrage
        if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
            return self.decide_kite_action(boss_enemy)

        # 3. If melee, attack directly
        dist = max(abs(boss_enemy.x - player.x), abs(boss_enemy.y - player.y))
        if dist == 1:
            return ("move", (boss_enemy.x - player.x, boss_enemy.y - player.y))

        # Close in to attack
        from naRou.ai_escape import SafePathfinder
        path = SafePathfinder.get_safe_path(self.bb, boss_enemy.x, boss_enemy.y)
        if path and len(path) > 1:
            return ("move", (path[1].x - player.x, path[1].y - player.y))

        return ("wait", None)

    def decide_combat_action(self, visible_enemies: list[Entity], adjacent_enemies: list[Entity]) -> tuple[str, Any]:
        """Main combat decision pipeline evaluating role, surroundings, threats, and chokepoints."""
        if not visible_enemies:
            return ("wait", None)

        nearest_enemy = visible_enemies[0]

        # 1. Check for extreme boss threats
        from naRou.ai_safety_grid import ThreatTable
        threat = ThreatTable.get_entity_threat_level(nearest_enemy)
        if threat >= 70.0:
            return self.decide_boss_encounter_action(nearest_enemy)

        # 2. Check for surrounding crisis (3+ adjacent hostiles)
        if len(adjacent_enemies) >= 3:
            surrounded_action = self.handle_surrounded_tactics(adjacent_enemies)
            if surrounded_action:
                return surrounded_action

        # 3. Mage/Speed Kiting role
        if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
            return self.decide_kite_action(nearest_enemy)

        # 4. Multi-enemy room: try chokepoint retreat if 2+ enemies visible and in open room
        if len(visible_enemies) >= 2:
            choke_step = self.find_chokepoint_retreat()
            if choke_step:
                return ("move", choke_step)

        # 5. Melee direct attack: select guaranteed kill target if adjacent
        if adjacent_enemies:
            target = self.select_guaranteed_kill_target(adjacent_enemies)
            if target:
                player = self.bb.engine.player
                return ("move", (target.x - player.x, target.y - player.y))

        # 6. Approach nearest enemy using safe path
        from naRou.ai_escape import SafePathfinder
        path = SafePathfinder.get_safe_path(self.bb, nearest_enemy.x, nearest_enemy.y)
        if path and len(path) > 1:
            player = self.bb.engine.player
            return ("move", (path[1].x - player.x, path[1].y - player.y))

        return ("wait", None)
