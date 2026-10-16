"""改善案6: 未統合システムのゲームループ配線テスト。

- Engine.pass_turn にメタ介入システムトリガーを配線
- Engine.descend_stairs に考古学デコーダーフラグメント発見チェックを配線
- Engine.reincarnate に再転生システムを配線
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch, PropertyMock

import pytest

from engine.engine import Engine


class TestImprovement6MetaInterventionWiring:
    """pass_turn にメタ介入システムトリガーが配線されていること"""

    def setup_method(self) -> None:
        self.engine = Engine(headless=True)
        self.engine.survival = SimpleNamespace()
        self.engine.survival.pass_turn = lambda p, e: []
        self.engine.advance_world = lambda: None

    def test_pass_turn_runs_without_intervention_system(self) -> None:
        """skill_eater_meta_intervention が None でも pass_turn は正常終了すること"""
        with patch.object(
            Engine, "skill_eater_meta_intervention", new_callable=PropertyMock, return_value=None
        ):
            logs = self.engine.pass_turn()
        assert isinstance(logs, list)

    def test_pass_turn_calls_intervention_check_event(self) -> None:
        """check_event を持つメタ介入システムが呼ばれること"""
        class FakeIntervention:
            def check_event(self, player, turns):
                return "メタ介入イベント発生!"

        with patch.object(
            Engine,
            "skill_eater_meta_intervention",
            new_callable=PropertyMock,
            return_value=FakeIntervention(),
        ):
            logs = self.engine.pass_turn()
        assert any("メタ介入イベント発生" in log for log in logs)


class TestImprovement6ArchaeologyWiring:
    """descend_stairs に考古学デコーダーフックが配線されていること"""

    def setup_method(self) -> None:
        self.engine = Engine(headless=True)

    def test_descend_stairs_calls_archaeology_discovery(self) -> None:
        """descend_stairs 実行時に考古学デコーダーチェックが呼ばれること"""
        self.engine.world_handler = SimpleNamespace()
        self.engine.world_handler.descend_stairs = lambda: None

        player = SimpleNamespace()
        player.archaeology = SimpleNamespace()
        self.engine.player = player

        class FakeDecoder:
            def get_all_fragments_state(self, entity):
                return [{"id": "frag_01", "name": "古代の断片", "is_decoded": False}]

        self.engine.kernel.register_system("archaeology_decoder", FakeDecoder())

        self.engine.descend_stairs()

    def test_descend_stairs_without_archaeology_component(self) -> None:
        """プレイヤーに archaeology コンポーネントがない場合は何もしないこと"""
        self.engine.world_handler = SimpleNamespace()
        self.engine.world_handler.descend_stairs = lambda: None
        self.engine.player = SimpleNamespace()

        self.engine.descend_stairs()


class TestImprovement6ReincarnationWiring:
    """reincarnate に再転生システムが配線されていること"""

    def setup_method(self) -> None:
        self.engine = Engine(headless=True)

    def test_reincarnate_uses_reincarnation_manager(self) -> None:
        """reincarnate 実行時に reincarnation_manager.reincarnate が呼ばれること"""
        player = SimpleNamespace()
        self.engine.player = player

        class FakeReincarnationManager:
            def reincarnate(self, player, engine):
                self.called = True
                self.player_arg = player
                self.engine_arg = engine

        mgr = FakeReincarnationManager()
        with patch.object(
            Engine, "reincarnation_manager", new_callable=PropertyMock, return_value=mgr
        ):
            self.engine.reincarnate()

        assert mgr.called is True
        assert mgr.player_arg is player
        assert mgr.engine_arg is self.engine

    def test_reincarnate_falls_back_to_ui_handler(self) -> None:
        """reincarnation_manager がない場合は ui_handler.reincarnate にフォールバックすること"""
        player = SimpleNamespace()
        self.engine.player = player

        class FakeUIHandler:
            def reincarnate(self):
                self.called = True

        self.engine.ui_handler = FakeUIHandler()
        with patch.object(
            Engine, "reincarnation_manager", new_callable=PropertyMock, return_value=None
        ):
            self.engine.reincarnate()

        assert self.engine.ui_handler.called is True
