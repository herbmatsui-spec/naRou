"""engine.systems.game_loop モジュールのテスト (GameLoopHandler).

GameLoopHandler はワールド進行、ターン処理、ラン終了・履歴記録を担当する。
Engine スタブは SimpleNamespace で構築し、MagicMock の予測不能な動作を避ける。
モックが必要なメソッド・属性は unittest.mock.patch で差し替える。
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from engine.systems.game_loop import GameLoopHandler
from run_summary import CAUSE_COMBAT, CAUSE_HUNGER, CAUSE_UNKNOWN, RunSummary
from constants import COLOR_GOLD_YELLOW
from run_summary import GAME_OVER_TITLE

# ゲームループ内部でローカル import する外部モジュールをスタブ化
for _mod_name in (
    "managers.persistence_manager",
    "managers.world_news_manager",
    "managers.faction_manager",
    "managers.pet_bond_manager",
    "pet_personality_system",
):
    sys.modules.setdefault(_mod_name, MagicMock())

_pm_stub = sys.modules["managers.persistence_manager"]


# ---------------------------------------------------------------------------
# ファイア: テスト用スタブエンジンの構築 (SimpleNamespace)
# ---------------------------------------------------------------------------


def _make_engine(**overrides):
    """GameLoopHandler のメソッドが参照する属性を持つスタブエンジンを返す."""
    clock = SimpleNamespace()
    clock.total_ticks = 1000
    clock.config = SimpleNamespace()
    clock.config.ticks_per_minute = 60

    world_clock = SimpleNamespace()
    world_clock.total_ticks = 1000
    world_clock.config = SimpleNamespace()
    world_clock.config.ticks_per_minute = 60

    time_system = SimpleNamespace()
    time_system.world_clock = world_clock

    game_state_machine = MagicMock()
    game_state_machine.current = "playing"

    player = SimpleNamespace()
    player.hp = 10
    player.max_hp = 20
    player.kill_counts = {}
    player.status_effects = []

    game_state_data = SimpleNamespace()
    game_state_data.current_state = "playing"
    game_state_data.game_state = "playing"
    game_state_data.world_a_data = {"skills": ()}

    survival = SimpleNamespace()
    survival.hunger = 50

    engine = SimpleNamespace()
    engine.game_state_machine = game_state_machine
    engine.player = player
    engine.dungeon_level = 1
    engine.turns = 5
    engine.kill_counts = {}
    engine.game_state_data = game_state_data
    engine.time_system = time_system
    engine.survival = survival
    engine.log = MagicMock()
    engine.kernel = None
    engine.gameplay_loop = MagicMock()
    engine.gameplay_loop.return_value = MagicMock()
    engine.check_win_condition = MagicMock(return_value=False)
    engine.floating_texts = []
    engine.particles = []
    engine.game_map = MagicMock()
    # オプショナル属性は持たせない (hasattr ガード対象)
    for k, v in overrides.items():
        setattr(engine, k, v)
    return engine


def _make_handler(engine=None):
    if engine is None:
        engine = _make_engine()
    return GameLoopHandler(engine), engine


# ---------------------------------------------------------------------------
# _end_run_if_player_dead
# ---------------------------------------------------------------------------


def test_end_run_if_player_dead_game_over_returns_true():
    """game_over 状態なら何もせず True を返す (冪等)."""
    handler, engine = _make_handler()
    engine.game_state_machine.current = "game_over"
    with patch.object(handler, "_on_player_death") as m_death:
        assert handler._end_run_if_player_dead() is True
    m_death.assert_not_called()


def test_end_run_if_player_dead_hp_positive_returns_false():
    """HP > 0 なら False を返し、死亡処理を行わない."""
    handler, engine = _make_handler()
    engine.player.hp = 5
    with patch.object(handler, "_on_player_death") as m_death:
        assert handler._end_run_if_player_dead() is False
    m_death.assert_not_called()


def test_end_run_if_player_dead_hp_zero_triggers_death_flow():
    """HP <= 0 なら死亡ハンドラを呼び、run_summary を構築・提示・記録して True を返す."""
    handler, engine = _make_handler()
    engine.player.hp = 0
    with patch.object(handler, "_on_player_death") as m_death, \
         patch.object(handler, "_build_run_summary", return_value=RunSummary(1, 0, 0, 1, "戦闘", 0, ())) as m_build, \
         patch.object(handler, "_present_run_summary") as m_present, \
         patch.object(handler, "_record_run_history") as m_record:
        result = handler._end_run_if_player_dead()
    assert result is True
    m_death.assert_called_once()
    m_build.assert_called_once()
    assert engine.run_summary is not None
    m_present.assert_called_once_with(engine.run_summary)
    m_record.assert_called_once_with(engine.run_summary)


# ---------------------------------------------------------------------------
# _record_harm_cause / _observed_harm_cause
# ---------------------------------------------------------------------------


def test_record_and_observed_harm_cause_same_hp():
    """記録した時点の HP と現在の HP が一致すれば記録された原因を返す."""
    handler, engine = _make_handler()
    engine.player.hp = 10
    handler._record_harm_cause(CAUSE_COMBAT)
    assert handler._observed_harm_cause() == CAUSE_COMBAT


def test_observed_harm_cause_hp_changed_returns_unknown():
    """記録後に HP が変わっていれば原因不明 (CAUSE_UNKNOWN) を返す."""
    handler, engine = _make_handler()
    engine.player.hp = 10
    handler._record_harm_cause(CAUSE_COMBAT)
    engine.player.hp = 5  # 記録後にダメージを受けた
    assert handler._observed_harm_cause() == CAUSE_UNKNOWN


def test_observed_harm_cause_no_record_returns_unknown():
    """記録がなければ __init__ を通さない旧セーブ想定で CAUSE_UNKNOWN を返す."""
    handler, engine = _make_handler()
    engine.player.hp = 10
    assert handler._observed_harm_cause() == CAUSE_UNKNOWN


# ---------------------------------------------------------------------------
# _build_run_summary
# ---------------------------------------------------------------------------


def test_build_run_summary():
    """RunSummary はエンジン状態からスナップショットを組み立てる."""
    handler, engine = _make_handler()
    engine.dungeon_level = 3
    engine.turns = 120
    engine.player.kill_counts = {"slime": 2, "goblin": 1}
    engine.game_state_data.world_a_data = {"skills": ("fire", "ice")}
    summary = handler._build_run_summary()
    assert isinstance(summary, RunSummary)
    assert summary.depth == 3
    assert summary.kills == 3
    assert summary.devoured_skills == 2
    assert summary.turns == 120
    assert summary.elapsed_minutes == 1000 // 60
    assert summary.devoured_skill_ids == ("fire", "ice")


# ---------------------------------------------------------------------------
# _present_run_summary
# ---------------------------------------------------------------------------


def test_present_run_summary_logs_title_and_lines():
    """run summary をログへ提示する (GAME_OVER タイトル + 各行)."""
    handler, engine = _make_handler()
    summary = RunSummary(1, 0, 0, 1, "戦闘", 0, ())
    handler._present_run_summary(summary)
    engine.log.assert_any_call(GAME_OVER_TITLE, (255, 50, 50), level="WARNING")
    for line in summary.format_lines():
        engine.log.assert_any_call(line, COLOR_GOLD_YELLOW, level="WARNING")


# ---------------------------------------------------------------------------
# _record_run_history
# ---------------------------------------------------------------------------


def test_record_run_history_success():
    """RunHistoryStore へ記録し、例外時はログだけ残して飲み込む."""
    handler, engine = _make_handler()
    summary = RunSummary(1, 0, 0, 1, "戦闘", 0, ())
    with patch("engine.systems.game_loop.RunHistoryStore") as m_store:
        m_store.return_value.record.return_value = None
        handler._record_run_history(summary)
        m_store.return_value.record.assert_called_once_with(summary)
    engine.log.assert_not_called()


def test_record_run_history_exception_swallowed():
    """記録に失敗してもラン終了を失敗させず、警告ログを出す."""
    handler, engine = _make_handler()
    summary = RunSummary(1, 0, 0, 1, "戦闘", 0, ())
    with patch("engine.systems.game_loop.RunHistoryStore") as m_store:
        m_store.return_value.record.side_effect = RuntimeError("disk error")
        handler._record_run_history(summary)
    engine.log.assert_called_once()


# ---------------------------------------------------------------------------
# _present_run_history
# ---------------------------------------------------------------------------


def test_present_run_history_logs_startup_lines():
    """起動時の履歴行をログへ提示する."""
    handler, engine = _make_handler()
    with patch("engine.systems.game_loop.RunHistoryStore") as m_store:
        m_store.return_value.startup_lines.return_value = ["前回: 深度 5", "前回: 戦闘"]
        handler._present_run_history()
    engine.log.assert_any_call("前回: 深度 5", (255, 215, 0), level="INFO")
    engine.log.assert_any_call("前回: 戦闘", (255, 215, 0), level="INFO")


# ---------------------------------------------------------------------------
# _on_player_death
# ---------------------------------------------------------------------------


def test_on_player_death_transitions_game_over():
    """プレイヤー死亡時に GameStateMachine を game_over へ遷移し、各種状態を更新する."""
    handler, engine = _make_handler()
    _pm_stub.PersistenceManager.return_value.save.return_value = None
    handler._on_player_death()
    engine.game_state_machine.transition.assert_called_once_with("game_over")
    from constants import GameState
    assert engine.game_state_data.current_state == GameState.GAME_OVER
    assert engine.game_state_data.game_state == "game_over"
    engine.log.assert_called_once()
    _pm_stub.PersistenceManager.return_value.save.assert_called_once_with(engine)


def test_on_player_death_persistence_failure_swallowed():
    """PersistenceManager が失敗しても死亡処理は継続する."""
    handler, engine = _make_handler()
    _pm_stub.PersistenceManager.return_value.save.side_effect = RuntimeError("save failed")
    handler._on_player_death()  # 例外を投げない
    engine.game_state_machine.transition.assert_called_once_with("game_over")


# ---------------------------------------------------------------------------
# advance_world
# ---------------------------------------------------------------------------


def test_advance_world_dead_player_returns_early():
    """プレイヤー死亡時は turn を進めず即座に返す."""
    handler, engine = _make_handler()
    engine.player.hp = 0
    with patch.object(handler, "_end_run_if_player_dead", return_value=True):
        handler.advance_world()
    assert engine.turns == 5  # 進まない


def test_advance_world_normal_flow_records_harm_and_continues():
    """通常ターン進行: turn カウンタを進め、HP 減少時は死因を記録する."""
    handler, engine = _make_handler()
    engine.player.hp = 10
    engine.survival.hunger = 0  # 飢え状態
    engine.player.x = 3
    engine.player.y = 4
    # gameplay_loop スタブ（hp を減らして死因記録をトリガー）
    mock_gl = MagicMock()
    mock_gl.advance_world.side_effect = lambda: setattr(engine.player, "hp", engine.player.hp - 1)
    engine.gameplay_loop.return_value = mock_gl
    # 外部モジュールをスタブ化
    _pm_stub.PersistenceManager.return_value.autosave_if_due.return_value = None
    sys.modules["managers.world_news_manager"].WorldNewsManager.return_value.advance.return_value = None
    sys.modules["managers.faction_manager"].FactionManager.return_value.update_influence.return_value = None
    sys.modules["managers.pet_bond_manager"].PetBondManager.return_value.update_turn_bond.return_value = None
    sys.modules["pet_personality_system"].PetPersonalitySystem.apply_bond_gameplay_effects.return_value = None
    with patch("engine.systems.game_loop.SoundManager") as m_sound, \
         patch.object(handler, "_record_harm_cause") as m_record_harm, \
         patch.object(handler, "_tick_skill_eater_template_events") as m_tick:
        m_sound.bgm_manager.check_crisis_trigger.return_value = None
        m_tick.return_value = None
        handler.advance_world()
    assert engine.turns == 6
    m_record_harm.assert_called_once()
    engine.game_map.compute_fov.assert_called_once_with(
        engine.player.x, engine.player.y, radius=8
    )


def test_advance_world_win_condition_returns_early():
    """勝利条件達成後はそれ以降の処理を行わず返す."""
    handler, engine = _make_handler()
    engine.player.hp = 10
    mock_gl = MagicMock()
    mock_gl.advance_world.return_value = None
    engine.gameplay_loop.return_value = mock_gl
    engine.check_win_condition.return_value = True
    with patch("engine.systems.game_loop.SoundManager"), \
         patch.object(handler, "_tick_skill_eater_template_events"):
        handler.advance_world()
    # game_map.compute_fov より前で返るので compute_fov は呼ばれない
    engine.game_map.compute_fov.assert_not_called()


# ---------------------------------------------------------------------------
# _tick_skill_eater_template_events
# ---------------------------------------------------------------------------


def test_tick_skill_eater_template_events_non_skill_eater_world_returns_early():
    """skill_eater ワールド以外では何もしない."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "main"
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []


