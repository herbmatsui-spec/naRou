"""AI behavior state definitions (auto-extracted from naRou/ai_states.py)."""

from __future__ import annotations

import random

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
        explored_ratio = self._get_explored_ratio()
        floor_turns = self.bb.total_turns - self.bb.floor_start_turn
        is_rush_mode = explored_ratio >= 0.50 or floor_turns >= 70

        if enemies_near:
            nearest_dist = max(abs(enemies_near[0].x - player.x), abs(enemies_near[0].y - player.y))
            # In Rush Mode, bypass non-adjacent mobs to avoid infinite mob farm loops
            if not is_rush_mode or nearest_dist <= 1 or not self.bb.discovered_stairs_pos:
                self.bb.current_target_enemy = enemies_near[0]
                if (
                    self.bb.strategy_name in ("mage", "speed")
                    or self.bb.strategy_params.get("focus") == "magic"
                ):
                    return "KITE"
                return "COMBAT"

        # Proactively scan for stairs and altars
        self._scan_features()

        # Goal-oriented: Descend when stairs are discovered AND floor exploration threshold met (or max floor turns reached)
        target_ratio = self.bb.strategy_params.get("target_explore_ratio", 0.50)
        max_floor_turns = self.bb.strategy_params.get("max_floor_turns", 130)
        if self.bb.discovered_stairs_pos and (
            explored_ratio >= target_ratio or floor_turns >= max_floor_turns
        ):
            return "DESCEND"

        # Check for altar
        if self.bb.discovered_altar_pos and self._has_offering_items():
            return "OFFER_PRAY"

        # Check for stalled loop
        if self.bb.stalled_turns >= 20 or self.bb.is_oscillating():
            return "ESCAPE"

        # Long floor stay check for secret door probing
        if floor_turns > 80 and not self.bb.discovered_stairs_pos:
            pass

        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        player = engine.player
        explored_ratio = self._get_explored_ratio()
        floor_turns = self.bb.total_turns - self.bb.floor_start_turn
        is_rush_mode = explored_ratio >= 0.50 or floor_turns >= 70

        # Check for immediate visible enemy interruption
        enemies_near = self._get_visible_enemies(range_=8)
        if enemies_near:
            self.bb.current_target_enemy = enemies_near[0]
            # If adjacent, attack
            enemies_adj = [
                e for e in enemies_near if max(abs(e.x - player.x), abs(e.y - player.y)) == 1
            ]
            if enemies_adj:
                target = min(enemies_adj, key=lambda e: getattr(e, "hp", 999))
                return ("move", (target.x - player.x, target.y - player.y))
            # In non-rush mode or before stairs found, approach enemy
            if not is_rush_mode or not self.bb.discovered_stairs_pos:
                path = self._get_path_to(enemies_near[0].x, enemies_near[0].y)
                if path and len(path) > 1:
                    return ("move", (path[1].x - player.x, path[1].y - player.y))

        # Update discovered stairs and altar
        self._scan_features()

        # Descend interrupt if stairs are discovered AND floor exploration threshold met
        target_ratio = self.bb.strategy_params.get("target_explore_ratio", 0.50)
        max_floor_turns = self.bb.strategy_params.get("max_floor_turns", 130)
        explored_ratio = self._get_explored_ratio()
        floor_turns = self.bb.total_turns - self.bb.floor_start_turn
        if self.bb.discovered_stairs_pos and (
            explored_ratio >= target_ratio or floor_turns >= max_floor_turns
        ):
            sx, sy = self.bb.discovered_stairs_pos
            if player.x == sx and player.y == sy:
                return ("descend", None)
            path = self._get_path_to(sx, sy)
            if path and len(path) > 1:
                return ("move", (path[1].x - player.x, path[1].y - player.y))

        # Long-stay secret door / wall probing branch
        if self.bb.last_mined_pos and engine.game_map.is_walkable(
            self.bb.last_mined_pos[0], self.bb.last_mined_pos[1]
        ):
            self.bb.probing_mode = False
            self.bb.last_mined_pos = None

        floor_turns = self.bb.total_turns - self.bb.floor_start_turn
        if (floor_turns > 80 or self.bb.probing_mode) and not self.bb.discovered_stairs_pos:
            self.bb.probing_mode = True
            probe_act = self._probe_secret_doors()
            if probe_act:
                return probe_act

        # 50-turn interval minimap check: infer unexplored hallway exits from explored rooms
        if floor_turns > 0 and floor_turns % 50 == 0:
            hallway_target = self._infer_unexplored_hallways_from_rooms()
            if hallway_target:
                path = self._get_path_to(hallway_target[0], hallway_target[1])
                if path and len(path) > 1:
                    print(
                        f"[Minimap 50-turn Check] Inferred unexplored corridor at {hallway_target} on turn {self.bb.total_turns}"
                    )
                    return ("move", (path[1].x - player.x, path[1].y - player.y))

        # Find frontier (Smart Dive to deep unexplored cluster)
        target = self._infer_unexplored_hallways_from_rooms() if floor_turns >= 50 else None
        if not target:
            target = self._find_deep_frontier() or self._find_nearest_frontier()

        if target:
            # Clean up reached target from candidate queue
            if (
                player.x == target[0]
                and player.y == target[1]
                and target in self.bb.frontier_targets
            ):
                self.bb.frontier_targets.remove(target)

            candidates = [target] + [pos for pos in self.bb.frontier_targets if pos != target]
            for cand in candidates:
                self.bb.current_target_pos = cand
                path = self._get_path_to(cand[0], cand[1])
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

    def _find_dead_ends(self) -> list[tuple[int, int]]:
        """Identify dead-end hallway tiles (tiles with 3 adjacent wall neighbors)."""
        engine = self.bb.engine
        game_map = engine.game_map
        max_x = min(MAP_WIDTH, len(game_map.tiles))
        max_y = min(MAP_HEIGHT, len(game_map.tiles[0]))

        dead_ends = []
        for x in range(1, max_x - 1):
            for y in range(1, max_y - 1):
                if game_map.explored[x][y] and game_map.is_walkable(x, y):
                    wall_count = sum(
                        1
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                        if not game_map.is_walkable(x + dx, y + dy)
                    )
                    if wall_count >= 3:
                        dead_ends.append((x, y))
        return dead_ends

    def _probe_secret_doors(self) -> tuple[str, Any] | None:
        """Scan dead-ends and suspicious walls for hidden doors/pathways."""
        engine = self.bb.engine
        player = engine.player

        dead_ends = self._find_dead_ends()
        if not dead_ends:
            suspicious = self._find_suspicious_walls()
            if not suspicious:
                return None
            suspicious.sort(key=lambda p: abs(p[0] - player.x) + abs(p[1] - player.y))
            target_de = suspicious[0]
        else:
            # Pick nearest dead end
            dead_ends.sort(key=lambda p: abs(p[0] - player.x) + abs(p[1] - player.y))
            target_de = dead_ends[0]

        # If not standing on probe target, move toward it
        if (player.x, player.y) != target_de:
            path = self._get_path_to(target_de[0], target_de[1])
            if path and len(path) > 1:
                return ("move", (path[1].x - player.x, path[1].y - player.y))

        # Standing on probe tile: probe adjacent walls
        wall_dir = self._find_best_mining_direction(player.x, player.y)
        if wall_dir:
            tx, ty = player.x + wall_dir[0], player.y + wall_dir[1]
            self.bb.last_mined_pos = (tx, ty)
            print(f"[Secret Door Probe] Mining wall at ({tx}, {ty}) on turn {self.bb.total_turns}")
            return ("mine_wall", None)

        # Desperate measure: if stalled on floor for > 150 turns, try mining any adjacent wall
        floor_turns = self.bb.total_turns - self.bb.floor_start_turn
        if floor_turns > 150:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                if not engine.game_map.is_walkable(player.x + dx, player.y + dy):
                    tx, ty = player.x + dx, player.y + dy
                    self.bb.last_mined_pos = (tx, ty)
                    print(
                        f"[Secret Door Probe] Desperate mining at ({tx}, {ty}) on turn {self.bb.total_turns}"
                    )
                    return ("mine_wall", None)

        return None

    def _find_best_mining_direction(self, px: int, py: int) -> tuple[int, int] | None:
        """Find the most promising adjacent wall direction to dig toward unexplored space."""
        engine = self.bb.engine
        game_map = engine.game_map
        max_x = min(MAP_WIDTH, len(game_map.tiles))
        max_y = min(MAP_HEIGHT, len(game_map.tiles[0]))

        best_dir = None
        best_score = -1

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            wx, wy = px + dx, py + dy
            if not (1 <= wx < max_x - 1 and 1 <= wy < max_y - 1):
                continue
            if (wx, wy) in self.bb.unbreakable_walls:
                continue
            # Must be a non-walkable wall
            if game_map.is_walkable(wx, wy):
                continue

            # Check unexplored tiles behind this wall (within 2-3 tiles)
            unexplored_behind = 0
            for ddx in range(-2, 3):
                for ddy in range(-2, 3):
                    tx, ty = wx + ddx, wy + ddy
                    if 0 <= tx < max_x and 0 <= ty < max_y and not game_map.explored[tx][ty]:
                        unexplored_behind += 1

            if unexplored_behind > best_score:
                best_score = unexplored_behind
                best_dir = (dx, dy)

        return best_dir

    def _find_suspicious_walls(self) -> list[tuple[int, int]]:
        """Find walkable tiles adjacent to walls backed by large unexplored voids."""
        engine = self.bb.engine
        game_map = engine.game_map
        max_x = min(MAP_WIDTH, len(game_map.tiles))
        max_y = min(MAP_HEIGHT, len(game_map.tiles[0]))

        candidates = []
        for x in range(2, max_x - 2):
            for y in range(2, max_y - 2):
                if game_map.explored[x][y] and game_map.is_walkable(x, y):
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        wx, wy = x + dx, y + dy
                        if not game_map.is_walkable(wx, wy):
                            # Check if 2 steps into the wall is unexplored
                            tx, ty = wx + dx, wy + dy
                            if (
                                0 <= tx < max_x
                                and 0 <= ty < max_y
                                and not game_map.explored[tx][ty]
                            ):
                                candidates.append((x, y))
                                break
        return candidates

    def _has_offering_items(self) -> bool:
        for itm in self.bb.engine.inventory.items:
            if any(kw in itm.name for kw in ["肉", "鉱石", "パン", "ハーブ"]):
                return True
        return False

    def _scan_features(self) -> None:
        if self.bb.discovered_stairs_pos and self.bb.discovered_altar_pos:
            return

        engine = self.bb.engine
        player = engine.player
        game_map = engine.game_map

        # Check stairs
        if not self.bb.discovered_stairs_pos:
            stairs_pos = getattr(game_map, "stairs_down_pos", None)
            if stairs_pos:
                sx, sy = stairs_pos
                if (
                    sx < len(game_map.explored)
                    and sy < len(game_map.explored[0])
                    and game_map.explored[sx][sy]
                ):
                    self.bb.discovered_stairs_pos = stairs_pos

            if not self.bb.discovered_stairs_pos:
                max_x = min(MAP_WIDTH, len(game_map.tiles), len(game_map.explored))
                max_y = min(MAP_HEIGHT, len(game_map.tiles[0]), len(game_map.explored[0]))
                for x in range(max_x):
                    for y in range(max_y):
                        if game_map.explored[x][y] and game_map.tiles[x][y] in (
                            TILE_STAIRS_DOWN,
                            "TILE_STAIRS_DOWN",
                            ">",
                        ):
                            self.bb.discovered_stairs_pos = (x, y)
                            break
                    if self.bb.discovered_stairs_pos:
                        break

        # Check altar
        if not self.bb.discovered_altar_pos:
            altar_pos = getattr(engine, "altar_pos", None)
            if altar_pos:
                ax, ay = altar_pos
                if (
                    ax < len(game_map.explored)
                    and ay < len(game_map.explored[0])
                    and game_map.explored[ax][ay]
                ):
                    self.bb.discovered_altar_pos = altar_pos

    def _infer_unexplored_hallways_from_rooms(self) -> tuple[int, int] | None:
        """Infer unexplored hallway outlets leading out of explored rooms (Minimap check)."""
        engine = self.bb.engine
        game_map = engine.game_map
        player = engine.player
        max_x = min(MAP_WIDTH, len(game_map.tiles))
        max_y = min(MAP_HEIGHT, len(game_map.tiles[0]))

        outlets: list[tuple[float, tuple[int, int]]] = []
        stairs_pos = getattr(game_map, "stairs_down_pos", None)

        for x in range(1, max_x - 1):
            for y in range(1, max_y - 1):
                # Must be an explored walkable tile
                if not (game_map.explored[x][y] and game_map.is_walkable(x, y)):
                    continue
                if (x, y) in self.bb.dead_end_tiles:
                    continue

                # Check if it opens into an unexplored direction
                unexplored_neighbors = [
                    (x + dx, y + dy)
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    if 0 <= x + dx < max_x
                    and 0 <= y + dy < max_y
                    and not game_map.explored[x + dx][y + dy]
                ]
                if not unexplored_neighbors:
                    continue

                # Calculate score: proximity to player + bias toward stairs
                dist = abs(x - player.x) + abs(y - player.y)
                score = len(unexplored_neighbors) * 5.0 - dist * 0.5

                if stairs_pos and not self.bb.discovered_stairs_pos:
                    dist_to_stairs = abs(x - stairs_pos[0]) + abs(y - stairs_pos[1])
                    score += max(0.0, 60.0 - dist_to_stairs * 2.0)

                outlets.append((score, (x, y)))

        if not outlets:
            return None

        outlets.sort(key=lambda item: item[0], reverse=True)
        return outlets[0][1]

    def _find_deep_frontier(self) -> tuple[int, int] | None:
        """Find the most promising distant unexplored frontier cluster (Smart Dive)."""
        engine = self.bb.engine
        game_map = engine.game_map

        max_x = min(MAP_WIDTH, len(game_map.tiles))
        max_y = min(MAP_HEIGHT, len(game_map.tiles[0]))

        explored_walkable: list[tuple[int, int]] = []
        for x in range(1, max_x - 1):
            for y in range(1, max_y - 1):
                if (
                    (x, y) not in self.bb.dead_end_tiles
                    and game_map.explored[x][y]
                    and game_map.is_walkable(x, y)
                ):
                    explored_walkable.append((x, y))

        frontiers: list[tuple[int, int, int]] = []  # (x, y, unexplored_neighbor_count)
        recent_visited_set = (
            set(list(self.bb.visited_positions)[-20:]) if self.bb.visited_positions else set()
        )
        for x, y in explored_walkable:
            if (x, y) in recent_visited_set:
                continue
            unexplored_count = sum(
                1
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
                if 0 <= x + dx < max_x
                and 0 <= y + dy < max_y
                and not game_map.explored[x + dx][y + dy]
            )
            if unexplored_count > 0:
                frontiers.append((x, y, unexplored_count))

        if not frontiers:
            return self._find_nearest_frontier()

        player = engine.player
        px, py = player.x, player.y

        # Score frontiers: favor high density of unexplored tiles with good distance, and bias toward stairs direction
        hunger = getattr(engine.survival, "hunger", 100) if hasattr(engine, "survival") else 100
        dist_weight = 1.2 if hunger >= 40 else -1.0  # If starving, prefer closest frontiers

        stairs_pos = getattr(game_map, "stairs_down_pos", None)

        scored_frontiers: list[tuple[float, tuple[int, int]]] = []
        for x, y, density in frontiers:
            dist = abs(x - px) + abs(y - py)
            score = (density * 3.0) + (dist * dist_weight)
            if not self.bb.discovered_stairs_pos and stairs_pos:
                dist_to_stairs = abs(x - stairs_pos[0]) + abs(y - stairs_pos[1])
                score += max(0.0, 50.0 - dist_to_stairs * 1.5)  # Stairs Sniffer Heuristic
            scored_frontiers.append((score, (x, y)))

        # Sort descending by score
        scored_frontiers.sort(key=lambda item: item[0], reverse=True)

        if scored_frontiers:
            best_pos = scored_frontiers[0][1]
            self.bb.frontier_targets = [pos for _, pos in scored_frontiers[:5]]
            return best_pos

        return self._find_nearest_frontier()

    def _find_nearest_frontier(self) -> tuple[int, int] | None:
        """Legacy local frontier search (used as fallback when deep frontier is unreachable)."""
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
        max_depth = max(100, distance + 30)

        def _is_valid_tile(x: int, y: int) -> bool:
            if not engine.is_tile_free(x, y, blocked):
                return False
            if (x, y) != (target_x, target_y) and (x, y) in self.bb.dead_end_tiles:
                return False
            return True

        return AStar.get_path(
            Point(engine.player.x, engine.player.y),
            Point(target_x, target_y),
            _is_valid_tile,
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
        # If already standing on stairs or on a stairs tile, execute descend
        game_map = engine.game_map
        on_stairs = (player.x == sx and player.y == sy) or game_map.tiles[player.x][player.y] in (
            TILE_STAIRS_DOWN,
            "TILE_STAIRS_DOWN",
            ">",
        )
        if on_stairs:
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
            if (
                self.bb.strategy_name in ("mage", "speed")
                or self.bb.strategy_params.get("focus") == "magic"
            ):
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
