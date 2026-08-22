"""SkillRewardManager: encapsulates skill-point rewards on monster kills.

Extracted from Engine._on_kill (game.py).
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


class SkillRewardManager:
    """Grants occasional skill points when the player kills an enemy."""

    def grant_kill_skill_points(self, engine: "Engine", entity: "Entity") -> None:
        """Random skill-point bonus on kill (Step 26 optional hook)."""
        from constants import SKILL_DROP_CHANCE, SKILL_DROP_MAX, SKILL_DROP_MIN

        if random.random() < SKILL_DROP_CHANCE:
            sp_bonus = random.randint(SKILL_DROP_MIN, SKILL_DROP_MAX)
            engine.player.skill_points += sp_bonus
            engine.player.total_skill_points_earned += sp_bonus
            engine.log(f"★討伐の閃き！ {sp_bonus} スキルポイントを獲得！", (150, 255, 200))
