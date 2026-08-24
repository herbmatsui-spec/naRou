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


class CombatState(AIState):
    """Handles direct melee combat, enemy engagement, and target priority."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # Emergency check
        if hp_ratio < 0.35:
            return "EMERGENCY"

        # Check if any enemy is in visible range
        enemies_near = self._get_visible_enemies(range_=8)
        if not enemies_near:
            self.bb.current_target_enemy = None
            return "EXPLORE"

        # If magic/speed focus and enemy is close, switch to KITE
        if (
            self.bb.strategy_name in ("mage", "speed")
            or self.bb.strategy_params.get("focus") == "magic"
        ):
            dist = max(abs(enemies_near[0].x - player.x), abs(enemies_near[0].y - player.y))
            if dist <= 2:
                self.bb.current_target_enemy = enemies_near[0]
                return "KITE"

        # Check for stalemate loop or stalled loop
        if self.bb.is_stalemate(5):
            if self.bb.discovered_stairs_pos:
                return "DESCEND"
            return "ESCAPE"

        if self.bb.stalled_turns >= 20 or self.bb.is_oscillating():
            return "ESCAPE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player

        enemies_adj = self._get_adjacent_enemies()
        if enemies_adj:
            # If surrounded by multiple enemies during stall/stalemate, try emergency teleport item
            if len(enemies_adj) >= 2 and (self.bb.stalled_turns >= 10 or self.bb.is_stalemate(4)):
                for item in engine.inventory.items:
                    name = getattr(item, "name", "")
                    if any(kw in name for kw in ["テレポート", "願い", "脱出", "跳躍"]):
                        self.bb.stalemate_turns = 0
                        return ("use_item", item)

            # Target Priority: prioritize lowest HP enemy for guaranteed kill
            target = min(enemies_adj, key=lambda e: getattr(e, "hp", 999))
            self.bb.current_target_enemy = target
            dx = target.x - player.x
            dy = target.y - player.y
            return ("move", (dx, dy))

        # Approach nearest visible enemy (with direct Charge if stalemated)
        enemies_near = self._get_visible_enemies(range_=8)
        if enemies_near:
            target = enemies_near[0]
            self.bb.current_target_enemy = target
            self.bb.update_combat_history((target.x, target.y))

            # If enemy is fleeing (dist >= 4) and stairs are known, disengage and go to stairs
            dist_to_enemy = max(abs(target.x - player.x), abs(target.y - player.y))
            if dist_to_enemy >= 4 and self.bb.discovered_stairs_pos:
                sx, sy = self.bb.discovered_stairs_pos
                path_stairs = self._get_path_to(sx, sy)
                if path_stairs and len(path_stairs) > 1:
                    return ("move", (path_stairs[1].x - player.x, path_stairs[1].y - player.y))

            # Direct Charge or Pet Swap if stalemated (only if healthy enough)
            hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
            if self.bb.is_stalemate(3) and hp_ratio > 0.35:
                self.bb.stalemate_turns = 0
                self.bb.stalemate_cooldown = 5
                print(
                    f"[Stalemate Breaker] Initiated direct attack/swap on turn {self.bb.total_turns}"
                )
                pet = getattr(engine, "pet", None)
                if pet and getattr(pet, "hp", 0) > 0:
                    # If pet is adjacent, swap with pet to let pet tank
                    pdist = max(abs(pet.x - player.x), abs(pet.y - player.y))
                    if pdist == 1:
                        return ("move", (pet.x - player.x, pet.y - player.y))

                dx = 1 if target.x > player.x else (-1 if target.x < player.x else 0)
                dy = 1 if target.y > player.y else (-1 if target.y < player.y else 0)
                if engine.game_map.is_walkable(player.x + dx, player.y + dy):
                    return ("move", (dx, dy))

            path = self._get_path_to(target.x, target.y)
            if path and len(path) > 1:
                dx = path[1].x - player.x
                dy = path[1].y - player.y
                return ("move", (dx, dy))

        return ("wait", None)

    def _is_corridor_confrontation(self, enemy: Entity) -> bool:
        """Check if confronting an enemy along a narrow 1-tile wide hallway."""
        engine = self.bb.engine
        player = engine.player
        dist = max(abs(enemy.x - player.x), abs(enemy.y - player.y))
        if dist != 2:
            return False
        walkable_around = sum(
            1
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if engine.game_map.is_walkable(player.x + dx, player.y + dy)
        )
        return walkable_around <= 2

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
        enemies.sort(key=lambda e: max(abs(e.x - player.x), abs(e.y - player.y)))
        return enemies

    def _get_path_to(self, target_x: int, target_y: int):
        engine = self.bb.engine
        blocked = engine.get_blocked_positions()
        distance = max(abs(target_x - engine.player.x), abs(target_y - engine.player.y))
        max_depth = max(40, distance + 10)
        return AStar.get_path(
            Point(engine.player.x, engine.player.y),
            Point(target_x, target_y),
            lambda x, y: engine.is_tile_free(x, y, blocked),
            max_depth=max_depth,
        )


class KiteState(AIState):
    """Maintains distance (kiting), casts ranged spells, and avoids melee lock for squishy classes."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # Emergency check
        if hp_ratio < 0.35:
            return "EMERGENCY"

        enemies_near = self._get_visible_enemies(range_=8)
        if not enemies_near:
            self.bb.current_target_enemy = None
            return "EXPLORE"

        # Check if melee fighter switched into this mistakenly
        if (
            self.bb.strategy_name in ("melee", "tank")
            and self.bb.strategy_params.get("focus") != "magic"
        ):
            return "COMBAT"

        # Check for stalemate loop or stalled loop
        if self.bb.is_stalemate(5):
            if self.bb.discovered_stairs_pos:
                return "DESCEND"
            return "ESCAPE"

        if self.bb.stalled_turns >= 20 or self.bb.is_oscillating():
            return "ESCAPE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player
        kite_dist = self.bb.strategy_params.get("kite_dist", 3)

        enemies_near = self._get_visible_enemies(range_=8)
        if not enemies_near:
            return ("wait", None)

        nearest_enemy = enemies_near[0]
        self.bb.current_target_enemy = nearest_enemy
        dist = max(abs(nearest_enemy.x - player.x), abs(nearest_enemy.y - player.y))

        # If stalemated, stop retreating and fire offensive ranged magic immediately (if in line of sight)
        has_los_to_target = engine.has_los(
            Point(player.x, player.y), Point(nearest_enemy.x, nearest_enemy.y)
        )
        if (self.bb.is_stalemate(3) or self.bb.force_blitz_attack) and has_los_to_target:
            if player.mp >= 10:
                self.bb.stalemate_turns = 0
                return ("cast_fireball", None)

        # If too close (dist < kite_dist), try to retreat away from enemies
        if dist < kite_dist:
            retreat_move = self._find_best_retreat_move(enemies_near)
            if retreat_move:
                self.bb.consecutive_kites += 1
                return ("move", retreat_move)

        # At optimal distance (dist >= kite_dist) or cornered: cast ranged spell if MP available and LOS clear
        if player.mp >= 10 and has_los_to_target:
            return ("cast_fireball", None)

        # Fallback: try offensive blitz item if MP depleted
        blitz_item_act = self._use_blitz_item()
        if blitz_item_act:
            return blitz_item_act

        # If adjacent and no retreat possible, attack in self-defense
        enemies_adj = self._get_adjacent_enemies()
        if enemies_adj:
            target = enemies_adj[0]
            dx = target.x - player.x
            dy = target.y - player.y
            return ("move", (dx, dy))

        return ("wait", None)

    def _use_blitz_item(self) -> tuple[str, Any] | None:
        """Use offensive/tactical item (wands, scrolls) to break stalemate when out of MP."""
        for item in self.bb.engine.inventory.items:
            name = getattr(item, "name", "")
            if any(
                kw in name for kw in ["杖", "ファイア", "ライトニング", "炎", "雷", "巻物", "爆発"]
            ):
                return ("use_item", item)
        return None

    def _find_best_blitz_pass_move(self, enemy: Entity) -> tuple[int, int] | None:
        """Find a diagonal bypass step to slip past a blocking enemy toward stairs/exit."""
        engine = self.bb.engine
        player = engine.player
        target_goal = self.bb.discovered_stairs_pos or (40, 25)

        best_move = None
        best_dist = 999.0

        for dx, dy in [(1, 1), (-1, -1), (1, -1), (-1, 1), (0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = player.x + dx, player.y + dy
            if not engine.game_map.is_walkable(nx, ny) or engine.get_entity_at(nx, ny):
                continue
            if (nx, ny) in self.bb.known_traps:
                continue
            # Ensure candidate tile does not bring us adjacent to enemy if trying to bypass
            dist_to_goal = abs(nx - target_goal[0]) + abs(ny - target_goal[1])
            if dist_to_goal < best_dist:
                best_dist = dist_to_goal
                best_move = (dx, dy)

        return best_move

    def _find_best_retreat_move(self, enemies: list[Entity]) -> tuple[int, int] | None:
        engine = self.bb.engine
        player = engine.player
        best_move = None
        best_score = -999.0

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if not engine.game_map.is_walkable(nx, ny) or engine.get_entity_at(nx, ny):
                continue

            # Calculate min distance to all enemies from candidate position
            min_dist = min(max(abs(e.x - nx), abs(e.y - ny)) for e in enemies)
            # Mobility bonus: check how many open adjacent tiles exist from candidate
            mobility = sum(
                1
                for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                if engine.game_map.is_walkable(nx + ddx, ny + ddy)
            )

            score = min_dist * 10.0 + mobility * 2.0
            if score > best_score:
                best_score = score
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
        enemies.sort(key=lambda e: max(abs(e.x - player.x), abs(e.y - player.y)))
        return enemies
