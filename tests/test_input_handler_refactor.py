"""
Regression tests for the InputHandler / ActionRegistry refactor (architecture
refactor Step 6 / Step 6.3-6.5).

Verifies that:
  - ActionRegistry stores per-state bindings and is idempotent when registered
  - InputHandler routes play-state keys through the registry (command pattern)
  - Keys without a registry binding fall back to the legacy handler
  - The registry is scoped to the "play" state (modal states fall back to legacy)
"""

from __future__ import annotations

import tcod.event

from input_actions import ActionRegistry
from input_handler import InputHandler


class StubEngine:
    """最小限のエンジンスタブ（InputHandler の呼び出しを記録）"""

    def __init__(self):
        self.game_state = "play"
        self.current_state = None
        self.active_dialogue = None
        self.moved = None
        self.opened = None
        self.logs = []

    def player_act(self, dx, dy):
        self.moved = (dx, dy)
        return True

    def advance_world(self):
        pass

    def open_context_menu(self):
        self.opened = "context"

    def log(self, *args, **kwargs):
        self.logs.append(args)


def _key(sym, mod=0):
    return tcod.event.KeyDown(sym=sym, scancode=0, mod=mod)


def _reset_registry():
    InputHandler._action_registry = ActionRegistry()
    InputHandler._actions_registered = False


def test_register_default_actions_is_idempotent():
    _reset_registry()
    InputHandler.register_default_actions()
    first = len(InputHandler._action_registry.get_bindings("play"))
    InputHandler.register_default_actions()
    second = len(InputHandler._action_registry.get_bindings("play"))
    assert first > 0
    assert first == second


def test_registry_scoped_to_play_state():
    _reset_registry()
    InputHandler.register_default_actions()
    # モーダル状態にはプレイバインドが露出しない
    assert InputHandler._action_registry.get_bindings("inventory") == []
    assert len(InputHandler._action_registry.get_bindings("play")) > 0


def test_registry_routes_movement_via_command_pattern():
    _reset_registry()
    InputHandler.register_default_actions()
    e = StubEngine()
    InputHandler.handle_event(_key(tcod.event.KeySym.K), e)
    assert e.moved == (0, -1)


def test_registry_routes_context_menu_on_space():
    _reset_registry()
    InputHandler.register_default_actions()
    e = StubEngine()
    InputHandler.handle_event(_key(tcod.event.KeySym.SPACE), e)
    assert e.opened == "context"


def test_unmapped_key_falls_back_to_legacy_handler():
    _reset_registry()
    InputHandler.register_default_actions()
    e = StubEngine()
    # Shift+A にはレジストリバインドがない → 従来ハンドラで実績画面へ
    InputHandler.handle_event(_key(tcod.event.KeySym.A, mod=tcod.event.Modifier.SHIFT), e)
    assert e.game_state == "achievements"
