"""FactionManager: encapsulates faction reputation and influence updates.

Extracted from Engine._on_kill and Engine.advance_world (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


class FactionManager:
    """Updates faction reputation on kills and influence over time."""

    def update_kill_reputation(self, engine: "Engine", entity: "Entity") -> None:
        """Increment kingdom reputation when the player kills an enemy (Step 63)."""
        if hasattr(engine.player, "faction_reputation"):
            engine.player.faction_reputation["kingdom_garde"] = (
                engine.player.faction_reputation.get("kingdom_garde", 0) + 1
            )

    def update_influence(self, engine: "Engine") -> None:
        """Periodic faction influence fluctuation (Step 62)."""
        from constants import FACTION_INFLUENCE_INTERVAL

        if engine.turns % FACTION_INFLUENCE_INTERVAL == 0:
            for fid in engine.faction_war_registry.all():
                chg = engine.faction_war_manager.calculate_influence_change(fid, engine)
                engine.faction_war_manager.apply_influence_effects(fid, chg)
