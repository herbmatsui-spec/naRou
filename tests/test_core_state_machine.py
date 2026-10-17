"""core/state_machine.py (StateMachine) の単体テスト。

状態遷移と on_exit/on_enter フックをスタブエンジンで検証する。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from constants import GameState
from core.state_machine import StateMachine


class _StubEngine:
    """StateMachine.apply が触れる属性のみを持つスタブエンジン。"""

    def __init__(self, current_state: GameState, **overrides) -> None:
        self.current_state = current_state
        self.active_dialogue = ("シエル", "こんにちは！")
        self.inventory_cursor = 5
        self.game_state = None
        self.look_cursor = SimpleNamespace(active=True)
        self.__dict__.update(overrides)


class TestApply:
    """StateMachine.apply をテストする。"""

    def test_same_state_returns_early(self):
        """同一状態への遷移は何もしない（早期リターン）。"""
        engine = _StubEngine(GameState.DIALOGUE)
        before_dialogue = engine.active_dialogue
        StateMachine().apply(engine, GameState.DIALOGUE)
        assert engine.current_state == GameState.DIALOGUE
        assert engine.active_dialogue == before_dialogue

    def test_dialogue_exit_clears_active_dialogue(self):
        """dialogue から離れるとき active_dialogue を None にする。"""
        engine = _StubEngine(GameState.DIALOGUE)
        StateMachine().apply(engine, GameState.MENU)
        assert engine.current_state == GameState.MENU
        assert engine.active_dialogue is None

    def test_menu_exit_resets_inventory_cursor(self):
        """menu から離れるとき inventory_cursor を 0 にする。"""
        engine = _StubEngine(GameState.MENU, inventory_cursor=7)
        StateMachine().apply(engine, GameState.EXPLORING)
        assert engine.current_state == GameState.EXPLORING
        assert engine.inventory_cursor == 0

    def test_exit_hook_only_applies_to_dialogue_and_menu(self):
        """exploring/paused などの終了時は特別なクリーンアップを行わない。"""
        engine = _StubEngine(GameState.EXPLORING, active_dialogue=None)
        StateMachine().apply(engine, GameState.MENU)
        assert engine.inventory_cursor == 5  # 変更なし

    def test_game_state_legacy_sync(self):
        """GAME_STATE_TO_LEGACY で game_state を双方向同期する。"""
        engine = _StubEngine(GameState.EXPLORING)
        StateMachine().apply(engine, GameState.DIALOGUE)
        assert engine.game_state == "talk"

        engine = _StubEngine(GameState.EXPLORING)
        StateMachine().apply(engine, GameState.MENU)
        assert engine.game_state == "menu"

        engine = _StubEngine(GameState.EXPLORING)
        StateMachine().apply(engine, GameState.COMBAT)
        assert engine.game_state == "combat"

    def test_menu_enter_deactivates_look_cursor(self):
        """menu へ遷移時、look_cursor があれば active = False にする。"""
        look_cursor = SimpleNamespace(active=True)
        engine = _StubEngine(GameState.EXPLORING, look_cursor=look_cursor)
        StateMachine().apply(engine, GameState.MENU)
        assert look_cursor.active is False

    def test_menu_enter_without_look_cursor_does_not_fail(self):
        """look_cursor を持たないエンジンでも menu 遷移は成功する。"""
        engine = _StubEngine(GameState.EXPLORING)
        del engine.look_cursor
        StateMachine().apply(engine, GameState.MENU)
        assert engine.current_state == GameState.MENU

    @pytest.mark.parametrize(
        "new_state,expected_legacy",
        [
            (GameState.PLAYING, "play"),
            (GameState.PAUSED, "paused"),
            (GameState.MENU, "menu"),
            (GameState.DIALOGUE, "talk"),
            (GameState.COMBAT, "combat"),
            (GameState.EVENT, "event"),
        ],
    )
    def test_legacy_mapping_various_states(self, new_state, expected_legacy):
        """各ゲーム状態に対応する legacy 文字列へ同期する。"""
        engine = _StubEngine(GameState.EXPLORING)
        StateMachine().apply(engine, new_state)
        assert engine.game_state == expected_legacy
