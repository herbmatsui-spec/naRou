"""Tests for wait action / turn advance (Step 3A)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecs.entity import Entity
from engine.engine import Engine
from input_actions import WaitAction
from tests.helpers.non_vacuity import assert_can_fail, assert_distinguishes


class TestWaitAdvancesWorld:
    """WaitAction.execute() が engine.pass_turn() を呼ぶことのテスト"""

    def test_wait_advances_the_world(self):
        """待機アクション実行時に pass_turn が呼ばれ、世界が進行する"""
        mock_engine = MagicMock(spec=Engine)
        mock_engine.game_state = "play"
        mock_engine.current_state = "EXPLORING"
        mock_engine.player = Entity(x=0, y=0, name="Player", char="@")
        mock_engine.survival = MagicMock()
        mock_engine.survival.pass_turn.return_value = ["自然回復: HP +1"]
        mock_engine.log = MagicMock()
        mock_engine.pass_turn = MagicMock(return_value=["ターン経過"])

        action = WaitAction()
        result = action.execute(mock_engine, None)

        assert result is True
        mock_engine.pass_turn.assert_called_once()
        mock_engine.log.assert_called_with("待機した。", (200, 200, 200))

        # Non-vacuity: pass_turn が呼ばれることを区別できる
        def _check_pass_turn_called(engine) -> None:
            if not engine.pass_turn.called:
                raise AssertionError("pass_turn was not called")

        # 正しいエンジン（pass_turn が呼ばれる）
        good_engine = MagicMock(spec=Engine)
        good_engine.game_state = "play"
        good_engine.current_state = "EXPLORING"
        good_engine.player = Entity(x=0, y=0, name="Player", char="@")
        good_engine.log = MagicMock()
        good_engine.pass_turn = MagicMock(return_value=[])

        action = WaitAction()
        action.execute(good_engine, None)
        _check_pass_turn_called(good_engine)

        # 間違った実装（pass_turn を呼ばない）をシミュレートするクラス
        class BadEngine:
            def __init__(self):
                self.game_state = "play"
                self.current_state = "EXPLORING"
                self.player = Entity(x=0, y=0, name="Player", char="@")
                self.log = MagicMock()
                self.pass_turn = MagicMock(return_value=[])
                self.advance_world = MagicMock()

        bad_engine = BadEngine()

        # 古い WaitAction 実装（advance_world を直接呼ぶ）を直接実行
        def old_wait_execute(engine, event):
            engine.log("待機した。", (200, 200, 200))
            engine.advance_world()
            return True

        # 古い実装では _check_pass_turn_called が失敗する
        old_wait_execute(bad_engine, None)
        # Non-vacuity: 古い実装だと pass_turn が呼ばれない
        assert_can_fail(
            lambda: _check_pass_turn_called(bad_engine),
            label="wait_calls_pass_turn",
        )


class TestWaitActionCanExecute:
    """WaitAction.can_execute のテスト"""

    def test_can_execute_in_play_state(self):
        """プレイ状態では実行可能"""
        mock_engine = MagicMock()
        mock_engine.game_state = "play"
        mock_engine.current_state = "EXPLORING"

        action = WaitAction()
        assert action.can_execute(mock_engine) is True

    def test_can_execute_in_exploring_state(self):
        """探索状態では実行可能"""
        from constants import GameState

        mock_engine = MagicMock()
        mock_engine.game_state = "menu"
        mock_engine.current_state = GameState.EXPLORING

        action = WaitAction()
        assert action.can_execute(mock_engine) is True

    def test_cannot_execute_in_other_state(self):
        """その他の状態では実行不可"""
        from constants import GameState

        action = WaitAction()

        mock_engine_false = MagicMock()
        mock_engine_false.game_state = "inventory"
        mock_engine_false.current_state = GameState.INVENTORY

        mock_engine_true = MagicMock()
        mock_engine_true.game_state = "play"
        mock_engine_true.current_state = "EXPLORING"

        assert action.can_execute(mock_engine_false) is False
        assert action.can_execute(mock_engine_true) is True

        # Non-vacuity: can_execute が状態によって True/False を返し分けることを区別できる
        def _check_can_execute(engine) -> None:
            if not action.can_execute(engine):
                raise AssertionError("Expected False for inventory state")

        assert_distinguishes(
            _check_can_execute,
            mock_engine_true,   # True -> pass (例外が出ない)
            mock_engine_false,  # False -> raise AssertionError
            label="wait_cannot_execute_in_inventory",
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
