"""Quest data class."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Quest:
    title: str
    target_monster: str
    target_count: int
    current_count: int = 0
    reward_gold: int = 200
    reward_platinum: int = 2
    completed: bool = False
