"""AI behavior state definitions (auto-extracted from naRou/ai_states.py)."""

from __future__ import annotations


from typing import TYPE_CHECKING, Any

from naRou.ai.states.base_state import (
    AIState,
    AStar,
    Point,
    MAP_HEIGHT,
    MAP_WIDTH,
    TILE_STAIRS_DOWN,
)

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.entity import Entity


class EmergencyState(AIState):
    """Executes urgent survival tactics: healing potions, praying, teleporting, or fleeing."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # If HP recovered above 50%, exit emergency
        if hp_ratio >= 0.50:
            enemies_near = self._get_visible_enemies(range_=8)
            if enemies_near:
                if (
                    self.bb.strategy_name in ("mage", "speed")
                    or self.bb.strategy_params.get("focus") == "magic"
                ):
                    return "KITE"
                return "COMBAT"
            return "EXPLORE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player

        # 1. Try to use healing potion
        for item in engine.inventory.items:
            if "治療" in item.name or "ポーション" in item.name:
                return ("use_item", item)

        # 2. Try to pray if piety is sufficient
        if getattr(player, "piety", 0) >= 20:
            return ("pray", None)

        # 3. Try to use teleport rod / scroll
        for item in engine.inventory.items:
            if "テレポート" in item.name or "願い" in item.name:
                return ("use_item", item)

        # 4. Flee away from nearest enemies
        enemies_near = self._get_visible_enemies(range_=6)
        if enemies_near:
            flee_move = self._find_flee_move(enemies_near)
            if flee_move:
                return ("move", flee_move)

        # 5. Desperate attack if adjacent
        enemies_adj = self._get_adjacent_enemies()
        if enemies_adj:
            target = enemies_adj[0]
            return ("move", (target.x - player.x, target.y - player.y))

        return ("wait", None)

    def _find_flee_move(self, enemies: list[Entity]) -> tuple[int, int] | None:
        engine = self.bb.engine
        player = engine.player
        best_move = None
        best_dist = -1

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if not engine.game_map.is_walkable(nx, ny) or engine.get_entity_at(nx, ny):
                continue

            min_dist_to_enemy = min(max(abs(e.x - nx), abs(e.y - ny)) for e in enemies)
            if min_dist_to_enemy > best_dist:
                best_dist = min_dist_to_enemy
                best_move = (dx, dy)

        return best_move

    def _get_adjacent_enemies(self) -> list[Entity]:
        engine = self.bb.engine
        player = engine.player
        adj = []
        for ent in engine.entity_manager.get_living_entities():
            if ent in (player, getattr(engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue
            dist = max(abs(ent.x - player.x), abs(ent.y - player.y))
            if dist == 1:
                adj.append(ent)
        return adj

    def _get_visible_enemies(self, range_: int = 8) -> list[Entity]:
        engine = self.bb.engine
        player = engine.player
        enemies = []
        for ent in engine.entity_manager.get_living_entities():
            if ent in (player, getattr(engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue
            dist = max(abs(ent.x - player.x), abs(ent.y - player.y))
            if dist <= range_ and engine.has_los(Point(player.x, player.y), Point(ent.x, ent.y)):
                enemies.append(ent)
        return enemies


class EscapeState(AIState):
    """Executes multi-tier escape tactics to break free from oscillation loops and dead-ends."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # Critical emergency check
        if hp_ratio < 0.30:
            return "EMERGENCY"

        # Check if agent has successfully broken out of stall
        if self.bb.stalled_turns == 0 and not self.bb.is_oscillating():
            enemies_near = self._get_visible_enemies(range_=6)
            if enemies_near:
                if (
                    self.bb.strategy_name in ("mage", "speed")
                    or self.bb.strategy_params.get("focus") == "magic"
                ):
                    return "KITE"
                return "COMBAT"
            return "EXPLORE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        from naRou.ai_escape import EscapeTactics

        # Level 4: Teleport escape if stall is critical (>= 40 turns)
        if self.bb.stalled_turns >= 40:
            act = EscapeTactics.try_teleport_escape(self.bb)
            if act:
                self.bb.stalled_turns = 0
                return act

        # Level 3: Wall mining escape if blocked (>= 30 turns)
        if self.bb.stalled_turns >= 30:
            mined = EscapeTactics.try_mine_escape(self.bb)
            if mined:
                self.bb.stalled_turns = max(0, self.bb.stalled_turns - 10)
                return ("mine_wall", None)

        # Level 2: Broad BFS escape to unvisited zone (>= 20 turns)
        if self.bb.stalled_turns >= 20:
            move = EscapeTactics.find_broad_escape_path(self.bb)
            if move:
                return ("move", move)

        # Level 1: Unvisited random walk (>= 10 turns)
        move = EscapeTactics.unvisited_random_walk(self.bb)
        if move:
            return ("move", move)

        return ("wait", None)

    def _get_visible_enemies(self, range_: int = 8) -> list[Entity]:
        engine = self.bb.engine
        player = engine.player
        enemies = []
        for ent in engine.entity_manager.get_living_entities():
            if ent in (player, getattr(engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue
            dist = max(abs(ent.x - player.x), abs(ent.y - player.y))
            if dist <= range_ and engine.has_los(Point(player.x, player.y), Point(ent.x, ent.y)):
                enemies.append(ent)
        return enemies
