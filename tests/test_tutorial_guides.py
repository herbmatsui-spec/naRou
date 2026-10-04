"""data/tutorial_guides.yaml の全ガイドが発動できることの検証。

設計方針:
  * 発動条件の一覧は YAML から導出する（ハードコード禁止）。
    新しい条件が YAML に追加され evaluator が無い場合、本テストが落ちる。
  * 状態は実物の Engine を書き換えて作る。チュートリアル側のモックは使わない。
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import game  # noqa: E402
from core.tutorial_controller import GuideContext, TutorialGuideEvaluator  # noqa: E402
from time_system import TimePhase  # noqa: E402

GUIDES_YAML = Path("data/tutorial_guides.yaml")


def load_declared_guides() -> dict[str, dict[str, Any]]:
    """YAML から guide_id -> 定義 を読み込む（テストが参照する唯一のデータ）"""
    with open(GUIDES_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    guides = data.get("tutorial_guides", {})
    assert guides, f"{GUIDES_YAML} に guide が定義されていない"
    return guides


def declared_conditions() -> set[str]:
    """YAML に宣言されている発動条件キーをすべて取り出す"""
    return {g["trigger_condition"] for g in load_declared_guides().values()}


def guide_ids_for(condition: str) -> set[str]:
    return {
        gid
        for gid, g in load_declared_guides().items()
        if g["trigger_condition"] == condition
    }


# ---------------------------------------------------------------------------
# 条件ごとに「その条件を満たす実物状態」を組み立てる
# 未知の条件は下の網羅テストで検出される。
# ---------------------------------------------------------------------------


def _arrange_game_start(eng: Any) -> None:
    eng.game_state = "play"


def _arrange_first_action(eng: Any) -> None:
    eng.turns = 1


def _arrange_first_time_check(eng: Any) -> None:
    eng.time_system.world_clock.advance_ticks(10)


def _arrange_first_npc_check(eng: Any) -> None:
    """夜間帯に切り替える。夜間のみ営業する NPC が立ち上がる"""
    clock = eng.time_system.world_clock
    clock.hour = 23
    clock._current_phase = TimePhase.NIGHT


def _arrange_hp_below_50(eng: Any) -> None:
    eng.player.hp = max(1, eng.player.max_hp // 2 - 1)


def _arrange_hunger_hungry(eng: Any) -> None:
    eng.survival.hunger = 900


def _arrange_reach_depth_10(eng: Any) -> None:
    eng.dungeon_level = 10


def _arrange_reincarnate_ready(eng: Any) -> None:
    eng.player.level = 50


def _arrange_open_menu_fusion(eng: Any) -> None:
    eng.player.skill_fusion_materials = {"fire_essence": 2}


def _arrange_switch_world_skill_eater(eng: Any) -> None:
    eng.game_state_data.current_world = "skill_eater"


def _arrange_first_scan(eng: Any) -> None:
    eng.last_scan_result = object()


def _arrange_first_devour_attempt(eng: Any) -> None:
    eng.game_state_data.world_a_data.setdefault("skills", []).append("fire_ball")


def _arrange_toxicity_above_40(eng: Any) -> None:
    eng.skill_eater_toxicity_manager.add_toxicity(40)


def _arrange_first_synthesis_open(eng: Any) -> None:
    eng.game_state_data.world_a_data.setdefault("skills", []).extend(["alpha", "beta"])


ARRANGERS: dict[str, Callable[[Any], None]] = {
    "game_start": _arrange_game_start,
    "first_action": _arrange_first_action,
    "first_time_check": _arrange_first_time_check,
    "first_npc_check": _arrange_first_npc_check,
    "hp_below_50": _arrange_hp_below_50,
    "hunger_hungry": _arrange_hunger_hungry,
    "reach_depth_10": _arrange_reach_depth_10,
    "reincarnate_ready": _arrange_reincarnate_ready,
    "open_menu_fusion": _arrange_open_menu_fusion,
    "switch_world_skill_eater": _arrange_switch_world_skill_eater,
    "first_scan": _arrange_first_scan,
    "first_devour_attempt": _arrange_first_devour_attempt,
    "toxicity_above_40": _arrange_toxicity_above_40,
    "first_synthesis_open": _arrange_first_synthesis_open,
}


@pytest.fixture
def engine() -> Any:
    return game.Engine()


def fired_ids(eng: Any, completed: set[str] | None = None) -> set[str]:
    evaluator = TutorialGuideEvaluator()
    ctx = GuideContext.from_engine(eng)
    return {g.id for g in evaluator.evaluate(ctx, completed or set())}


# ---------------------------------------------------------------------------
# 1. YAML に宣言されたすべての条件に evaluator が存在するか
# ---------------------------------------------------------------------------


def test_every_declared_condition_has_an_evaluator():
    missing = sorted(declared_conditions() - set(TutorialGuideEvaluator.CONDITION_EVALUATORS))
    assert not missing, f"evaluator 未実装の発動条件: {missing}"


def test_evaluator_set_matches_declared_conditions_exactly():
    """YAML に存在しない evaluator は死にコードなので残さない"""
    extra = sorted(set(TutorialGuideEvaluator.CONDITION_EVALUATORS) - declared_conditions())
    assert not extra, f"YAML に存在しない evaluator: {extra}"


def test_arrangers_cover_every_declared_condition():
    """条件が追加されても反映テストを忘れた場合に落とす"""
    missing = sorted(declared_conditions() - set(ARRANGERS))
    assert not missing, f"テスト側の状態組み立てが無い条件: {missing}"


# ---------------------------------------------------------------------------
# 2. 宣言されたガイドがすべて実際に発火するか
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("condition", sorted(declared_conditions()))
def test_declared_guide_fires_for_its_condition(condition, engine):
    ARRANGERS[condition](engine)
    fired = fired_ids(engine)
    assert fired, f"条件 {condition} でガイドが1つも発火しなかった"
    missing = sorted(guide_ids_for(condition) - fired)
    assert not missing, f"条件 {condition} のガイド {missing} が発火しなかった"


def test_every_authored_guide_is_reachable(engine):
    """著作者が書いたガイドがすべて evaluable であることの総当たり"""
    unreached = []
    for guide_id, guide in load_declared_guides().items():
        ARRANGERS[guide["trigger_condition"]](engine)
        if guide_id not in fired_ids(engine):
            unreached.append(guide_id)
    assert not unreached, f"発動しないガイド: {unreached}"


# ---------------------------------------------------------------------------
# 3. 死んでいた主要ケースの個別検証
# ---------------------------------------------------------------------------


def test_hp_below_50_fires_when_hp_drops_below_half(engine):
    """HPが半分を下回った瞬間に first_low_hp が発火する"""
    engine.player.hp = engine.player.max_hp
    assert "first_low_hp" not in fired_ids(engine)

    engine.player.hp = engine.player.max_hp // 2 - 1
    assert "first_low_hp" in fired_ids(engine)


def test_hunger_hungry_fires_when_hunger_is_low(engine):
    engine.survival.hunger = 8000
    assert "first_hunger" not in fired_ids(engine)

    engine.survival.hunger = 900
    assert "first_hunger" in fired_ids(engine)


def test_completed_guide_does_not_fire_again(engine):
    engine.player.hp = 1
    assert "first_low_hp" in fired_ids(engine, engine.player.completed_tutorials)

    engine.player.completed_tutorials.add("first_low_hp")
    assert "first_low_hp" not in fired_ids(engine, engine.player.completed_tutorials)


def test_guide_payload_is_displayable(engine):
    """発火したガイドは既存のUI/ログ規約どおりの dict になる"""
    evaluator = TutorialGuideEvaluator()
    engine.player.hp = 1
    fired = evaluator.evaluate(GuideContext.from_engine(engine), set())
    payload = next(g.to_dict() for g in fired if g.id == "first_low_hp")
    assert set(payload) == {
        "id",
        "trigger_condition",
        "title",
        "message",
        "action_required",
    }
    assert payload["title"] and payload["message"]


def test_evaluator_loads_all_authored_guides():
    evaluator = TutorialGuideEvaluator()
    assert set(load_declared_guides()) == set(evaluator.guides)
