"""
Hierarchical Finite State Machine (HFSM) Framework for AI Subagents
Manages state lifecycle (enter/exit), transitions, and action decisions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

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


class AIStateMachine:
    """Manages state transitions and active state execution."""

    def __init__(self, blackboard: AIBlackboard):
        self.bb = blackboard
        self.states: dict[str, AIState] = {}
        self._current_state_name: str | None = None
        self._current_state: AIState | None = None

    def register_state(self, name: str, state: AIState) -> None:
        """Register a state under a unique string name."""
        self.states[name] = state

    @property
    def current_state_name(self) -> str | None:
        return self._current_state_name

    @property
    def current_state(self) -> AIState | None:
        return self._current_state

    def change_state(self, new_state_name: str) -> None:
        """Transition from current state to a new state."""
        if new_state_name not in self.states:
            raise ValueError(f"State '{new_state_name}' is not registered.")

        if self._current_state:
            self._current_state.exit()

        self._current_state_name = new_state_name
        self._current_state = self.states[new_state_name]
        self._current_state.enter()

    def update(self) -> tuple[str, Any]:
        """Check transitions and decide next action."""
        if not self._current_state:
            raise RuntimeError("StateMachine has no active state. Call change_state() first.")

        # Check for state transitions (allow chaining up to 3 transitions)
        for _ in range(3):
            next_state = self._current_state.check_transition()
            if next_state and next_state != self._current_state_name and next_state in self.states:
                self.change_state(next_state)
            else:
                break

        return self._current_state.decide_action()
