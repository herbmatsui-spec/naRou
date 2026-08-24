"""Base class and shared imports for AI behavior states.

The abstract ``AIState`` base class was extracted here from
``naRou/ai_state_machine.py`` so that the concrete states in this subpackage
can depend on a single, stable base without pulling in the full state-machine
engine. ``naRou/ai_state_machine`` continues to re-export ``AIState`` for
backward compatibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from naRou.constants import MAP_HEIGHT, MAP_WIDTH, TILE_STAIRS_DOWN
from naRou.core_framework import AStar, Point

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard


class AIState(ABC):
    """Abstract base class for all AI behavior states."""

    def __init__(self, blackboard: AIBlackboard):
        self.bb = blackboard

    def enter(self) -> None:
        """Called when entering this state."""
        pass

    def exit(self) -> None:
        """Called when exiting this state."""
        pass

    @abstractmethod
    def check_transition(self) -> str | None:
        """Evaluate conditions and return the next state name, or None to stay."""
        pass

    @abstractmethod
    def decide_action(self) -> tuple[str, Any]:
        """Determine and return the action (action_name, params) to perform."""
        pass
