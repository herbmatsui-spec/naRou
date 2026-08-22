"""
Concrete AI States Implementation
Defines behaviors for Exploration, Combat, Kiting, Rest, Emergency, Descending, etc.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from naRou.ai_state_machine import AIState
from naRou.constants import MAP_HEIGHT, MAP_WIDTH, TILE_STAIRS_DOWN
from naRou.core_framework import AStar, Point

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.entity import Entity


class ExploreState(AIState):
    """Explores the dungeon map, uncovering fog of war and navigating to frontiers."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # Emergency check
        if hp_ratio < 0.35:
            return "EMERGENCY"

        # Check for visible enemies
        enemies_near = self._get_visible_enemies(range_=8)
        if enemies_near:
            self.bb.current_target_enemy = enemies_near[0]
            if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
                return "KITE"
            return "COMBAT"

        # Check if stairs found and exploration is high enough
        if self.bb.discovered_stairs_pos:
            explored_ratio = self._get_explored_ratio()
            if explored_ratio >= 0.65 or self.bb.strategy_params.get("fast_descend", False):
                return "DESCEND"

        # Check for altar
        if self.bb.discovered_altar_pos and self._has_offering_items():
            return "OFFER_PRAY"

        # Check for stalled loop
        if self.bb.stalled_turns >= 20 or self.bb.is_oscillating():
            return "ESCAPE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player

        # Update discovered stairs and altar
        self._scan_features()

        # Find frontier (nearest walkable unexplored neighbor)
        target = self._find_nearest_frontier()
        if target:
            self.bb.current_target_pos = target
            path = self._get_path_to(target[0], target[1])
            if path and len(path) > 1:
                dx = path[1].x - player.x
                dy = path[1].y - player.y
                return ("move", (dx, dy))

        # Fallback: random valid move
        moves = self._get_valid_moves()
        if moves:
            return ("move", random.choice(moves))

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
        enemies.sort(key=lambda e: max(abs(e.x - player.x), abs(e.y - player.y)))
        return enemies

    def _get_explored_ratio(self) -> float:
        game_map = self.bb.engine.game_map
        walkable = 0
        explored_walkable = 0
        for x in range(min(MAP_WIDTH, len(game_map.tiles))):
            for y in range(min(MAP_HEIGHT, len(game_map.tiles[0]))):
                if game_map.is_walkable(x, y):
                    walkable += 1
                    if game_map.explored[x][y]:
                        explored_walkable += 1
        return explored_walkable / max(1, walkable)

    def _has_offering_items(self) -> bool:
        for itm in self.bb.engine.inventory.items:
            if any(kw in itm.name for kw in ["肉", "鉱石", "パン", "ハーブ"]):
                return True
        return False

    def _scan_features(self) -> None:
        engine = self.bb.engine
        player = engine.player
        game_map = engine.game_map

        # Check stairs
        stairs_pos = getattr(game_map, "stairs_down_pos", None)
        if stairs_pos:
            sx, sy = stairs_pos
            if game_map.explored[sx][sy]:
                self.bb.discovered_stairs_pos = stairs_pos

        # Check altar
        altar_pos = getattr(engine, "altar_pos", None)
        if altar_pos:
            ax, ay = altar_pos
            if game_map.explored[ax][ay]:
                self.bb.discovered_altar_pos = altar_pos

    def _find_nearest_frontier(self) -> tuple[int, int] | None:
        engine = self.bb.engine
        player = engine.player
        player_pos = Point(player.x, player.y)
        game_map = engine.game_map

        best = None
        best_dist = 999
        max_x = min(MAP_WIDTH, len(game_map.tiles))
        max_y = min(MAP_HEIGHT, len(game_map.tiles[0]))

        for x in range(1, max_x - 1):
            for y in range(1, max_y - 1):
                if (x, y) in self.bb.dead_end_tiles:
                    continue
                if game_map.explored[x][y] and game_map.is_walkable(x, y):
                    has_unexplored = any(
                        not game_map.explored[x + dx][y + dy]
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                        if 0 <= x + dx < max_x and 0 <= y + dy < max_y
                    )
                    if has_unexplored:
                        dist = player_pos.chebyshev_distance(Point(x, y))
                        if dist < best_dist:
                            best_dist = dist
                            best = (x, y)
                            if dist <= 2:
                                return best
        return best

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

    def _get_valid_moves(self) -> list[tuple[int, int]]:
        engine = self.bb.engine
        player = engine.player
        moves = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if engine.game_map.is_walkable(nx, ny) and not engine.get_entity_at(nx, ny):
                moves.append((dx, dy))
        return moves


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
        if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
            dist = max(abs(enemies_near[0].x - player.x), abs(enemies_near[0].y - player.y))
            if dist <= 2:
                self.bb.current_target_enemy = enemies_near[0]
                return "KITE"

        # Check for stalled loop
        if self.bb.stalled_turns >= 20 or self.bb.is_oscillating():
            return "ESCAPE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player

        enemies_adj = self._get_adjacent_enemies()
        if enemies_adj:
            # Target Priority: prioritize lowest HP enemy for guaranteed kill
            target = min(enemies_adj, key=lambda e: getattr(e, "hp", 999))
            self.bb.current_target_enemy = target
            dx = target.x - player.x
            dy = target.y - player.y
            return ("move", (dx, dy))

        # Approach nearest visible enemy
        enemies_near = self._get_visible_enemies(range_=8)
        if enemies_near:
            target = enemies_near[0]
            self.bb.current_target_enemy = target
            path = self._get_path_to(target.x, target.y)
            if path and len(path) > 1:
                dx = path[1].x - player.x
                dy = path[1].y - player.y
                return ("move", (dx, dy))

        return ("wait", None)

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
        if self.bb.strategy_name in ("melee", "tank") and self.bb.strategy_params.get("focus") != "magic":
            return "COMBAT"

        # Check for stalled loop
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

        # If too close (dist < kite_dist), try to retreat away from enemies
        if dist < kite_dist:
            retreat_move = self._find_best_retreat_move(enemies_near)
            if retreat_move:
                self.bb.consecutive_kites += 1
                return ("move", retreat_move)

        # At optimal distance (dist >= kite_dist) or cornered: cast ranged spell if MP available
        if player.mp >= 10:
            return ("cast_fireball", None)

        # If adjacent and no retreat possible, attack in self-defense
        enemies_adj = self._get_adjacent_enemies()
        if enemies_adj:
            target = enemies_adj[0]
            dx = target.x - player.x
            dy = target.y - player.y
            return ("move", (dx, dy))

        return ("wait", None)

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
                1 for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
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


