"""Backward-compatibility shim for ``naRou/ai_states``.

The concrete AI behavior states defined here previously now live in the
``naRou/ai/states/`` subpackage. This module re-exports them so existing
imports such as ``from naRou.ai_states import CombatState`` keep working.

New code should import directly from ``naRou.ai.states``.
"""

from naRou.ai.states import *  # noqa: F401,F403
from naRou.ai.states import (  # noqa: F401
    AIState,
    CombatState,
    DescendState,
    EmergencyState,
    EscapeState,
    ExploreState,
    KiteState,
    OfferPrayState,
    RestRecoverState,
)
