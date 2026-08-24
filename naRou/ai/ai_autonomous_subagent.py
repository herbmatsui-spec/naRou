"""
Unified Autonomous Subagent AI Engine
Master AI combining Hierarchical FSM, Blackboard memory, Safety Heatmaps,
Combat Tactics, Item Decisions, Pet Coordination, and Floor Progression.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.game import Engine

from naRou.ai_blackboard import AIBlackboard
from naRou.ai_state_machine import AIStateMachine
from naRou.ai.states import (
    CombatState,
    DescendState,
    EmergencyState,
    EscapeState,
    ExploreState,
    KiteState,
    OfferPrayState,
    RestRecoverState,
)
from naRou.ai.states.excavate_states import ExcavateState, InterpretState
from naRou.ai_safety_grid import SafetyGridEvaluator
from naRou.ai_combat_tactics import CombatTacticsManager
from naRou.ai_item_decider import ItemDecider
from naRou.ai_pet_tactics import PetTacticsCoordinator
from naRou.ai_floor_progression import FloorProgressionManager


class AutonomousSubagentAI:
    """Master AI engine governing the player character with high-level autonomy."""

    def __init__(
        self,
        engine: Engine,
        strategy_name: str = "hybrid",
        strategy_params: dict[str, Any] | None = None,
    ):
        self.engine = engine
        self.bb = AIBlackboard(
            engine=engine,
            strategy_name=strategy_name,
            strategy_params=strategy_params or {},
        )
        self.fsm = AIStateMachine(self.bb)

        # Register specialized managers
        self.safety_grid = SafetyGridEvaluator(self.bb)
        self.combat_tactics = CombatTacticsManager(self.bb)
        self.item_decider = ItemDecider(self.bb)
        self.pet_tactics = PetTacticsCoordinator(self.bb)
        self.floor_progression = FloorProgressionManager(self.bb)

        # Register all HFSM states (supporting both lowercase and uppercase names)
        states_map = {
            "explore": ExploreState(self.bb),
            "combat": CombatState(self.bb),
            "kite": KiteState(self.bb),
            "rest": RestRecoverState(self.bb),
            "emergency": EmergencyState(self.bb),
            "descend": DescendState(self.bb),
            "pray": OfferPrayState(self.bb),
            "offer_pray": OfferPrayState(self.bb),
            "escape": EscapeState(self.bb),
            "excavate": ExcavateState(self.bb),
            "interpret": InterpretState(self.bb),
        }
        for k, v in list(states_map.items()):
            self.fsm.register_state(k.lower(), v)
            self.fsm.register_state(k.upper(), v)

        self.fsm.change_state("explore")

    def decide_turn_action(self) -> tuple[str, Any]:
        """Execute one autonomous decision cycle and return action."""
        player = self.engine.player
        self.bb.record_position((player.x, player.y))

        # Check stairs transition
        if getattr(self.engine, "dungeon_level", 1) != self.bb.current_floor:
            self.floor_progression.on_floor_transition(self.engine.dungeon_level)
            self.fsm.change_state("explore")

        self._sync_archaeology_flags()

        return self.fsm.update()

    def _sync_archaeology_flags(self) -> None:
        """Sync reached truths from player component into blackboard (Step 45/64)."""
        comp = getattr(self.engine.player, "archaeology", None)
        if comp is None:
            return
        reached = getattr(comp, "reached_truths", [])
        for tid in reached:
            if tid not in self.bb.reached_truths:
                self.bb.reached_truths.append(tid)
                self.bb.pending_interpret = True
