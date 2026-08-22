"""
AI Blackboard System for Autonomous Subagents
Central shared memory holding world state, goal targets, spatial memory, and heuristics.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.entity import Entity
    from naRou.game import Engine


@dataclass
class AIBlackboard:
    engine: Engine
    strategy_name: str = "hybrid"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    
    # Target and navigation
    current_target_pos: tuple[int, int] | None = None
    current_target_enemy: Entity | None = None
    current_path: list[tuple[int, int]] = field(default_factory=list)
    frontier_targets: list[tuple[int, int]] = field(default_factory=list)
    unexplored_clusters: list[list[tuple[int, int]]] = field(default_factory=list)
    
    # Spatial & temporal memory
    visited_positions: deque[tuple[int, int]] = field(default_factory=lambda: deque(maxlen=100))
    dead_end_tiles: set[tuple[int, int]] = field(default_factory=set)
    known_traps: set[tuple[int, int]] = field(default_factory=set)
    unbreakable_walls: set[tuple[int, int]] = field(default_factory=set)
    discovered_stairs_pos: tuple[int, int] | None = None
    discovered_altar_pos: tuple[int, int] | None = None
    combat_history: deque[int] = field(default_factory=lambda: deque(maxlen=10))
    
    # Counters and metrics
    stalled_turns: int = 0
    consecutive_kites: int = 0
    stalemate_turns: int = 0
    stalemate_cooldown: int = 0
    force_blitz_attack: bool = False
    probing_mode: bool = False
    last_mined_pos: tuple[int, int] | None = None
    floor_start_turn: int = 0
    current_floor: int = 1
    total_turns: int = 0

    def record_position(self, pos: tuple[int, int]) -> None:
        """Record current player position into history and update oscillation checks."""
        self.visited_positions.append(pos)
        self.total_turns += 1
        if self.stalemate_cooldown > 0:
            self.stalemate_cooldown -= 1

    def update_combat_history(self, enemy_pos: tuple[int, int]) -> None:
        """Record distance to current combat target and track stalemate turns."""
        if not self.visited_positions:
            return
        px, py = self.visited_positions[-1]
        dist = max(abs(enemy_pos[0] - px), abs(enemy_pos[1] - py))
        self.combat_history.append(dist)
        if len(self.combat_history) >= 2 and self.combat_history[-1] == self.combat_history[-2]:
            self.stalemate_turns += 1
        else:
            self.stalemate_turns = 0

    def is_stalemate(self, threshold: int = 5) -> bool:
        """Detect if combat has been stalled/stalemated with unchanged distance."""
        if self.stalemate_cooldown > 0:
            return False
        return self.stalemate_turns >= threshold

    def is_oscillating(self, window_size: int = 20, max_unique: int = 3) -> bool:
        """Detect if agent is trapped in a 2-3 tile oscillation loop."""
        if len(self.visited_positions) < window_size:
            return False
        recent = list(self.visited_positions)[-window_size:]
        unique_coords = set(recent)
        return len(unique_coords) <= max_unique

    def reset_floor_memory(self, floor_level: int) -> None:
        """Reset spatial memory when moving to a new dungeon floor."""
        self.current_floor = floor_level
        self.current_target_pos = None
        self.current_target_enemy = None
        self.current_path.clear()
        self.frontier_targets.clear()
        self.unexplored_clusters.clear()
        self.visited_positions.clear()
        self.dead_end_tiles.clear()
        self.known_traps.clear()
        self.unbreakable_walls.clear()
        self.discovered_stairs_pos = None
        self.discovered_altar_pos = None
        self.stalled_turns = 0
        self.consecutive_kites = 0
        self.stalemate_turns = 0
        self.stalemate_cooldown = 0
        self.force_blitz_attack = False
        self.probing_mode = False
        self.last_mined_pos = None
        self.floor_start_turn = self.total_turns
