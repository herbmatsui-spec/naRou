"""
AI Escape & Oscillation Management Engine
Detects movement loops, dead-ends, and manages multi-tier escape tactics.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard


class OscillationDetector:
    """Detects oscillation loops and stationary stalling."""

    def __init__(self, window_size: int = 20, max_unique: int = 3):
        self.window_size = window_size
        self.max_unique = max_unique

    def is_oscillating(self, history: deque[tuple[int, int]]) -> bool:
        """Check if recent movement history consists of <= max_unique coordinates."""
        if len(history) < self.window_size:
            return False
        recent = list(history)[-self.window_size:]
        unique_positions = set(recent)
        return len(unique_positions) <= self.max_unique

    def update_blackboard_stall(self, blackboard: AIBlackboard, current_pos: tuple[int, int]) -> None:
        """Update stall counters and oscillation state on the blackboard."""
        blackboard.record_position(current_pos)
        if self.is_oscillating(blackboard.visited_positions):
            blackboard.stalled_turns += 1
        else:
            # Gradually decay stall counter when moving freely
            blackboard.stalled_turns = max(0, blackboard.stalled_turns - 1)


class DeadEndDetector:
    """Identifies and registers dead-end tiles to prevent repetitive cul-de-sac pathing."""

    @staticmethod
    def scan_dead_ends(blackboard: AIBlackboard) -> set[tuple[int, int]]:
        """Identify all dead-end tiles on the explored map and add them to blackboard.dead_end_tiles."""
        game_map = blackboard.engine.game_map
        max_x = len(game_map.tiles)
        max_y = len(game_map.tiles[0])
        
        # Dead ends: explored walkable tiles with only 1 walkable neighbor and no special objects
        changed = True
        new_dead_ends: set[tuple[int, int]] = set()

        while changed:
            changed = False
            for x in range(1, max_x - 1):
                for y in range(1, max_y - 1):
                    pos = (x, y)
                    if pos in blackboard.dead_end_tiles or pos in new_dead_ends:
                        continue

                    # Never mark stairs or altar as dead end
                    if pos == blackboard.discovered_stairs_pos or pos == blackboard.discovered_altar_pos:
                        continue

                    if game_map.explored[x][y] and game_map.is_walkable(x, y):
                        # Count open walkable neighbors not already marked as dead ends
                        open_neighbors = sum(
                            1 for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                            if 0 <= x + dx < max_x and 0 <= y + dy < max_y
                            and game_map.is_walkable(x + dx, y + dy)
                            and (x + dx, y + dy) not in blackboard.dead_end_tiles
                            and (x + dx, y + dy) not in new_dead_ends
                        )
                        # If cul-de-sac (1 neighbor or isolated 0 neighbor) and no unexplored neighbor
                        if open_neighbors <= 1:
                            has_unexplored_neighbor = any(
                                not game_map.explored[x + dx][y + dy]
                                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                                if 0 <= x + dx < max_x and 0 <= y + dy < max_y
                            )
                            if not has_unexplored_neighbor:
                                new_dead_ends.add(pos)
                                changed = True

        blackboard.dead_end_tiles.update(new_dead_ends)
        return blackboard.dead_end_tiles


class SafePathfinder:
    """Computes paths that avoid known traps, dead ends, and high danger tiles."""

    @staticmethod
    def get_safe_path(
        blackboard: AIBlackboard,
        target_x: int,
        target_y: int,
        max_depth: int = 50,
    ) -> list[Point] | None:
        """Find path considering trap penalties and blocked positions."""
        from naRou.core_framework import AStar, Point

        engine = blackboard.engine
        blocked = engine.get_blocked_positions()
        player = engine.player

        # Check if tile is walkable and free
        def is_valid(x: int, y: int) -> bool:
            if (x, y) == (target_x, target_y):
                return engine.game_map.is_walkable(x, y)
            return engine.is_tile_free(x, y, blocked)

        path = AStar.get_path(
            Point(player.x, player.y),
            Point(target_x, target_y),
            is_valid,
            max_depth=max_depth,
        )
        return path


class EscapeTactics:
    """Provides multi-tier escape tactics for stuck AI agents."""

    @staticmethod
    def unvisited_random_walk(blackboard: AIBlackboard) -> tuple[int, int] | None:
        """Level 1 Escape: Move to the adjacent walkable tile with the lowest visit count."""
        import random
        engine = blackboard.engine
        player = engine.player
        history = list(blackboard.visited_positions)

        candidates = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if engine.game_map.is_walkable(nx, ny) and not engine.get_entity_at(nx, ny):
                # Count occurrences in recent history
                visit_count = history.count((nx, ny))
                candidates.append(((dx, dy), visit_count))

        if not candidates:
            return None

        # Pick move with minimum visits, break ties randomly
        min_visits = min(c[1] for c in candidates)
        best_moves = [c[0] for c in candidates if c[1] == min_visits]
        return random.choice(best_moves)

    @staticmethod
    def find_broad_escape_path(blackboard: AIBlackboard) -> tuple[int, int] | None:
        """Level 2 Escape: Breadth-first search for the farthest reachable unvisited tile."""
        from collections import deque
        from naRou.core_framework import Point

        engine = blackboard.engine
        player = engine.player
        game_map = engine.game_map
        visited_set = set(blackboard.visited_positions)

        queue: deque[tuple[int, int, list[tuple[int, int]]]] = deque([(player.x, player.y, [])])
        seen: set[tuple[int, int]] = {(player.x, player.y)}

        best_path: list[tuple[int, int]] | None = None
        max_dist_from_start = 0

        while queue:
            cx, cy, path = queue.popleft()
            
            # If we reached a tile never in recent history, return first move
            if (cx, cy) not in visited_set and len(path) > 0:
                return path[0]

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < len(game_map.tiles) and 0 <= ny < len(game_map.tiles[0]):
                    if (nx, ny) not in seen and game_map.is_walkable(nx, ny):
                        seen.add((nx, ny))
                        new_path = path + [(dx, dy)] if path else [(dx, dy)]
                        queue.append((nx, ny, new_path))
                        if len(new_path) > max_dist_from_start:
                            max_dist_from_start = len(new_path)
                            best_path = new_path

        if best_path:
            return best_path[0]
        return None

    @staticmethod
    def try_mine_escape(blackboard: AIBlackboard) -> bool:
        """Level 3 Escape: Mine an adjacent wall to carve a new path out of isolation."""
        from naRou.constants import TILE_WALL

        engine = blackboard.engine
        player = engine.player
        game_map = engine.game_map

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = player.x + dx, player.y + dy
            if 0 <= nx < len(game_map.tiles) and 0 <= ny < len(game_map.tiles[0]):
                if game_map.tiles[nx][ny] == TILE_WALL:
                    engine.mine_wall()
                    return True
        return False

    @staticmethod
    def try_teleport_escape(blackboard: AIBlackboard) -> tuple[str, Any] | None:
        """Level 4 Escape: Use teleport rod or wish rod to warp out of terminal trap."""
        engine = blackboard.engine

        for item in engine.inventory.items:
            if any(kw in item.name for kw in ["テレポート", "願い"]):
                return ("use_item", item)

        return None
