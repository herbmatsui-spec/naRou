"""
偏執的クエストシステム テスト (設計書 Phase 1 Steps 1-4)
条件分岐ツリー (CQCT): AST / パーサ / 評価 / QuestObjective 統合を検証する。
"""

from __future__ import annotations

import os
import tempfile

import pytest

from quest_condition_ast import (
    AndCondition,
    LeafCondition,
    NotCondition,
    OrCondition,
    XorCondition,
    is_condition_node,
)
from quest_condition_parser import parse_condition, ConditionParseError
from quest_condition_evaluator import (
    evaluate,
    DictContext,
    EvaluationContext,
)

from main_quest_system import MainQuestSystem, QuestObjective, QuestStatus


# ---------------------------------------------------------------------------
# Step 1 / Step 3: AST + 評価
# ---------------------------------------------------------------------------

def test_leaf_comparison():
    ctx = DictContext({"player": {"level": 10}})
    node = LeafCondition("player.level", ">=", 5)
    assert node.evaluate(ctx) is True
    assert LeafCondition("player.level", "<", 5).evaluate(ctx) is False


def test_leaf_membership():
    ctx = DictContext({"flags": {"slew_guardian": True}, "inventory": ["sword"]})
    # 値なし has -> キーの真偽
    assert LeafCondition("flags.slew_guardian", "has", None).evaluate(ctx) is True
    # 値あり has -> メンバーシップ
    assert LeafCondition("inventory", "has", "sword").evaluate(ctx) is True
    assert LeafCondition("flags.missing", "exists", None).evaluate(ctx) is False
    assert LeafCondition("player.weapon", "in", ["sword", "axe"]).evaluate(
        DictContext({"player": {"weapon": "sword"}})
    ) is True


def test_and_or_not_xor():
    ctx = DictContext({"player": {"level": 10}, "flags": {"a": True, "b": False}})
    assert AndCondition([
        LeafCondition("player.level", ">=", 5),
        LeafCondition("flags.a", "truthy", None),
    ]).evaluate(ctx) is True
    assert OrCondition([
        LeafCondition("flags.b", "truthy", None),
        LeafCondition("player.level", ">=", 5),
    ]).evaluate(ctx) is True
    assert NotCondition(LeafCondition("flags.b", "truthy", None)).evaluate(ctx) is True
    assert XorCondition([
        LeafCondition("flags.a", "truthy", None),
        LeafCondition("flags.b", "truthy", None),
    ]).evaluate(ctx) is True
    # 両方真なら xor は偽
    assert XorCondition([
        LeafCondition("flags.a", "truthy", None),
        LeafCondition("player.level", ">=", 1),
    ]).evaluate(ctx) is False


# ---------------------------------------------------------------------------
# Step 2: パーサ
# ---------------------------------------------------------------------------

def test_parse_leaf():
    node = parse_condition("(>= player.level 10)")
    assert isinstance(node, LeafCondition)
    assert node.key == "player.level"
    assert node.op == ">="
    assert node.value == 10


def test_parse_string_value():
    node = parse_condition('(has flags.met "elder")')
    assert isinstance(node, LeafCondition)
    assert node.value == "elder"


def test_parse_nested_combinators():
    dsl = "(and (>= player.level 5) (or (has flags.a) (not (has flags.b))))"
    node = parse_condition(dsl)
    assert isinstance(node, AndCondition)
    assert len(node.children) == 2
    assert isinstance(node.children[1], OrCondition)
    assert isinstance(node.children[1].children[1], NotCondition)


def test_parse_xor_requires_two():
    with pytest.raises(ConditionParseError):
        parse_condition("(xor (has flags.a))")


def test_parse_errors():
    with pytest.raises(ConditionParseError):
        parse_condition("(>= player.level)")  # 値欠落
    with pytest.raises(ConditionParseError):
        parse_condition("(unknown_op player.level 1)")
    with pytest.raises(ConditionParseError):
        parse_condition("(>= player.level 5")  # 閉じ括弧欠落


def test_roundtrip_evaluate_via_parser():
    ctx = DictContext({"player": {"level": 3}, "flags": {"a": True, "b": False}})
    dsl = "(or (>= player.level 5) (has flags.a))"
    assert evaluate(parse_condition(dsl), ctx) is True
    assert evaluate(parse_condition("(not (has flags.a))"), ctx) is False


# ---------------------------------------------------------------------------
# Step 4: QuestObjective 統合 + YAML スキーマ拡張
# ---------------------------------------------------------------------------

def test_questobjective_condition_satisfied():
    obj = QuestObjective(
        objective_id="prove",
        description="試練",
        target_type="variable",
        target_id="prove",
        condition_dsl="(or (>= player.level 5) (has flags.slew_guardian))",
    )
    # 直接構築時は condition_dsl -> condition_tree を自前で構築（ロード時は _build_condition が行う）
    obj.condition_tree = parse_condition(obj.condition_dsl)
    assert is_condition_node(obj.condition_tree)
    assert obj.evaluate(DictContext({"player": {"level": 2}, "flags": {"slew_guardian": True}})) is True
    assert obj.evaluate(DictContext({"player": {"level": 2}, "flags": {}})) is False
    # 条件なしの場合は従来のカウントベースにフォールバック
    plain = QuestObjective("x", "y", "kill", "z")
    assert plain.condition_tree is None


def test_yaml_loads_condition_dsl():
    yaml_text = """
main_quests:
  - quest_id: "q1"
    title: "テストクエスト"
    description: "CQCT 統合確認"
    required_phase: "BEGINNING"
    objectives:
      - objective_id: "prove_resolve"
        description: "試練: Lv5以上 または 守護者討伐済み"
        target_type: "variable"
        target_id: "prove_resolve"
        required_count: 1
        condition_dsl: "(or (>= player.level 5) (has flags.slew_guardian))"
    rewards:
      gold: 10
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_text)
        path = f.name
    try:
        system = MainQuestSystem(data_path=path)
        quest = system.quests["q1"]
        obj = quest.objectives[0]
        assert obj.condition_tree is not None
        assert obj.evaluate(DictContext({"player": {"level": 1}, "flags": {"slew_guardian": True}})) is True
        assert obj.evaluate(DictContext({"player": {"level": 1}, "flags": {}})) is False
    finally:
        os.unlink(path)


def test_main_quests_yaml_has_sample_condition():
    # 実データにも condition_dsl サンプルが含まれていることを確認
    system = MainQuestSystem()
    found = False
    for quest in system.quests.values():
        for obj in quest.objectives:
            if obj.condition_dsl:
                found = True
                assert obj.condition_tree is not None
    assert found, "data/main_quests.yaml に condition_dsl サンプルが必要です"


def test_evaluation_context_protocol():
    class CustomCtx:
        def resolve(self, key: str):

            return {"x": 1}.get(key)
    assert evaluate(LeafCondition("x", "==", 1), CustomCtx()) is True
