"""AI behavior state subpackage.

Concrete AI behavior states previously defined in ``naRou/ai_states.py`` are
split into role-based modules: ``exploration_states``, ``combat_states``,
``idle_states``, ``flee_states`` (and a reserved ``pet_states``). The old
``naRou/ai_states.py`` is now a thin backward-compatibility shim that re-exports
everything from this package.
"""

from naRou.ai.states.base_state import AIState
from naRou.ai.states.combat_states import CombatState, KiteState
from naRou.ai.states.exploration_states import (
    DescendState,
    ExploreState,
    OfferPrayState,
)
from naRou.ai.states.flee_states import EmergencyState, EscapeState
from naRou.ai.states.idle_states import RestRecoverState

__all__ = [
    "AIState",
    "CombatState",
    "KiteState",
    "DescendState",
    "ExploreState",
    "OfferPrayState",
    "EmergencyState",
    "EscapeState",
    "RestRecoverState",
]
