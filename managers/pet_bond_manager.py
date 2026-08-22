"""PetBondManager: encapsulates pet bond updates.

Extracted from Engine._on_kill and Engine.advance_world (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core_framework import Point

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


class PetBondManager:
    """Updates pet bond based on combat cooperation and proximity."""

    def update_combat_bond(self, engine: "Engine", entity: "Entity") -> None:
        """Increase bond when the pet fought alongside the player (Step 33)."""
        from constants import COMBAT_BOND_GAIN

        if engine.pet and engine.pet.hp > 0 and hasattr(engine.pet, "pet_ai"):
            p_dist = Point(engine.pet.x, engine.pet.y).chebyshev_distance(Point(entity.x, entity.y))
            if p_dist <= 3:
                engine.pet.pet_ai.increase_bond(COMBAT_BOND_GAIN, "combat_together")

    def update_turn_bond(self, engine: "Engine") -> None:
        """Per-turn walking/neglected bond change (Steps 30, 34, 44, 45)."""
        from constants import (
            BOND_NEGLECTED_LOSS,
            BOND_WALKING_GAIN,
            PET_NEGLECTED_BOND_DISTANCE,
            PET_WALKING_BOND_DISTANCE,
        )

        if engine.pet and hasattr(engine.pet, "pet_ai"):
            p_dist = Point(engine.pet.x, engine.pet.y).chebyshev_distance(
                Point(engine.player.x, engine.player.y)
            )
            if p_dist <= PET_WALKING_BOND_DISTANCE and engine.pet.hp > 0:
                engine.pet.pet_ai.increase_bond(BOND_WALKING_GAIN, "walking")
            elif p_dist >= PET_NEGLECTED_BOND_DISTANCE:
                engine.pet.pet_ai.increase_bond(BOND_NEGLECTED_LOSS, "neglected")
