"""StateMachine: encapsulates game-state transition logic and hooks.

Extracted from Engine.change_state (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from constants import GAME_STATE_TO_LEGACY

if TYPE_CHECKING:
    from constants import GameState
    from game import Engine


class StateMachine:
    """Applies state transitions with on_exit/on_enter hooks."""

    def apply(self, engine: "Engine", new_state: "GameState") -> None:
        """状態遷移（ステートマシン）の厳格化とフック処理 (Step 6.2)"""
        if engine.current_state == new_state:
            return

        old_state = engine.current_state
        # on_exit hook
        if old_state.value == "dialogue":
            engine.active_dialogue = None
        elif old_state.value == "menu":
            engine.inventory_cursor = 0

        engine.current_state = new_state

        # 旧 game_state 文字列への双方向同期
        engine.game_state = GAME_STATE_TO_LEGACY.get(new_state, "play")

        # on_enter hook
        if new_state.value == "menu" and hasattr(engine, "look_cursor"):
            engine.look_cursor.active = False
