"""PersistenceManager: encapsulates auto-save logic.

Extracted from Engine.advance_world (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Engine


class PersistenceManager:
    """Handles periodic auto-save of game state."""

    def autosave_if_due(self, engine: "Engine") -> None:
        """Auto-save every AUTO_SAVE_INTERVAL turns (Step 71)."""
        from advanced_systems import SaveSystem
        from constants import AUTO_SAVE_INTERVAL

        if engine.turns % AUTO_SAVE_INTERVAL == 0:
            msg = SaveSystem.save(engine)
            engine.log(f"[Auto] {msg}", (80, 200, 80))
