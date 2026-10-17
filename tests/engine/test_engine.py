"""Unit tests for engine/engine.py - Core engine implementation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from constants import GAME_STATE_TO_LEGACY, GameState
from ecs.entity import Entity
from engine.engine import Engine
from engine.game_state import GameStateMachine


class TestEngineInitialization:
    """Tests for Engine initialization."""

    def test_engine_creates(self):
        """Engine initializes without errors."""
        engine = Engine()

        assert engine is not None

    def test_engine_has_kernel(self):
        """Engine has kernel attribute."""
        engine = Engine()

        assert hasattr(engine, "kernel")

    def test_engine_has_player(self):
        """Engine has player attribute."""
        engine = Engine()

        assert hasattr(engine, "player")

    def test_engine_has_entity_manager(self):
        """Engine has entity_manager attribute."""
        engine = Engine()

        assert hasattr(engine, "entity_manager")

    def test_engine_has_dungeon_level(self):
        """Engine has dungeon_level attribute."""
        engine = Engine()

        assert hasattr(engine, "dungeon_level")
        assert engine.dungeon_level == 1

    def test_engine_has_turns(self):
        """Engine has turns attribute."""
        engine = Engine()

        assert hasattr(engine, "turns")
        assert engine.turns == 0


class TestEngineLogging:
    """Tests for Engine logging functionality."""

    def test_log_method_exists(self):
        """Engine has log method."""
        engine = Engine()

        assert hasattr(engine, "log")
        assert callable(engine.log)

    def test_log_accepts_message(self):
        """Log method accepts message and color."""
        engine = Engine()
        # Should not raise
        engine.log("Test message", (255, 255, 255))

    def test_log_accepts_color(self):
        """Log method accepts color tuple."""
        engine = Engine()
        engine.log("Test", (255, 0, 0))
        engine.log("Test", (0, 255, 0))
        engine.log("Test", (0, 0, 255))


class TestEngineSystems:
    """Tests for Engine system management."""

    def test_engine_has_systems(self):
        """Engine has registered systems."""
        engine = Engine()

        # Check for key systems
        assert engine.kernel.has_system("event_bus")
        assert engine.kernel.has_system("entity_manager")

    def test_get_system(self):
        """Engine can retrieve systems."""
        engine = Engine()

        event_bus = engine.kernel.get_system("event_bus")
        assert event_bus is not None

        entity_mgr = engine.kernel.get_system("entity_manager")
        assert entity_mgr is not None


class TestEnginePlayer:
    """Tests for Engine player management."""

    def test_player_is_entity(self):
        """Player is an Entity instance."""
        engine = Engine()

        from ecs.entity import Entity
        assert isinstance(engine.player, Entity)

    def test_player_has_name(self):
        """Player has name attribute."""
        engine = Engine()

        assert hasattr(engine.player, "name")

    def test_player_is_player_flag(self):
        """Player has is_player flag set."""
        engine = Engine()

        assert engine.player.is_player is True


class TestEngineDungeon:
    """Tests for Engine dungeon management."""

    def test_dungeon_level_starts_at_1(self):
        """Dungeon level starts at 1."""
        engine = Engine()

        assert engine.dungeon_level == 1

    def test_dungeon_level_can_increase(self):
        """Dungeon level can be modified."""
        engine = Engine()
        engine.dungeon_level = 5

        assert engine.dungeon_level == 5


class TestEngineTurns:
    """Tests for Engine turn management."""

    def test_turns_start_at_zero(self):
        """Turns start at 0."""
        engine = Engine()

        assert engine.turns == 0

    def test_turns_can_increment(self):
        """Turns can be incremented."""
        engine = Engine()
        engine.turns = 10

        assert engine.turns == 10


class TestEngineQuests:
    """Tests for Engine quest management."""

    def test_quests_list_exists(self):
        """Engine has quests list."""
        engine = Engine()

        assert hasattr(engine, "quests")
        assert isinstance(engine.quests, list)

    def test_quests_can_add(self):
        """Quests can be added to engine."""
        engine = Engine()

        class MockQuest:
            def __init__(self):
                self.completed = False
                self.target_monster = "goblin"
                self.target_count = 10
                self.current_count = 0
                self.reward_gold = 100
                self.reward_platinum = 1

        initial_count = len(engine.quests)
        quest = MockQuest()
        engine.quests.append(quest)

        assert len(engine.quests) == initial_count + 1
        assert engine.quests[-1] is quest


class TestEngineSurvival:
    """Tests for Engine survival system."""

    def test_survival_system_exists(self):
        """Engine has survival system."""
        engine = Engine()

        assert hasattr(engine, "survival")

    def test_survival_has_gold(self):
        """Survival system has gold attribute."""
        engine = Engine()

        assert hasattr(engine.survival, "gold")
        assert engine.survival.gold == 0


class TestEngineShutdown:
    """Tests for Engine shutdown hook."""

    def test_shutdown_hook_registered(self):
        """Engine registers shutdown hook."""
        engine = Engine()

        # The shutdown hook should be registered via atexit
        import atexit
        # Just verify engine can be created and destroyed
        del engine


class TestEngineAdvanceWorld:
    """Tests for advance_world functionality."""

    def test_advance_world_method_exists(self):
        """Engine has advance_world method."""
        engine = Engine()

        assert hasattr(engine, "advance_world")
        assert callable(engine.advance_world)


# =============================================================================
# Shared fixtures / helpers for the delegation-focused test classes below
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    """Fully initialized Engine shared by the tests in this module.

    Engine() boots the full kernel package stack and is comparatively
    expensive, so one instance is reused. Tests that mutate shared state
    (dungeon_level, turns, quests) must restore it.
    """
    return Engine()


def _make_shell_engine() -> Engine:
    """Engine built via __new__ (no full init) with a mocked kernel.

    Attributes are assigned manually so property delegation can be exercised
    against configurable kernel systems without booting the real stack.
    """
    engine = Engine.__new__(Engine)
    kernel = MagicMock(name="kernel")
    systems: dict[str, object] = {}
    kernel.get_system.side_effect = lambda name, default=None: systems.get(name, default)
    kernel.has_system.side_effect = lambda name: name in systems
    kernel.register_system.side_effect = lambda name, system: systems.__setitem__(name, system)
    engine.kernel = kernel
    engine.game_state_data = SimpleNamespace(current_state=GameState.PLAYING, game_state="play")
    engine.player = MagicMock(name="player")
    engine.log = MagicMock(name="log")
    return engine


class TestEngineStateProperties:
    """Tests for Engine property delegation to GameStateData (engine.py 329-631)."""

    def test_player_property_returns_game_state_data_player(self, engine):
        """player property delegates to game_state_data.player."""
        assert engine.player is engine.game_state_data.player
        assert isinstance(engine.player, Entity)
        assert engine.player.is_player is True

    def test_inventory_property_delegates(self, engine):
        """inventory property returns the game state inventory object."""
        assert engine.inventory is engine.game_state_data.inventory
        assert hasattr(engine.inventory, "items")

    def test_survival_property_prefers_kernel_registered_system(self, engine):
        """survival returns the kernel-registered survival_system object."""
        assert engine.survival is engine.kernel.get_system("survival_system")
        assert engine.survival is engine.game_state_data.survival
        assert hasattr(engine.survival, "gold")

    def test_game_map_property_delegates(self, engine):
        """game_map property delegates to game_state_data.game_map."""
        assert engine.game_map is not None
        assert engine.game_map is engine.game_state_data.game_map

    def test_entities_property_returns_entity_manager_contents(self, engine):
        """entities property returns entity_manager.get_entities()."""
        entities = engine.entities
        assert isinstance(entities, list)
        assert engine.player in entities
        assert engine.pet in entities

    def test_quests_property_returns_list(self, engine):
        """quests property delegates to game_state_data.quests."""
        assert isinstance(engine.quests, list)
        assert engine.quests is engine.game_state_data.quests

    def test_current_state_property_is_game_state_enum(self, engine):
        """current_state property returns a GameState enum member."""
        assert isinstance(engine.current_state, GameState)
        assert engine.current_state is engine.game_state_data.current_state

    def test_dungeon_level_setter_roundtrip(self, engine):
        """dungeon_level setter writes through to game state data."""
        original = engine.dungeon_level
        try:
            engine.dungeon_level = 7
            assert engine.dungeon_level == 7
            assert engine.game_state_data.dungeon_level == 7
        finally:
            engine.dungeon_level = original

    def test_turns_setter_roundtrip(self, engine):
        """turns setter writes through to game state data."""
        original = engine.turns
        try:
            engine.turns = 99
            assert engine.turns == 99
            assert engine.game_state_data.turns == 99
        finally:
            engine.turns = original


class TestEngineKernelAccessors:
    """Tests for the kernel system accessor properties (engine.py 633-1008)."""

    def test_kernel_attribute_exists(self, engine):
        """Engine holds a kernel with a get_system lookup."""
        assert engine.kernel is not None
        assert callable(engine.kernel.get_system)

    @pytest.mark.parametrize(
        "accessor_name",
        [
            "event_bus",
            "time_system",
            "turn_queue",
            "combat_system",
            "survival_system",
            "skill_tree_manager",
            "job_manager",
            "guild_manager",
            "faction_war_manager",
            "procedural_quest_manager",
            "achievement_manager",
            "reincarnation_manager",
            "quest_scheduler",
        ],
    )
    def test_accessor_returns_kernel_registered_system(self, engine, accessor_name):
        """Each accessor resolves to the system registered under its kernel name."""
        system = getattr(engine, accessor_name)
        assert system is not None, f"{accessor_name} accessor returned None"
        assert system is engine.kernel.get_system(accessor_name)


class TestEngineLog:
    """Tests for Engine.log() routing to the kernel message_log system."""

    def test_log_with_message_only_uses_defaults(self, engine):
        """log(text) appends a default-colored INFO entry to msg_log."""
        before = len(engine.msg_log.history)
        engine.log("ログテスト: メッセージのみ")

        assert len(engine.msg_log.history) == before + 1
        entry = engine.msg_log.history[-1]
        assert entry.text == "ログテスト: メッセージのみ"
        assert entry.color == (230, 230, 230)
        assert entry.level == "INFO"

    def test_log_with_message_and_color(self, engine):
        """log(text, color) records the given color with default level."""
        engine.log("ログテスト: 色指定", (255, 0, 0))

        entry = engine.msg_log.history[-1]
        assert entry.text == "ログテスト: 色指定"
        assert entry.color == (255, 0, 0)
        assert entry.level == "INFO"

    def test_log_with_message_color_and_level(self, engine):
        """log(text, color, level) records all three fields."""
        engine.log("ログテスト: レベル指定", (0, 255, 0), level="SUCCESS")

        entry = engine.msg_log.history[-1]
        assert entry.text == "ログテスト: レベル指定"
        assert entry.color == (0, 255, 0)
        assert entry.level == "SUCCESS"


class TestEngineSkillEaterDelegation:
    """Tests for skill-eater methods delegating to SkillEaterSystemHandler."""

    @pytest.fixture
    def shell(self):
        """Shell engine with a MagicMock skill_eater_handler."""
        engine = _make_shell_engine()
        engine.skill_eater_handler = MagicMock(name="skill_eater_handler")
        return engine

    def test_execute_scan_delegates(self, shell):
        """execute_scan forwards to skill_eater_handler.execute_scan."""
        shell.skill_eater_handler.execute_scan.return_value = True

        assert shell.execute_scan() is True
        shell.skill_eater_handler.execute_scan.assert_called_once_with()

    def test_execute_devour_delegates(self, shell):
        """execute_devour forwards to skill_eater_handler.execute_devour."""
        shell.skill_eater_handler.execute_devour.return_value = False

        assert shell.execute_devour() is False
        shell.skill_eater_handler.execute_devour.assert_called_once_with()

    def test_execute_synthesis_delegates_with_skills(self, shell):
        """execute_synthesis forwards both skill ids to the handler."""
        shell.skill_eater_handler.execute_synthesis.return_value = True

        assert shell.execute_synthesis("fire_bolt", "ice_bolt") is True
        shell.skill_eater_handler.execute_synthesis.assert_called_once_with(
            "fire_bolt", "ice_bolt"
        )

    def test_execute_pet_dispatch_delegates_with_mission_parameters(self, shell):
        """execute_pet_dispatch forwards mission name, duration, and reward."""
        shell.skill_eater_handler.execute_pet_dispatch.return_value = True

        assert shell.execute_pet_dispatch("herb_fetch", 15, 700) is True
        shell.skill_eater_handler.execute_pet_dispatch.assert_called_once_with(
            "herb_fetch", 15, 700
        )

    def test_execute_base_upgrade_delegates_with_facility_and_cost(self, shell):
        """execute_base_upgrade forwards facility id and applies the default cost."""
        shell.skill_eater_handler.execute_base_upgrade.return_value = True

        assert shell.execute_base_upgrade("kitchen", 2500) is True
        shell.skill_eater_handler.execute_base_upgrade.assert_called_once_with(
            "kitchen", 2500
        )

        shell.execute_base_upgrade("well")
        shell.skill_eater_handler.execute_base_upgrade.assert_called_with("well", 1000)

    def test_execute_solve_puzzle_delegates_with_puzzle_and_skill(self, shell):
        """execute_solve_puzzle forwards puzzle type and skill tag."""
        shell.skill_eater_handler.execute_solve_puzzle.return_value = True

        assert shell.execute_solve_puzzle("lever", "teleport") is True
        shell.skill_eater_handler.execute_solve_puzzle.assert_called_once_with(
            "lever", "teleport"
        )


class TestEngineWithMockKernel:
    """Tests for Engine behavior on a shell instance with a mocked kernel."""

    @pytest.fixture
    def shell(self):
        return _make_shell_engine()

    def test_change_state_transitions_and_syncs_legacy_string(self, shell):
        """change_state updates current_state and the legacy game_state string."""
        shell.change_state(GameState.MENU)

        assert shell.game_state_data.current_state is GameState.MENU
        assert shell.game_state_data.game_state == GAME_STATE_TO_LEGACY[GameState.MENU]

    def test_change_state_same_state_is_noop(self, shell):
        """change_state to the current state leaves state untouched."""
        shell.game_state_data.game_state = "play"

        shell.change_state(GameState.PLAYING)

        assert shell.game_state_data.current_state is GameState.PLAYING
        assert shell.game_state_data.game_state == "play"

    def test_open_journal_toggles_ui_and_sets_state(self, shell):
        """open_journal toggles journal_ui and syncs game_state accordingly."""
        journal = MagicMock(name="journal_ui")
        journal.visible = True
        shell.kernel.register_system("journal_ui", journal)

        shell.open_journal()
        journal.toggle.assert_called_once_with()
        assert shell.game_state_data.game_state == "journal"

        journal.visible = False
        shell.open_journal()
        assert journal.toggle.call_count == 2
        assert shell.game_state_data.game_state == "play"

    def test_player_act_blocked_after_game_over(self, shell):
        """player_act refuses input once the run is no longer playing."""
        shell.game_state_machine = GameStateMachine("game_over")

        assert shell.player_act(1, 0) is False
        queried = [call.args[0] for call in shell.kernel.get_system.call_args_list]
        assert "gameplay_loop" not in queried

    def test_player_act_delegates_to_gameplay_loop_system(self, shell):
        """player_act invokes the kernel gameplay_loop system with the run context."""
        shell.game_state_machine = GameStateMachine("playing")
        loop_factory = MagicMock(name="gameplay_loop")
        loop_factory.return_value.player_act.return_value = True
        shell.kernel.register_system("gameplay_loop", loop_factory)

        assert shell.player_act(1, 0) is True
        loop_factory.assert_called_once_with(shell.kernel, shell)
        loop_factory.return_value.player_act.assert_called_once_with(1, 0)

    def test_advance_world_delegates_to_game_loop_handler(self, shell):
        """advance_world forwards to the GameLoopHandler."""
        shell.game_loop_handler = MagicMock(name="game_loop_handler")

        shell.advance_world()

        shell.game_loop_handler.advance_world.assert_called_once_with()

    def test_kernel_get_system_queried_with_expected_names(self, shell):
        """Kernel is queried by system name for journal UI and gameplay loop."""
        journal = MagicMock(name="journal_ui")
        journal.visible = False
        shell.kernel.register_system("journal_ui", journal)
        shell.game_state_machine = GameStateMachine("playing")
        shell.kernel.register_system("gameplay_loop", MagicMock())

        shell.open_journal()
        shell.player_act(1, 0)

        queried = [call.args[0] for call in shell.kernel.get_system.call_args_list]
        assert "journal_ui" in queried
        assert "gameplay_loop" in queried


class TestEngineQuestProgress:
    """Tests for Engine quest list handling and procedural quest progress."""

    def test_quests_append_and_remove_roundtrip(self, engine):
        """Quests appended to engine.quests are visible and removable."""
        initial = list(engine.quests)
        quest = SimpleNamespace(
            completed=False,
            target_monster="slime",
            target_count=5,
            current_count=0,
            reward_gold=50,
            reward_platinum=0,
        )
        try:
            engine.quests.append(quest)

            assert quest in engine.quests
            assert engine.quests[-1] is quest
        finally:
            engine.quests.remove(quest)

        assert list(engine.quests) == initial

    def test_progress_generated_quests_tolerates_unknown_event(self, engine):
        """_progress_generated_quests is silent for events with no active quest."""
        before = len(engine.msg_log.history)

        result = engine._progress_generated_quests("kill", "definitely_not_a_target", 1)

        assert result is None
        assert len(engine.msg_log.history) == before

    def test_progress_generated_quests_without_manager_is_silent(self):
        """_progress_generated_quests returns early when no manager is registered."""
        engine = _make_shell_engine()
        engine.game_state_data.player = None

        assert engine._progress_generated_quests("kill", "goblin") is None

    def test_progress_generated_quests_logs_manager_messages(self):
        """Manager progress messages are logged with SUCCESS level and gold color."""
        engine = _make_shell_engine()
        player = engine.player
        manager = MagicMock(name="procedural_quest_manager")
        manager.update_progress.return_value = ["進捗A", "進捗B"]
        engine.kernel.register_system("procedural_quest_manager", manager)

        engine._progress_generated_quests("kill", "goblin", 3)

        manager.update_progress.assert_called_once_with(player, "kill", "goblin", 3, engine)
        assert engine.log.call_count == 2
        first_call = engine.log.call_args_list[0]
        assert first_call.args == ("進捗A", (255, 215, 0))
        assert first_call.kwargs == {"level": "SUCCESS"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