class RestRecoverState(AIState):
    """Waits in safe zones to naturally regenerate HP when safe and well-fed."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        hunger = getattr(self.bb.engine.survival, "hunger", 100)

        # Visible enemies interrupt rest
        enemies_near = self._get_visible_enemies(range_=8)
        if enemies_near:
            self.bb.current_target_enemy = enemies_near[0]
            if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
                return "KITE"
            return "COMBAT"

        # Fully or sufficiently recovered
        if hp_ratio >= 0.90:
            return "EXPLORE"

        # Hungry: do not waste turns starving
        if hunger < 35:
            return "EXPLORE"

        return None

    def decide_action(self) -> tuple[str, Any]:
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


class EmergencyState(AIState):
    """Executes urgent survival tactics: healing potions, praying, teleporting, or fleeing."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # If HP recovered above 50%, exit emergency
        if hp_ratio >= 0.50:
            enemies_near = self._get_visible_enemies(range_=8)
            if enemies_near:
                if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
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


class DescendState(AIState):
    """Navigates directly to the discovered stairs down and descends to the next dungeon floor."""

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # Critical emergency check
        if hp_ratio < 0.30:
            return "EMERGENCY"

        # If stairs position was lost or cleared, fallback to explore
        if not self.bb.discovered_stairs_pos:
            return "EXPLORE"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player
        stairs_pos = self.bb.discovered_stairs_pos

        if not stairs_pos:
            return ("wait", None)

        sx, sy = stairs_pos
        # If already standing on stairs, execute descend
        if player.x == sx and player.y == sy:
            return ("descend", None)

        # Check for adjacent enemy blocking path
        enemies_adj = self._get_adjacent_enemies()
        if enemies_adj:
            target = enemies_adj[0]
            return ("move", (target.x - player.x, target.y - player.y))

        # Navigate directly to stairs
        path = self._get_path_to(sx, sy)
        if path and len(path) > 1:
            dx = path[1].x - player.x
            dy = path[1].y - player.y
            return ("move", (dx, dy))

        return ("wait", None)

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


class OfferPrayState(AIState):
    """Navigates to the altar and offers surplus items to gain piety."""

    def check_transition(self) -> str | None:
        # Check if offering items are exhausted
        if not self._has_offering_items():
            return "EXPLORE"

        # Check for visible hostile enemies
        enemies_near = self._get_visible_enemies(range_=5)
        if enemies_near:
            self.bb.current_target_enemy = enemies_near[0]
            if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
                return "KITE"
            return "COMBAT"

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player
        altar_pos = self.bb.discovered_altar_pos or getattr(engine, "altar_pos", None)

        if not altar_pos:
            return ("wait", None)

        ax, ay = altar_pos
        # If standing on altar, execute offer_altar
        if player.x == ax and player.y == ay:
            return ("offer_altar", None)

        # Navigate to altar
        path = self._get_path_to(ax, ay)
        if path and len(path) > 1:
            dx = path[1].x - player.x
            dy = path[1].y - player.y
            return ("move", (dx, dy))

        return ("wait", None)

    def _has_offering_items(self) -> bool:
        for itm in self.bb.engine.inventory.items:
            if any(kw in itm.name for kw in ["肉", "鉱石", "パン", "ハーブ"]):
                return True
        return False

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
                if self.bb.strategy_name in ("mage", "speed") or self.bb.strategy_params.get("focus") == "magic":
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
