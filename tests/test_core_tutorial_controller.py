"""core/tutorial_controller モジュールのテスト。

TutorialController, GuideContext, TutorialGuideEvaluator の正常系・異常系・境界値をカバーする。
ui_fx_systems.TutorialManager はモックして外部依存を避ける。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core import tutorial_controller


# --- TutorialController ------------------------------------------------------

def test_tutorial_controller_init_loads_steps():
    """実データの tutorial_steps.json からステップを読み込む。"""
    controller = tutorial_controller.TutorialController("data/tutorial_steps.json")
    assert controller.total() == 7
    assert controller.index == 0


def test_tutorial_controller_current_and_text():
    """current() と current_text() で現在のステップを取得できる。"""
    controller = tutorial_controller.TutorialController("data/tutorial_steps.json")
    cur = controller.current()
    assert cur is not None
    assert cur["id"] == 1
    assert controller.current_text() == "WASD または HJKL で移動できます。"


def test_tutorial_controller_advance():
    """advance() で次のステップに進み、最後で停止する。"""
    controller = tutorial_controller.TutorialController("data/tutorial_steps.json")
    # 最初は index 0
    assert controller.index == 0
    assert not controller.is_last()

    # 1つ進める
    nxt = controller.advance()
    assert controller.index == 1
    assert nxt["id"] == 2

    # 最後まで進める
    for _ in range(5):
        controller.advance()
    assert controller.index == 6
    assert controller.is_last()

    # 最後の状態で advance しても index は変わらない
    controller.advance()
    assert controller.index == 6
    assert controller.is_last()


def test_tutorial_controller_back():
    """back() で前のステップに戻り、最初で停止する。"""
    controller = tutorial_controller.TutorialController("data/tutorial_steps.json")
    # 最後まで進む
    for _ in range(6):
        controller.advance()
    assert controller.index == 6

    # 1つ戻る
    prev = controller.back()
    assert controller.index == 5
    assert prev["id"] == 6

    # 最初まで戻る
    for _ in range(5):
        controller.back()
    assert controller.index == 0
    assert controller.current()["id"] == 1

    # 最初の状態で back しても index は変わらない
    controller.back()
    assert controller.index == 0


def test_tutorial_controller_empty_file():
    """存在しないファイルを指定した場合は空リストになる。"""
    controller = tutorial_controller.TutorialController("data/nonexistent_steps.json")
    assert controller.total() == 0
    assert controller.current() is None
    assert controller.current_text() == ""
    assert controller.is_last()  # 0 >= 0 - 1 なので True


def test_tutorial_controller_non_list_json():
    """JSON がリストでない場合は空リストになる。"""
    import json
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"not": "a list"}, f)
        tmp_path = f.name
    try:
        controller = tutorial_controller.TutorialController(tmp_path)
        assert controller.total() == 0
        assert controller.current() is None
    finally:
        os.unlink(tmp_path)


# --- GuideContext ------------------------------------------------------------

def test_guide_context_defaults():
    """GuideContext のデフォルト値を確認する。"""
    ctx = tutorial_controller.GuideContext()
    assert ctx.run_started is False
    assert ctx.turns == 0
    assert ctx.clock_ticks == 0
    assert ctx.active_npcs == ()
    assert ctx.hp == 0
    assert ctx.max_hp == 0
    assert ctx.hunger == tutorial_controller.HUNGER_HUNGRY_THRESHOLD
    assert ctx.dungeon_depth == 0
    assert ctx.max_dungeon_depth == 0
    assert ctx.current_world == ""
    assert ctx.toxicity == 0
    assert ctx.can_reincarnate is False
    assert ctx.fusion_material_count == 0
    assert ctx.has_scan_result is False
    assert ctx.devoured_skill_count == 0


def test_guide_context_from_engine_with_none_player():
    """player が None のエンジンならデフォルトの GuideContext を返す。"""
    engine = SimpleNamespace(player=None)
    ctx = tutorial_controller.GuideContext.from_engine(engine)
    assert ctx.run_started is False
    assert ctx.turns == 0


def test_guide_context_from_engine_full():
    """エンジンからすべての状態を採取できる。"""
    world_clock = SimpleNamespace(
        total_ticks=100,
        current_phase=SimpleNamespace(name="day"),
        npc_registry=SimpleNamespace(
            _schedules={
                "npc1": SimpleNamespace(npc_id="npc1", active_phases=[SimpleNamespace(name="day")]),
                "npc2": SimpleNamespace(npc_id="npc2", active_phases=[SimpleNamespace(name="night")]),
            }
        ),
    )
    time_system = SimpleNamespace(world_clock=world_clock)
    player = SimpleNamespace(
        hp=30,
        max_hp=100,
        max_dungeon_depth=5,
        skill_fusion_materials={"mat1": 1, "mat2": 2},
    )
    toxicity_mgr = SimpleNamespace(state=SimpleNamespace(current_toxicity=50))
    game_state_data = SimpleNamespace(
        world_a_data={"skills": ["skill_a", "skill_b"]},
        current_world="skill_eater",
    )
    survival = SimpleNamespace(hunger=800)
    engine = SimpleNamespace(
        player=player,
        game_state="play",
        turns=5,
        time_system=time_system,
        skill_eater_toxicity_manager=toxicity_mgr,
        game_state_data=game_state_data,
        survival=survival,
        dungeon_level=8,
        reincarnation_manager=None,
        last_scan_result=None,
    )
    ctx = tutorial_controller.GuideContext.from_engine(engine)
    assert ctx.run_started is True
    assert ctx.turns == 5
    assert ctx.clock_ticks == 100
    assert "npc1" in ctx.active_npcs
    assert "npc2" not in ctx.active_npcs  # night フェーズなので day にいない
    assert ctx.hp == 30
    assert ctx.max_hp == 100
    assert ctx.hunger == 800
    assert ctx.dungeon_depth == 8
    assert ctx.max_dungeon_depth == 5
    assert ctx.current_world == "skill_eater"
    assert ctx.toxicity == 50
    assert ctx.can_reincarnate is False
    assert ctx.fusion_material_count == 2
    assert ctx.has_scan_result is False
    assert ctx.devoured_skill_count == 2


def test_guide_context_from_engine_with_reincarnation_manager():
    """reincarnation_manager.can_reincarnate が True なら can_reincarnate も True になる。"""
    player = SimpleNamespace(hp=0, max_hp=0, max_dungeon_depth=0, skill_fusion_materials={})
    reincarnation_manager = MagicMock()
    reincarnation_manager.can_reincarnate.return_value = True
    engine = SimpleNamespace(
        player=player,
        game_state="",
        turns=0,
        time_system=None,
        skill_eater_toxicity_manager=None,
        game_state_data=SimpleNamespace(world_a_data={}, current_world=""),
        survival=None,
        dungeon_level=0,
        reincarnation_manager=reincarnation_manager,
        last_scan_result=None,
    )
    ctx = tutorial_controller.GuideContext.from_engine(engine)
    assert ctx.can_reincarnate is True


# --- CONDITION_EVALUATORS ----------------------------------------------------

def test_condition_evaluator_game_start():
    """game_start: run_started が True なら成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["game_start"](
        tutorial_controller.GuideContext(run_started=True)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["game_start"](
        tutorial_controller.GuideContext(run_started=False)
    ) is False


def test_condition_evaluator_first_action():
    """first_action: turns >= 1 で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["first_action"](
        tutorial_controller.GuideContext(turns=1)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["first_action"](
        tutorial_controller.GuideContext(turns=0)
    ) is False


def test_condition_evaluator_hp_below_50():
    """hp_below_50: max_hp > 0 かつ hp < max_hp * 0.5 で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["hp_below_50"](
        tutorial_controller.GuideContext(hp=30, max_hp=100)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["hp_below_50"](
        tutorial_controller.GuideContext(hp=60, max_hp=100)
    ) is False
    # max_hp == 0 の場合は False（ゼロ除算回避）
    assert tutorial_controller.CONDITION_EVALUATORS["hp_below_50"](
        tutorial_controller.GuideContext(hp=0, max_hp=0)
    ) is False


def test_condition_evaluator_hunger_hungry():
    """hunger_hungry: hunger < HUNGER_HUNGRY_THRESHOLD で成立。"""
    th = tutorial_controller.HUNGER_HUNGRY_THRESHOLD
    assert tutorial_controller.CONDITION_EVALUATORS["hunger_hungry"](
        tutorial_controller.GuideContext(hunger=th - 1)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["hunger_hungry"](
        tutorial_controller.GuideContext(hunger=th)
    ) is False
    assert tutorial_controller.CONDITION_EVALUATORS["hunger_hungry"](
        tutorial_controller.GuideContext(hunger=th + 100)
    ) is False


def test_condition_evaluator_reach_depth_10():
    """reach_depth_10: max(dungeon_depth, max_dungeon_depth) >= 10 で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["reach_depth_10"](
        tutorial_controller.GuideContext(dungeon_depth=10, max_dungeon_depth=0)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["reach_depth_10"](
        tutorial_controller.GuideContext(dungeon_depth=0, max_dungeon_depth=10)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["reach_depth_10"](
        tutorial_controller.GuideContext(dungeon_depth=9, max_dungeon_depth=9)
    ) is False


def test_condition_evaluator_reincarnate_ready():
    """reincarnate_ready: can_reincarnate で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["reincarnate_ready"](
        tutorial_controller.GuideContext(can_reincarnate=True)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["reincarnate_ready"](
        tutorial_controller.GuideContext(can_reincarnate=False)
    ) is False


def test_condition_evaluator_open_menu_fusion():
    """open_menu_fusion: fusion_material_count > 0 で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["open_menu_fusion"](
        tutorial_controller.GuideContext(fusion_material_count=1)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["open_menu_fusion"](
        tutorial_controller.GuideContext(fusion_material_count=0)
    ) is False


def test_condition_evaluator_switch_world_skill_eater():
    """switch_world_skill_eater: current_world == "skill_eater" で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["switch_world_skill_eater"](
        tutorial_controller.GuideContext(current_world="skill_eater")
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["switch_world_skill_eater"](
        tutorial_controller.GuideContext(current_world="main")
    ) is False


def test_condition_evaluator_first_scan():
    """first_scan: has_scan_result で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["first_scan"](
        tutorial_controller.GuideContext(has_scan_result=True)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["first_scan"](
        tutorial_controller.GuideContext(has_scan_result=False)
    ) is False


def test_condition_evaluator_first_devour_attempt():
    """first_devour_attempt: devoured_skill_count > 0 で成立。"""
    assert tutorial_controller.CONDITION_EVALUATORS["first_devour_attempt"](
        tutorial_controller.GuideContext(devoured_skill_count=1)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["first_devour_attempt"](
        tutorial_controller.GuideContext(devoured_skill_count=0)
    ) is False


def test_condition_evaluator_toxicity_above_40():
    """toxicity_above_40: toxicity >= TOXICITY_WARNING_THRESHOLD で成立。"""
    th = tutorial_controller.TOXICITY_WARNING_THRESHOLD
    assert tutorial_controller.CONDITION_EVALUATORS["toxicity_above_40"](
        tutorial_controller.GuideContext(toxicity=th)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["toxicity_above_40"](
        tutorial_controller.GuideContext(toxicity=th - 1)
    ) is False


def test_condition_evaluator_first_synthesis_open():
    """first_synthesis_open: devoured_skill_count >= SYNTHESIS_SKILL_MINIMUM で成立。"""
    min_n = tutorial_controller.SYNTHESIS_SKILL_MINIMUM
    assert tutorial_controller.CONDITION_EVALUATORS["first_synthesis_open"](
        tutorial_controller.GuideContext(devoured_skill_count=min_n)
    ) is True
    assert tutorial_controller.CONDITION_EVALUATORS["first_synthesis_open"](
        tutorial_controller.GuideContext(devoured_skill_count=min_n - 1)
    ) is False


# --- TutorialGuideEvaluator --------------------------------------------------

def test_tutorial_guide_evaluator_unevaluable_conditions():
    """evaluator の無い条件キーを返す。"""
    with patch(
        "ui_fx_systems.TutorialManager",
        return_value=SimpleNamespace(guides={}),
    ):
        evaluator = tutorial_controller.TutorialGuideEvaluator("data/tutorial_guides.yaml")
        # すべてのガイド条件に evaluator があるため空集合になるはず
        assert evaluator.unevaluable_conditions() == set()


def test_tutorial_guide_evaluator_evaluate_fires_guides():
    """未完了かつ条件を満たすガイドをすべて返す。"""
    guides = {
        "welcome_start": SimpleNamespace(
            id="welcome_start", trigger_condition="game_start", title="始まり", message="ようこそ", action_required="move"
        ),
        "first_hunger": SimpleNamespace(
            id="first_hunger", trigger_condition="hunger_hungry", title="空腹", message="お腹が空いた", action_required="eat_food"
        ),
    }
    with patch(
        "ui_fx_systems.TutorialManager",
        return_value=SimpleNamespace(guides=guides),
    ):
        evaluator = tutorial_controller.TutorialGuideEvaluator("data/tutorial_guides.yaml")
        context = tutorial_controller.GuideContext(run_started=True, hunger=500)
        fired = evaluator.evaluate(context, completed=set())
        fired_ids = {g.id for g in fired}
        assert "welcome_start" in fired_ids  # game_start かつ run_started=True
        assert "first_hunger" in fired_ids  # hunger_hungry かつ hunger=500 < 1000


def test_tutorial_guide_evaluator_evaluate_skips_completed():
    """completed に含まれるガイドは発動しない。"""
    guides = {
        "welcome_start": SimpleNamespace(
            id="welcome_start", trigger_condition="game_start", title="始まり", message="ようこそ", action_required="move"
        ),
    }
    with patch(
        "ui_fx_systems.TutorialManager",
        return_value=SimpleNamespace(guides=guides),
    ):
        evaluator = tutorial_controller.TutorialGuideEvaluator("data/tutorial_guides.yaml")
        context = tutorial_controller.GuideContext(run_started=True)
        fired = evaluator.evaluate(context, completed={"welcome_start"})
        assert fired == []


def test_tutorial_guide_evaluator_evaluate_condition_not_met():
    """条件を満たさないガイドは発動しない。"""
    guides = {
        "welcome_start": SimpleNamespace(
            id="welcome_start", trigger_condition="game_start", title="始まり", message="ようこそ", action_required="move"
        ),
    }
    with patch(
        "ui_fx_systems.TutorialManager",
        return_value=SimpleNamespace(guides=guides),
    ):
        evaluator = tutorial_controller.TutorialGuideEvaluator("data/tutorial_guides.yaml")
        context = tutorial_controller.GuideContext(run_started=False)
        fired = evaluator.evaluate(context, completed=set())
        assert fired == []


def test_tutorial_guide_evaluator_evaluate_no_evaluator():
    """evaluator の無い trigger_condition は無視される。"""
    guides = {
        "unknown_guide": SimpleNamespace(
            id="unknown_guide", trigger_condition="nonexistent_condition", title="不明", message="メッセージ", action_required="?"
        ),
    }
    with patch(
        "ui_fx_systems.TutorialManager",
        return_value=SimpleNamespace(guides=guides),
    ):
        evaluator = tutorial_controller.TutorialGuideEvaluator("data/tutorial_guides.yaml")
        context = tutorial_controller.GuideContext()
        fired = evaluator.evaluate(context, completed=set())
        assert fired == []
        assert "nonexistent_condition" in evaluator.unevaluable_conditions()
