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
    
    # Spatial & temporal memory
    visited_positions: deque[tuple[int, int]] = field(default_factory=lambda: deque(maxlen=40))
    dead_end_tiles: set[tuple[int, int]] = field(default_factory=set)
    known_traps: set[tuple[int, int]] = field(default_factory=set)
    discovered_stairs_pos: tuple[int, int] | None = None
    discovered_altar_pos: tuple[int, int] | None = None
    
    # Counters and metrics
    stalled_turns: int = 0
    consecutive_kites: int = 0
    floor_start_turn: int = 0
    current_floor: int = 1
    total_turns: int = 0

    def record_position(self, pos: tuple[int, int]) -> None:
        """Record current player position into history and update oscillation checks."""
        self.visited_positions.append(pos)
        self.total_turns += 1

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
        self.visited_positions.clear()
        self.dead_end_tiles.clear()
        self.known_traps.clear()
        self.discovered_stairs_pos = None
        self.discovered_altar_pos = None
        self.stalled_turns = 0
        self.consecutive_kites = 0
        self.floor_start_turn = self.total_turns