def test_tick_skill_eater_template_events_no_kernel_returns_early():
    """kernel がないスキルイーター ワールドでは早期リターン."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "skill_eater"
    engine.kernel = None
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []


def test_tick_skill_eater_template_events_no_system_returns_early():
    """skill_eater_meta_intervention システムがなければ早期リターン."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "skill_eater"
    engine.kernel = MagicMock()
    engine.kernel.has_system.return_value = False
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []


def test_tick_skill_eater_template_events_lifetime_expiry():
    """期限切れイベントは完遂扱いでリストから除外される."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "skill_eater"
    engine.kernel = MagicMock()
    engine.kernel.has_system.return_value = True
    gen = MagicMock()
    engine.kernel.get_system.return_value = gen
    # 期限切れイベント (turn - turn_spawned >= lifetime)
    old_event = SimpleNamespace(turn_spawned=1, archetype="古代の儀式")
    handler._loop_template_events = [old_event]
    engine.turns = 99  # 99 - 1 >= 40 で期限切れ、かつ 99 % 20 != 0 で spawn 判定をスキップ
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []
    engine.log.assert_called_once()


def test_tick_skill_eater_template_events_not_cadence_turn_skips_spawn():
    """cadence ターン以外では新規発生判定を行わない."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "skill_eater"
    engine.kernel = MagicMock()
    engine.kernel.has_system.return_value = True
    gen = MagicMock()
    engine.kernel.get_system.return_value = gen
    engine.turns = 21  # 20 の倍数ではない
    handler._tick_skill_eater_template_events()
    gen.maybe_spawn.assert_not_called()


