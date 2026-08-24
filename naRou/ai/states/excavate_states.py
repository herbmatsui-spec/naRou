"""AI archaeology states: excavate sites and interpret reached truths.

Excavation is depth-based (no tile navigation needed): the engine picks a
site valid for the current depth. Interpretation triggers the ending once a
truth has been reached via decoding.
"""

from __future__ import annotations

from typing import Any

from naRou.ai.states.base_state import AIState
from naRou.ai_floor_progression import FloorProgressionManager


class ExcavateState(AIState):
    """Excavates an archaeology site at the current depth when one is available."""

    def _fp(self) -> FloorProgressionManager:
        return FloorProgressionManager(self.bb)

    def check_transition(self) -> str | None:
        player = self.bb.engine.player
        hp_ratio = player.hp / player.max_hp if getattr(player, "max_hp", 0) > 0 else 0
        if hp_ratio < 0.35:
            return "EMERGENCY"
        if not self._fp().should_excavate():
            return "EXPLORE"
        return None

    def decide_action(self) -> tuple[str, Any]:
        # engine.excavate() picks a valid site for the current depth and resolves it.
        return ("excavate", None)


class InterpretState(AIState):
    """Interprets the most recently reached truth to trigger an ending."""

    def check_transition(self) -> str | None:
        if not self.bb.pending_interpret:
            return "EXPLORE"
        return None

    def decide_action(self) -> tuple[str, Any]:
        engine = self.bb.engine
        # Open the interpret prompt, then confirm the first candidate ending.
        if not getattr(engine, "arch_interpret_active", False):
            engine.open_interpret_prompt()
        if getattr(engine, "arch_interpret_active", False):
            engine.confirm_interpret()
        self.bb.pending_interpret = False
        return ("wait", None)
