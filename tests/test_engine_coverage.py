"""Engine モジュールのテストカバレッジ向上用テスト。

engine/engine.py (Engine クラス) と engine/game_state.py
(GameStateMachine, 定数) の主要パスをカバーする。

外部依存 (pygame / tcod / SDL など) を避けるため、
Engine.__init__ を通さず `__new__` でシェルインスタンスを構築し、
kernel や各種ハンドラをモックに差し替えてテストする。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from constants import GameState, GAME_STATE_TO_LEGACY
from engine.engine import Engine
from engine.game_state import (
    ALLOWED_TRANSITIONS,
    GAME_OVER,
    PLAYING,
    TITLE,
    VICTORY,
    GameStateMachine,
)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_shell_engine() -> Engine:
    """完全初期化を行わない Engine シェルインスタンスを作成する。

    kernel および各システム・ハンドラを MagicMock に差し替え、
    game_state_data にプロパティ委譲先となる属性をあらかじめ持たせる。
    これにより Engine() の重い初期化 (パッケージロード・SDL 等) を回避し、
    プロパティ委譲やメソッド委譲の主要パスを手軽に実行できる。
    """
    engine = Engine.__new__(Engine)
    engine.headless = False

    # --- Kernel: システム名 -> モック の辞書で get_system / has_system /
    # register_system を模倣。未登録名にもキャッシュされたモックを返す。 ---
    kernel = MagicMock(name="kernel")
    systems: dict[str, object] = {}
    unregistered_cache: dict[str, object] = {}

    def get_system(name: str, default=None) -> object:
        if name in systems:
            return systems[name]
        if name not in unregistered_cache:
            unregistered_cache[name] = MagicMock(name=f"system:{name}")
        return unregistered_cache[name]

    kernel.get_system.side_effect = get_system
    kernel.has_system.side_effect = lambda name: name in systems
    kernel.register_system.side_effect = lambda name, sys: systems.__setitem__(name, sys)
    engine.kernel = kernel

    # メッセージログ (history をリストにする)
    msg_log = MagicMock(name="message_log")
    msg_log.history = []
    systems["message_log"] = msg_log
    systems["survival_system"] = MagicMock(name="survival_system")
    entity_manager = MagicMock(name="entity_manager")
    entity_manager.items_on_ground = []
    entity_manager.resource_nodes = []
    entity_manager.get_entities.return_value = []
    entity_manager.get_blocked_positions.return_value = set()
    entity_manager.is_position_blocked.return_value = False
    entity_manager.get_entity_at.return_value = None
    systems["entity_manager"] = entity_manager

    # --- GameStateData (プロパティ委譲先) ---
    engine.game_state_data = SimpleNamespace(
        player=MagicMock(name="player"),
        pet=MagicMock(name="pet"),
        inventory=MagicMock(name="inventory"),
        pet_inventory=MagicMock(name="pet_inventory"),
        survival=MagicMock(name="survival"),
        game_map=MagicMock(name="game_map"),
        altar_pos=(0, 0),
        dungeon_level=1,
        quests=[],
        current_state=GameState.PLAYING,
        game_state="play",
        help_tab=0,
        inventory_target="",
        inventory_cursor=0,
        inventory_tab=0,
        active_dialogue=None,
        wish_input="",
        debug_input="",
        turns=0,
        arch_interpret_active=False,
        arch_interpret_groups_cache=[],
        arch_interpret_truth_idx=0,
        arch_interpret_ending_idx=0,
        localization_manager=MagicMock(name="localization_manager"),
        world_a_data=MagicMock(name="world_a_data"),
    )

    # --- 各種ハンドラ / マネージャー ---
    engine.systems_coordinator = MagicMock(name="systems_coordinator")
    engine.combat_handler = MagicMock(name="combat_handler")
    engine.world_handler = MagicMock(name="world_handler")
    engine.entity_handler = MagicMock(name="entity_handler")
    engine.skill_eater_handler = MagicMock(name="skill_eater_handler")
    engine.pet_handler = MagicMock(name="pet_handler")
    engine.game_loop_handler = MagicMock(name="game_loop_handler")
    engine.render_handler = MagicMock(name="render_handler")
    engine.ui_handler = MagicMock(name="ui_handler")

    # --- その他 ---
    engine.game_state_machine = GameStateMachine("playing")
    engine._harm_cause = "unknown"
    engine._harm_cause_hp = None
    engine.fx_manager = MagicMock(name="fx_manager")
    engine.localization_manager = MagicMock(name="localization_manager")
    engine.config_mgr = MagicMock(name="config_mgr")
    engine.config_mgr.get.return_value = None
    engine.notification_manager = MagicMock(name="notification_manager")
    engine.look_cursor = MagicMock(name="look_cursor")
    engine.context_menu = MagicMock(name="context_menu")
    engine.tutorial_manager = None

    return engine


@pytest.fixture
def engine() -> Engine:
    """テスト用 Engine シェルインスタンス."""
    return _make_shell_engine()


# ===========================================================================
# GameStateMachine
# ===========================================================================

class TestGameStateMachine:
    """engine/game_state.py: GameStateMachine と定数のテスト."""

    def test_default_state_is_playing(self):
        """デフォルト状態は playing."""
        m = GameStateMachine()
        assert m.current == PLAYING
        assert m.is_playing is True
        assert m.is_terminal is False

    @pytest.mark.parametrize("state", [PLAYING, GAME_OVER, VICTORY])
    def test_construct_with_known_state(self, state):
        """既知の状態で構築できる."""
        m = GameStateMachine(state)
        assert m.current == state

    def test_construct_with_unknown_state_raises(self):
        """未知の初期状態（TITLE も遷移元として登録されていない）は ValueError."""
        with pytest.raises(ValueError):
            GameStateMachine("unknown_state")
        with pytest.raises(ValueError):
            GameStateMachine(TITLE)

    @pytest.mark.parametrize("state", [GAME_OVER, VICTORY])
    def test_is_terminal_for_end_states(self, state):
        """game_over / victory は終端状態."""
        m = GameStateMachine(state)
        assert m.is_terminal is True
        assert m.is_playing is False

    def test_is_terminal_false_for_playing(self):
        """playing は終端ではない."""
        assert GameStateMachine(PLAYING).is_terminal is False

    @pytest.mark.parametrize(
        "frm,to",
        [
            (PLAYING, GAME_OVER),
            (PLAYING, VICTORY),
            (GAME_OVER, TITLE),
            (VICTORY, TITLE),
        ],
    )
    def test_can_transition_allowed(self, frm, to):
        """許可遷移は can_transition が True."""
        m = GameStateMachine(frm)
        assert m.can_transition(to) is True

    @pytest.mark.parametrize(
        "frm,to",
        [
            (PLAYING, TITLE),
            (PLAYING, PLAYING),
            (GAME_OVER, GAME_OVER),
            (GAME_OVER, PLAYING),
            (VICTORY, VICTORY),
        ],
    )
    def test_can_transition_disallowed(self, frm, to):
        """非許可遷移は can_transition が False."""
        m = GameStateMachine(frm)
        assert m.can_transition(to) is False

    @pytest.mark.parametrize(
        "frm,to",
        [
            (PLAYING, GAME_OVER),
            (GAME_OVER, TITLE),
        ],
    )
    def test_transition_records_history(self, frm, to):
        """遷移成功時に history へ (from, to, timestamp) が追加される."""
        m = GameStateMachine(frm)
        before = len(m.history)
        m.transition(to)
        assert m.current == to
        assert len(m.history) == before + 1
        frm_rec, to_rec, ts = m.history[-1]
        assert frm_rec == frm
        assert to_rec == to
        assert isinstance(ts, float)

    def test_transition_disallowed_raises_and_keeps_state(self):
        """非許可遷移は ValueError で状態は変わらない."""
        m = GameStateMachine(PLAYING)
        with pytest.raises(ValueError):
            m.transition(TITLE)
        assert m.current == PLAYING
        assert m.history == []

    def test_copy_is_independent(self):
        """__copy__ は独立したスナップショットを返す."""
        m = GameStateMachine(PLAYING)
        m.transition(GAME_OVER)
        cp = m.__copy__()
        assert cp.current == GAME_OVER
        assert len(cp.history) == 1
        cp.transition(TITLE)
        assert cp.current == TITLE
        assert m.current == GAME_OVER
        assert len(m.history) == 1

    def test_allowed_transitions_table(self):
        """ALLOWED_TRANSITIONS 定数の妥当性."""
        assert ALLOWED_TRANSITIONS[PLAYING] == frozenset({GAME_OVER, VICTORY})
        assert ALLOWED_TRANSITIONS[GAME_OVER] == frozenset({TITLE})
        assert ALLOWED_TRANSITIONS[VICTORY] == frozenset({TITLE})
        assert TITLE not in ALLOWED_TRANSITIONS


# ===========================================================================
# Engine: プロパティ委譲 (GameStateData)
# ===========================================================================

class TestEngineGameStateDataDelegation:
    """Engine プロパティが game_state_data へ委譲されること."""

    def test_player_property(self):
        engine = _make_shell_engine()
        assert engine.player is engine.game_state_data.player

    def test_pet_property(self):
        engine = _make_shell_engine()
        assert engine.pet is engine.game_state_data.pet

    def test_inventory_property(self):
        engine = _make_shell_engine()
        assert engine.inventory is engine.game_state_data.inventory

    def test_pet_inventory_property(self):
        engine = _make_shell_engine()
        assert engine.pet_inventory is engine.game_state_data.pet_inventory

    def test_survival_property(self):
        engine = _make_shell_engine()
        # survival はカーネル登録済みシステムを優先して返す
        assert engine.survival is engine.kernel.get_system("survival_system")

    def test_systems_mgr_property(self):
        engine = _make_shell_engine()
        assert engine.systems_mgr is engine.systems_coordinator

    def test_dungeon_level_property(self):
        engine = _make_shell_engine()
        assert engine.dungeon_level == 1
        engine.dungeon_level = 3
        assert engine.dungeon_level == 3

    def test_game_map_property(self):
        engine = _make_shell_engine()
        assert engine.game_map is engine.game_state_data.game_map

    def test_altar_pos_property(self):
        engine = _make_shell_engine()
        assert engine.altar_pos == (0, 0)
        engine.altar_pos = (5, 6)
        assert engine.altar_pos == (5, 6)

    def test_entities_property(self):
        engine = _make_shell_engine()
        assert engine.entities == []

    def test_items_on_ground_property(self):
        engine = _make_shell_engine()
        assert engine.items_on_ground == []

    def test_resource_nodes_property(self):
        engine = _make_shell_engine()
        assert engine.resource_nodes == []

    def test_quests_property(self):
        engine = _make_shell_engine()
        assert engine.quests == []

    def test_current_state_property(self):
        engine = _make_shell_engine()
        assert engine.current_state is GameState.PLAYING

    def test_game_state_property(self):
        engine = _make_shell_engine()
        assert engine.game_state == "play"
        engine.game_state = "skill_tree"
        assert engine.game_state == "skill_tree"

    def test_help_tab_property(self):
        engine = _make_shell_engine()
        engine.help_tab = 2
        assert engine.help_tab == 2

    def test_inventory_target_property(self):
        engine = _make_shell_engine()
        engine.inventory_target = "slot"
        assert engine.inventory_target == "slot"

    def test_inventory_cursor_property(self):
        engine = _make_shell_engine()
        engine.inventory_cursor = 3
        assert engine.inventory_cursor == 3

    def test_inventory_tab_property(self):
        engine = _make_shell_engine()
        engine.inventory_tab = 1
        assert engine.inventory_tab == 1

    def test_active_dialogue_property(self):
        engine = _make_shell_engine()
        engine.active_dialogue = ("npc", "hello")
        assert engine.active_dialogue == ("npc", "hello")

    def test_wish_input_property(self):
        engine = _make_shell_engine()
        engine.wish_input = "wish"
        assert engine.wish_input == "wish"

    def test_debug_input_property(self):
        engine = _make_shell_engine()
        engine.debug_input = "cmd"
        assert engine.debug_input == "cmd"

    def test_turns_property(self):
        engine = _make_shell_engine()
        engine.turns = 42
        assert engine.turns == 42

    def test_arch_interpret_properties(self):
        engine = _make_shell_engine()
        engine.arch_interpret_active = True
        engine.arch_interpret_groups_cache = [{"a": 1}]
        engine.arch_interpret_truth_idx = 2
        engine.arch_interpret_ending_idx = 1
        assert engine.arch_interpret_active is True
        assert engine.arch_interpret_groups_cache == [{"a": 1}]
        assert engine.arch_interpret_truth_idx == 2
        assert engine.arch_interpret_ending_idx == 1

    def test_last_scan_result_property(self):
        engine = _make_shell_engine()
        assert engine.last_scan_result is None
        engine.last_scan_result = {"rate": 0.5}
        assert engine.last_scan_result == {"rate": 0.5}

    def test_territory_state_property(self, monkeypatch):
        """territory_state は TerritoryState.get_instance() を返す."""
        fake = MagicMock(name="TerritoryState")
        monkeypatch.setattr(
            "skill_eater_territory_system.TerritoryState.get_instance",
            lambda: fake,
        )
        engine = _make_shell_engine()
        assert engine.territory_state is fake

    def test_territory_state_setter(self, monkeypatch):
        """territory_state セッターは TerritoryState._instance を書き換える."""
        fake = MagicMock(name="TerritoryState")
        fake._instance = None
        monkeypatch.setattr("skill_eater_territory_system.TerritoryState", fake)
        engine = _make_shell_engine()
        engine.territory_state = "stored"
        assert fake._instance == "stored"


# ===========================================================================
# Engine: カーネルシステムアクセサ
# ===========================================================================

class TestEngineKernelAccessors:
    """Engine のカーネルシステムアクセサプロパティ."""

    @pytest.mark.parametrize(
        "accessor_name",
        [
            "event_bus",
            "time_system",
            "turn_queue",
            "combat_system",
            "survival_system",
            "starter_items_factory",
            "dungeon_spawner",
            "gameplay_loop",
            "skill_tree_manager",
            "job_manager",
            "skill_fusion_manager",
            "skill_evolution_manager",
            "skill_awakening_manager",
            "skill_transfer_manager",
            "skill_resonance_manager",
            "skill_inheritance_manager",
            "skill_specialization_manager",
            "player_pet_initializer",
            "guild_manager",
            "guild_quest_manager",
            "faction_war_manager",
            "guild_skill_manager",
            "pet_contract_manager",
            "pet_evolution_manager",
            "pet_fusion_manager",
            "relationship_manager",
            "procedural_quest_manager",
            "quest_scheduler",
            "achievement_manager",
            "reincarnation_manager",
            "inheritance_manager",
            "karma_manager",
            "reincarnation_dungeon_manager",
            "legacy_skill_manager",
            "challenge_manager",
            "meta_progression_manager",
            "title_manager",
            "procedural_dungeon_generator",
            "world_event_manager",
            "archaeology_manager",
            "world_state_manager",
            "dungeon_theme_registry",
            "storyteller_manager",
            "choice_manager",
            "dialogue_manager",
            "main_quest_system",
            "journal_ui",
            "web_server_factory",
            "input_handler",
        ],
    )
    def test_accessor_returns_kernel_registered_system(self, engine, accessor_name):
        """各アクセサはカーネルに登録されたシステムを返す."""
        result = getattr(engine, accessor_name)
        assert result is engine.kernel.get_system(accessor_name)

    def test_skill_eater_optional_accessors_return_none_when_unregistered(self):
        """スキルイーター関連オプションアクセサは未登録時 None."""
        engine = _make_shell_engine()
        engine.kernel.has_system.return_value = False
        for name in [
            "skill_eater_combat_system",
            "skill_eater_registry",
            "skill_eater_synthesis_system",
            "skill_eater_toxicity_manager",
            "slum_base_expansion_manager",
            "skill_eater_pet_dispatch_manager",
            "skill_eater_underground_arena",
            "skill_eater_bounty_system",
            "skill_eater_ascension_board",
            "skill_eater_concept_crystal",
            "skill_eater_temporal_vault",
            "skill_eater_epilogue_manager",
            "skill_eater_meta_intervention",
            "skill_eater_intervention_engine",
            "skill_eater_exploration_system",
        ]:
            assert getattr(engine, name) is None


# ===========================================================================
# Engine: スキルイーター委譲メソッド
# ===========================================================================

class TestEngineSkillEaterDelegation:
    """Engine のスキルイーター系メソッドがハンドラへ委譲されること."""

    def test_execute_scan(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_scan.return_value = True
        assert engine.execute_scan() is True
        engine.skill_eater_handler.execute_scan.assert_called_once_with()

    def test_execute_devour(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_devour.return_value = False
        assert engine.execute_devour() is False
        engine.skill_eater_handler.execute_devour.assert_called_once_with()

    def test_execute_synthesis(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_synthesis.return_value = True
        assert engine.execute_synthesis("fire_bolt", "ice_bolt") is True
        engine.skill_eater_handler.execute_synthesis.assert_called_once_with(
            "fire_bolt", "ice_bolt"
        )

    def test_execute_pet_dispatch(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_pet_dispatch.return_value = True
        assert engine.execute_pet_dispatch("herb_fetch", 15, 700) is True
        engine.skill_eater_handler.execute_pet_dispatch.assert_called_once_with(
            "herb_fetch", 15, 700
        )

    def test_execute_base_upgrade_default_cost(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_base_upgrade.return_value = True
        assert engine.execute_base_upgrade("well") is True
        engine.skill_eater_handler.execute_base_upgrade.assert_called_with("well", 1000)

    def test_execute_solve_puzzle(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_solve_puzzle.return_value = True
        assert engine.execute_solve_puzzle("lever", "teleport") is True
        engine.skill_eater_handler.execute_solve_puzzle.assert_called_once_with(
            "lever", "teleport"
        )

    def test_switch_world(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.switch_world.return_value = True
        assert engine.switch_world("world_a") is True
        engine.skill_eater_handler.switch_world.assert_called_once_with("world_a")

    def test_execute_epilogue_world_transition(self):
        engine = _make_shell_engine()
        engine.skill_eater_handler.execute_epilogue_world_transition.return_value = True
        assert engine.execute_epilogue_world_transition() is True


# ===========================================================================
# Engine: ログ・状態・ダイアログ・クエスト進行
# ===========================================================================

class TestEngineLogAndState:
    """Engine.log / change_state / open_journal / open_context_menu / 進行."""

    def test_log_routes_to_msg_log(self, engine):
        """log は msg_log.add へ転送する."""
        engine.log("テストメッセージ", (255, 0, 0), level="ERROR")
        engine.msg_log.add.assert_called_once_with(
            "テストメッセージ", (255, 0, 0), level="ERROR"
        )

    def test_check_tutorial_triggers_no_manager(self, engine):
        """tutorial_manager が無い場合は None."""
        del engine.tutorial_manager
        assert engine.check_tutorial_triggers("game_start") is None

    def test_check_tutorial_triggers_with_guide(self, engine):
        """チュートリアルガイドが返った場合はログ・ポップアップを設定する."""
        engine.tutorial_manager = MagicMock(name="tutorial_manager")
        guide = MagicMock(name="guide")
        guide.id = "tut_1"
        guide.title = "タイトル"
        guide.message = "メッセージ"
        guide.to_dict.return_value = {"id": "tut_1"}
        engine.tutorial_manager.check_triggers.return_value = guide
        engine.log = MagicMock(name="log")
        engine.player = MagicMock(name="player")
        engine.player.completed_tutorials = MagicMock()
        engine.player.pending_tutorial_popup = None

        result = engine.check_tutorial_triggers("game_start")

        assert result is guide
        engine.player.completed_tutorials.add.assert_called_once_with("tut_1")
        assert engine.player.pending_tutorial_popup == {"id": "tut_1"}
        engine.log.assert_called_once()
        assert "ガイド" in engine.log.call_args[0][0]
        engine.notification_manager.notify.assert_called_once()

    def test_change_state_transitions(self, engine):
        """change_state は StateMachine 経由で遷移し legacy 文字列を同期する."""
        engine.change_state(GameState.MENU)
        assert engine.game_state_data.current_state is GameState.MENU
        assert engine.game_state_data.game_state == GAME_STATE_TO_LEGACY[GameState.MENU]

    def test_open_journal_toggles(self, engine):
        """open_journal は journal_ui.toggle を呼び state を同期する."""
        journal = MagicMock(name="journal_ui")
        journal.visible = True
        engine.kernel.register_system("journal_ui", journal)

        engine.open_journal()
        journal.toggle.assert_called_once_with()
        assert engine.game_state_data.game_state == "journal"

        journal.visible = False
        engine.open_journal()
        assert journal.toggle.call_count == 2
        assert engine.game_state_data.game_state == "play"

    def test_open_context_menu_with_actions(self, engine):
        """open_context_menu はアクションがあればコンテキストメニューを設定する."""
        builder = MagicMock(name="ContextMenuBuilder")
        builder.build_actions.return_value = ["act1"]
        import managers.context_menu_builder as cmb

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(cmb, "ContextMenuBuilder", lambda: builder)
        try:
            engine.context_menu = MagicMock(name="context_menu")
            engine.open_context_menu()
            engine.context_menu.set_actions.assert_called_once_with(["act1"])
            assert engine.game_state_data.game_state == "context"
        finally:
            monkeypatch.undo()

    def test_open_context_menu_no_actions_logs(self, engine):
        """アクションがない場合はログを出力する."""
        import managers.context_menu_builder as cmb

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            cmb,
            "ContextMenuBuilder",
            lambda: MagicMock(build_actions=MagicMock(return_value=[])),
        )
        try:
            engine.open_context_menu()
            engine.msg_log.add.assert_called_once()
            args, kwargs = engine.msg_log.add.call_args
            assert args[0] == "周囲にアクション可能な対象がない。"
        finally:
            monkeypatch.undo()


# ===========================================================================
# Engine: プレイヤー行動・世界進行・更新
# ===========================================================================

class TestEnginePlayerActAndWorld:
    """player_act / advance_world / update / pass_turn."""

    def test_player_act_blocked_after_game_over(self, engine):
        """ゲームオーバー後は player_act を受け付けない."""
        engine.game_state_machine = GameStateMachine("game_over")
        assert engine.player_act(1, 0) is False
        queried = [c.args[0] for c in engine.kernel.get_system.call_args_list]
        assert "gameplay_loop" not in queried

    def test_player_act_delegates_to_gameplay_loop(self, engine):
        """playing 状態では gameplay_loop システムへ委譲する."""
        engine.game_state_machine = GameStateMachine("playing")
        loop_factory = MagicMock(name="gameplay_loop")
        loop_factory.return_value.player_act.return_value = True
        engine.kernel.register_system("gameplay_loop", loop_factory)

        assert engine.player_act(1, 0) is True
        loop_factory.assert_called_once_with(engine.kernel, engine)
        loop_factory.return_value.player_act.assert_called_once_with(1, 0)

    def test_advance_world_delegates(self, engine):
        """advance_world は game_loop_handler.advance_world へ委譲する."""
        engine.advance_world()
        engine.game_loop_handler.advance_world.assert_called_once_with()

    def test_update_delegates(self, engine):
        """update は game_loop_handler.update へ委譲する."""
        engine.update(0.5)
        engine.game_loop_handler.update.assert_called_once_with(0.5)

    def test_pass_turn(self, engine):
        """pass_turn は survival.pass_turn と advance_world を実行する."""
        engine.survival.pass_turn.return_value = ["log1"]
        logs = engine.pass_turn()
        engine.survival.pass_turn.assert_called_once_with(engine.player, engine)
        engine.game_loop_handler.advance_world.assert_called_once_with()
        assert logs == ["log1"]

    def test_pass_turn_without_survival(self, engine):
        """survival が偽の場合は世界進行のみ行う."""
        # survival_system を未登録にし game_state_data.survival も偽にする
        engine.game_state_data.survival = None
        # get_system が survival_system で None を返すよう差し替え
        orig_get_system = engine.kernel.get_system.side_effect

        def get_system(name, default=None):
            if name == "survival_system":
                return None
            return orig_get_system(name, default)

        engine.kernel.get_system.side_effect = get_system
        logs = engine.pass_turn()
        engine.game_loop_handler.advance_world.assert_called_once_with()
        assert logs == []


# ===========================================================================
# Engine: その他の委譲メソッド
# ===========================================================================

class TestEngineOtherDelegation:
    """_on_player_death / _on_kill / 判定系 / 描画早期リターンなど."""

    def test_on_player_death(self, engine):
        engine._on_player_death()
        engine.game_loop_handler._on_player_death.assert_called_once_with()

    def test_on_kill(self, engine):
        entity = MagicMock(name="entity")
        engine._on_kill(entity)
        engine.combat_handler.handle_kill.assert_called_once_with(entity)

    def test_progress_generated_quests_silent_no_manager(self, engine):
        """procedural_quest_manager が無い場合は何もしない."""
        engine.player = None
        assert engine._progress_generated_quests("kill", "goblin") is None

    def test_progress_generated_quests_logs_messages(self, engine):
        """クエスト進行メッセージをログ出力する."""
        mgr = MagicMock(name="procedural_quest_manager")
        mgr.update_progress.return_value = ["進捗A", "進捗B"]
        engine.kernel.register_system("procedural_quest_manager", mgr)
        engine.player = MagicMock(name="player")

        result = engine._progress_generated_quests("kill", "goblin", 3)

        assert result is None
        mgr.update_progress.assert_called_once_with(
            engine.player, "kill", "goblin", 3, engine
        )
        assert engine.msg_log.add.call_count == 2
        first_call = engine.msg_log.add.call_args_list[0]
        assert first_call.args == ("進捗A", (255, 215, 0))
        assert first_call.kwargs == {"level": "SUCCESS"}

    def test_has_los(self, engine):
        """has_los は Bresenham 線上の中間点が不透明でないか判定する."""
        from core_framework import Point

        engine.game_map.is_transparent.return_value = True
        assert engine.has_los(Point(0, 0), Point(2, 2)) is True

    def test_get_blocked_positions(self, engine):
        engine.get_blocked_positions()
        engine.entity_manager.get_blocked_positions.assert_called_once_with()

    def test_is_tile_free(self, engine):
        engine.game_map.is_walkable.return_value = True
        engine.entity_manager.is_position_blocked.return_value = False
        assert engine.is_tile_free(1, 2) is True

    def test_get_entity_at(self, engine):
        ent = MagicMock(name="ent")
        engine.entity_manager.get_entity_at.return_value = ent
        assert engine.get_entity_at(1, 2) is ent

    def test_check_win_condition(self, engine):
        engine.world_handler.check_win_condition.return_value = True
        assert engine.check_win_condition() is True

    def test_render_to_text_early_return_no_player(self, engine):
        """player が無い場合は "Loading..." を描画して早期リターンする."""
        engine.game_state_data.player = None
        tr = MagicMock(name="text_renderer")
        tr.height = 10
        tr.width = 20
        engine.render_to_text(tr)
        tr.clear.assert_called_once_with()
        tr.draw_text.assert_called_with(0, 0, "Loading...", (255, 255, 255))
        tr.present.assert_called_once_with()

    def test_render_to_text_early_return_no_game_map(self, engine):
        """game_map が無い場合は "Loading..." を描画して早期リターンする."""
        engine.game_state_data.game_map = None
        tr = MagicMock(name="text_renderer")
        tr.height = 10
        tr.width = 20
        engine.render_to_text(tr)
        tr.draw_text.assert_called_with(0, 0, "Loading...", (255, 255, 255))

    def test_render_delegates(self, engine):
        console = MagicMock(name="console")
        engine.render(console)
        engine.render_handler.render.assert_called_once_with(console)

    def test_cast_fireball(self, engine):
        engine.cast_fireball()
        engine.combat_handler.cast_fireball.assert_called_once_with()

    def test_mine_wall(self, engine):
        engine.mine_wall()
        engine.ui_handler.mine_wall.assert_called_once_with()

    def test_excavate(self, engine):
        engine.excavate()
        engine.ui_handler.excavate.assert_called_once_with()

    def test_pet_actions(self, engine):
        engine.play_music()
        engine.pray()
        engine.offer_altar()
        engine.use_wish_rod()
        engine.use_pet_evolution_stone()
        engine.use_alchemy_lab()
        engine.confirm_wish()
        engine.pet_handler.play_music.assert_called_once_with()
        engine.pet_handler.pray.assert_called_once_with()
        engine.pet_handler.offer_altar.assert_called_once_with()
        engine.pet_handler.use_wish_rod.assert_called_once_with()
        engine.pet_handler.use_pet_evolution_stone.assert_called_once_with()
        engine.pet_handler.use_alchemy_lab.assert_called_once_with()
        engine.pet_handler.confirm_wish.assert_called_once_with()

    def test_descend_stairs(self, engine):
        engine.descend_stairs()
        engine.world_handler.descend_stairs.assert_called_once_with()

    def test_check_reincarnation_option_and_reincarnate(self, engine):
        engine.ui_handler.check_reincarnation_option.return_value = True
        assert engine.check_reincarnation_option() is True
        engine.reincarnate()
        engine.ui_handler.reincarnate.assert_called_once_with()

    def test_help_friend(self, engine):
        engine.help_friend()
        engine.ui_handler.help_friend.assert_called_once_with()


# ===========================================================================
# Engine: モジュールレベル関数
# ===========================================================================

class TestModuleLevelFunctions:
    """_declared_skill_ids / _character_state_from_entity など."""

    def test_declared_skill_ids_empty(self):
        """_skills が無いエンティティは空リスト."""
        entity = MagicMock(name="entity")
        del entity._skills
        from engine.engine import _declared_skill_ids

        assert _declared_skill_ids(entity) == []

    def test_declared_skill_ids_dict(self):
        """_skills が dict ならキーのリスト."""
        entity = MagicMock(name="entity")
        entity._skills = {"fire": 1, "ice": 2}
        from engine.engine import _declared_skill_ids

        assert sorted(_declared_skill_ids(entity)) == ["fire", "ice"]

    def test_declared_skill_ids_list(self):
        """_skills がリストなら id 文字列のリスト."""
        entity = MagicMock(name="entity")
        entity._skills = ["fire", "ice"]
        from engine.engine import _declared_skill_ids

        assert sorted(_declared_skill_ids(entity)) == ["fire", "ice"]