def test_tick_skill_eater_template_events_spawn_and_present():
    """発生判定を通過したイベントはリストに追加され、発表システムに通知される."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "skill_eater"
    engine.kernel = MagicMock()
    engine.kernel.has_system.return_value = True
    gen = MagicMock()
    new_event = SimpleNamespace(turn_spawned=20, archetype="原典のささやき")
    gen.maybe_spawn.return_value = new_event
    engine.kernel.get_system.return_value = gen
    engine.turns = 20
    with patch.object(handler, "_template_event_context", return_value=("slum", 1)):
        handler._tick_skill_eater_template_events()
    assert new_event in handler._loop_template_events
    engine.log.assert_called()


def test_tick_skill_eater_template_events_spawn_no_presentation_system():
    """発表システムがなくてもイベント登録は行われる."""
    handler, engine = _make_handler()
    engine.game_state_data.current_world = "skill_eater"
    engine.kernel = MagicMock()
    engine.kernel.has_system.side_effect = lambda name: name == "skill_eater_meta_intervention"
    gen = MagicMock()
    new_event = SimpleNamespace(turn_spawned=20, archetype="原典のささやき")
    gen.maybe_spawn.return_value = new_event
    engine.kernel.get_system.return_value = gen
    engine.turns = 20
    with patch.object(handler, "_template_event_context", return_value=("slum", 1)):
        handler._tick_skill_eater_template_events()
    assert new_event in handler._loop_template_events


# ---------------------------------------------------------------------------
# _template_event_context
# ---------------------------------------------------------------------------


def test_template_event_context_defaults_to_slum():
    """カーネルや探索システムがなければデフォルト (slum, 1) を返す."""
    handler, engine = _make_handler()
    engine.kernel = None
    ctx, lc = handler._template_event_context()
    assert ctx == "slum"
    assert lc == 1


def test_template_event_context_with_exploration_system():
    """探索システムから部屋 ID とランクを導く."""
    handler, engine = _make_handler()
    engine.kernel = MagicMock()
    engine.kernel.has_system.return_value = True
    explore = MagicMock()
    explore.current_room_id = "midas_tower_entrance"
    explore.exploration_rank = MagicMock()
    explore.exploration_rank.rank = 9
    engine.kernel.get_system.return_value = explore
    ctx, lc = handler._template_event_context()
    assert ctx == "noble_quarter"
    assert lc == 3  # 9 // 3 = 3


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_calls_turn_queue_and_systems():
    """update はターンキューとシステムコーディネータを呼び出す."""
    handler, engine = _make_handler()
    engine.turn_queue = MagicMock()
    engine.systems_coordinator = MagicMock()
    engine.fx_manager = MagicMock()
    engine.tutorial_manager = MagicMock()
    engine.notification_manager = MagicMock()
    engine.game_map = MagicMock()
    handler.update(delta_time=0.5)
    engine.turn_queue.process.assert_called_once_with(engine, 0.5)
    engine.systems_coordinator.update_all.assert_called_once_with(engine, 0.5)


def test_update_skips_missing_attrs():
    """存在しないオプショナル属性は hasattr でガードされエラーにならない."""
    handler, engine = _make_handler()
    # turn_queue なしなど
    handler.update(delta_time=1.0)  # 例外を投げない
