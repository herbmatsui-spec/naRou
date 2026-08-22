"""
AI Floor Progression & Dungeon Descent Engine
Manages exploration ratio tracking, descent triggers, stairs navigation, and memory resets across floors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard


class FloorProgressionManager:
    """Controls floor exploration tracking, descent criteria, and floor transition state management."""

    def __init__(self, blackboard: AIBlackboard):
        self.bb = blackboard

    def compute_exploration_ratio(self) -> float:
        """Compute the ratio of explored walkable tiles over total walkable tiles."""
        engine = self.bb.engine
        game_map = engine.game_map

        total_walkable = 0
        explored_walkable = 0
        visited_set = set(self.bb.visited_positions)

        for y in range(game_map.height):
            for x in range(game_map.width):
                if game_map.is_walkable(x, y):
                    total_walkable += 1
                    is_explored = False
                    if hasattr(game_map, "explored"):
                        if isinstance(game_map.explored, dict):
                            is_explored = game_map.explored.get((x, y), False)
                        elif hasattr(game_map.explored, "__getitem__"):
                            try:
                                is_explored = bool(game_map.explored[y, x])
                            except Exception:
                                pass
                    if (x, y) in visited_set or is_explored:
                        explored_walkable += 1

        if total_walkable == 0:
            return 1.0

        return explored_walkable / total_walkable

    def should_descend(self) -> bool:
        """Determine whether the AI should descend to the next floor."""
        engine = self.bb.engine
        stairs_pos = self.bb.discovered_stairs_pos or getattr(engine, "stairs_down_pos", None)

        if not stairs_pos:
            return False

        ratio = self.compute_exploration_ratio()

        # Strategy-dependent exploration threshold
        threshold = 0.60
        if self.bb.strategy_name == "speed":
            threshold = 0.25
        elif self.bb.strategy_name == "safe":
            threshold = 0.75

        # Check threshold
        if ratio >= threshold:
            return True

        # Crisis descent check (low HP and enemies nearby)
        player = engine.player
        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0
        if hp_ratio < 0.35:
            # If stairs are in adjacent or reachable range, descend to escape
            dist_to_stairs = max(abs(player.x - stairs_pos[0]), abs(player.y - stairs_pos[1]))
            if dist_to_stairs <= 3:
                return True

        return False

    def navigate_to_stairs(self) -> tuple[str, Any] | None:
        """Navigate towards discovered stairs or take stairs if standing on them."""
        engine = self.bb.engine
        player = engine.player
        stairs_pos = self.bb.discovered_stairs_pos or getattr(engine, "stairs_down_pos", None)

        if not stairs_pos:
            return None

        sx, sy = stairs_pos

        # If on stairs, descend
        if player.x == sx and player.y == sy:
            return ("descend", None)

        # Pathfind to stairs
        from naRou.ai_escape import SafePathfinder
        path = SafePathfinder.get_safe_path(self.bb, sx, sy)
        if path and len(path) > 1:
            return ("move", (path[1].x - player.x, path[1].y - player.y))

        return None

    def on_floor_transition(self, new_floor: int) -> None:
        """Completely reset floor-specific spatial memory upon entering a new floor."""
        self.bb.current_floor = new_floor
        self.bb.discovered_stairs_pos = None
        self.bb.discovered_altar_pos = None
        self.bb.current_target_pos = None
        self.bb.current_target_enemy = None
        self.bb.current_path.clear()
        self.bb.dead_end_tiles.clear()
        self.bb.known_traps.clear()
        self.bb.visited_positions.clear()
        self.bb.stalled_turns = 0
        self.bb.consecutive_kites = 0
        self.bb.floor_start_turn = self.bb.total_turns

    def scan_entry_safety(self) -> dict[str, Any]:
        """Perform immediate 3x3 surrounding scan upon arriving at new floor."""
        engine = self.bb.engine
        player = engine.player
        adjacent_enemies = []

        for ent in getattr(engine, "entities", []):
            if ent is not player and getattr(ent, "hp", 0) > 0 and not getattr(ent, "is_pet", False):
                dist = max(abs(ent.x - player.x), abs(ent.y - player.y))
                if dist <= 1:
                    adjacent_enemies.append(ent)

        is_safe = len(adjacent_enemies) == 0
        return {
            "is_safe": is_safe,
            "adjacent_enemies": adjacent_enemies,
            "enemy_count": len(adjacent_enemies),
        }

    def find_next_frontier_step(self) -> tuple[int, int] | None:
        """Find the nearest walkable unvisited frontier tile and return first step."""
        from collections import deque
        engine = self.bb.engine
        player = engine.player
        game_map = engine.game_map

        visited_set = set(self.bb.visited_positions)
        dead_ends = self.bb.dead_end_tiles

        queue = deque([(player.x, player.y, [])])
        seen = {(player.x, player.y)}

        while queue:
            cx, cy, path = queue.popleft()

            # If we reached an unvisited walkable tile not in dead ends
            if (cx, cy) not in visited_set and (cx, cy) not in dead_ends and (cx, cy) != (player.x, player.y):
                if path:
                    first_step = path[0]
                    return (first_step[0] - player.x, first_step[1] - player.y)

            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in seen and game_map.is_walkable(nx, ny):
                    seen.add((nx, ny))
                    queue.append((nx, ny, path + [(nx, ny)]))

        return None

    def decide_progression_action(self) -> tuple[str, Any]:
        """Evaluate floor progression and decide whether to descend or continue exploring."""
        # 1. Check if we should descend now
        if self.should_descend():
            stairs_action = self.navigate_to_stairs()
            if stairs_action:
                return stairs_action

        # 2. Otherwise, advance towards nearest unvisited frontier
        frontier_step = self.find_next_frontier_step()
        if frontier_step:
            return ("move", frontier_step)

        # 3. Fallback: random walk if fully explored but not descending
        import random
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        return ("move", (dx, dy))
