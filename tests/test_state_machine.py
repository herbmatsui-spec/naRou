from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from constants import GameState
from game import Engine


def test_game_state_definitions():
    assert GameState.EXPLORING.value == "exploring"
    assert GameState.COMBAT.value == "combat"
    assert GameState.DIALOGUE.value == "dialogue"
    assert GameState.MENU.value == "menu"
    assert GameState.EVENT.value == "event"
    assert GameState.PAUSED.value == "paused"


def test_engine_change_state_and_hooks():
    eng = Engine()
    assert eng.current_state == GameState.EXPLORING

    # Transition to DIALOGUE
    eng.active_dialogue = ("シエル", "こんにちは！")
    eng.change_state(GameState.DIALOGUE)
    assert eng.current_state == GameState.DIALOGUE
    assert eng.game_state == "talk"

    # Transition to MENU triggers exit hook (clearing active_dialogue)
    eng.change_state(GameState.MENU)
    assert eng.current_state == GameState.MENU
    assert eng.active_dialogue is None

    # Transition back to EXPLORING
    eng.change_state(GameState.EXPLORING)
    assert eng.current_state == GameState.EXPLORING
    assert eng.game_state == "play"


def test_state_machine_robustness():
    eng = Engine()
    # Continuous state switching
    for st in [
        GameState.MENU,
        GameState.DIALOGUE,
        GameState.EVENT,
        GameState.PAUSED,
        GameState.EXPLORING,
    ]:
        eng.change_state(st)
        assert eng.current_state == st
