#!/usr/bin/env python3
"""Simple test for the quest condition system"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quest_condition_ast import *
from quest_condition_evaluator import evaluate_condition
from quest_condition_parser import parse_condition


# モックプレイヤー
class MockPlayer:
    level = 10
    gold = 5000
    job = "mage"
    kill_counts = {"goblin": 7, "slime": 3}
    collect_counts = {"herb": 5}
    visited_locations = {"shrine", "village"}
    story_variables = {"boss_defeated": False, "gold": 5000}
    skills = {"fire_mastery": {"level": 3}}
    character_relationships = {"npc_001": {"trust": 60}}
    faction_reputation = {"adventurer_guild": 150}
    pets = []


class MockPet:
    species = "fenrir"
    contract_tier = 2
    fusion_history = ["ice"]
    evolution_stage = 1


class MockEngine:
    class TimeSystem:
        def get_current_time(self):
            class T:
                hour = 10
                minute = 30

            return T()

    class WeatherSystem:
        def get_current_weather(self):
            return "clear"

    class CalendarSystem:
        def get_current_season(self):
            return "spring"

        def get_moon_phase(self):
            return 3

    time_system = TimeSystem()
    weather_system = WeatherSystem()
    calendar_system = CalendarSystem()


class MockWorldState:
    def get_phase(self):
        class Phase:
            name = "EXPLORATION"

        return Phase()

    def get_variable(self, player, var_name, default=None):
        return player.story_variables.get(var_name, default)


def test_condition_system():
    print("=== Testing Quest Condition System ===\n")

    # モックオブジェクト作成
    player = MockPlayer()
    player.pets = [MockPet()]
    engine = MockEngine()
    world_state = MockWorldState()

    # テストケース（S式記法を使用）
    test_cases = [
        ("(>= player.kill_counts.goblin 5)", True),
        ("(>= player.kill_counts.goblin 10)", False),
        (
            "(and (>= player.kill_counts.goblin 5) (>= player.collect_counts.herb 3))",
            True,
        ),
        ('(and (>= player.level 10) (== player.job "mage"))', True),
        ("(== player.story_variables.boss_defeated false)", True),
        ("(>= player.skills.fire_mastery.level 3)", True),
        ("(>= player.faction_reputation.adventurer_guild 100)", True),
        ("(>= player.character_relationships.npc_001.trust 50)", True),
        ("(has player.pets)", True),  # ペットを持っているか
        ('(has player.visited_locations "shrine")', True),  # 指定場所を訪問済みか
        (
            "(and (>= player.kill_counts.goblin 5) (>= player.kill_counts.slime 3))",
            True,
        ),
        (
            "(or (>= player.kill_counts.goblin 10) (>= player.collect_counts.herb 10))",
            False,
        ),  # 両方ともfalse
        (
            "(or (>= player.kill_counts.goblin 5) (>= player.collect_counts.herb 10))",
            True,
        ),  # 片方のみtrue
    ]

    passed = 0
    total = len(test_cases)

    for condition_str, expected in test_cases:
        try:
            # パース
            ast = parse_condition(condition_str)
            # 評価
            result = evaluate_condition(ast, player, engine, world_state)
            # 結果チェック
            if result == expected:
                print(f"✓ {condition_str:<55} => {result}")
                passed += 1
            else:
                print(f"✗ {condition_str:<55} => {result} (expected {expected})")
        except Exception as e:
            import traceback

            print(f"✗ {condition_str:<55} => ERROR: {e}")
            traceback.print_exc()

    print(f"\n結果: {passed}/{total} 成功")
    return passed == total


def test_quest_objective_integration():
    print("\n=== Testing QuestObjective Integration ===\n")

    # 従来の目的（後方互換性）
    from main_quest_system import QuestObjective

    obj1 = QuestObjective(
        objective_id="test1",
        description="ゴブリンを5体倒せ",
        target_type="kill",
        target_id="goblin",
        required_count=5,
    )

    print("従来の目的オブジェクト:")
    print(f"  初期状態: {obj1.is_completed}")
    obj1.update("goblin", 3)
    print(f"  3体倒した後: {obj1.is_completed}")
    obj1.update("goblin", 2)
    print(f"  2体追加後: {obj1.is_completed}")

    # CQCT目的
    obj2 = QuestObjective(
        objective_id="test2",
        description="複合条件: ゴブリン3体以上 OR スライム10体以上",
        condition_dsl="(or (>= player.kill_counts.goblin 3) (>= player.kill_counts.slime 10))",
        auto_evaluate=True,
    )
    obj2.build_condition_tree()

    print("\nCQCT目的オブジェクト:")
    print(f"  DSL: {obj2.condition_dsl}")
    print(f"  初期状態: {obj2.is_completed}")

    # テスト用コンテキスト
    player = MockPlayer()
    engine = MockEngine()
    world_state = MockWorldState()

    from quest_condition_evaluator import ParanoidEvaluationContext

    context = ParanoidEvaluationContext(player, engine, world_state)

    print(f"  評価結果: {obj2.evaluate(context)}")

    # 条件を変更してテスト
    player.kill_counts["slime"] = 10
    print(f"  スライム10体後に評価: {obj2.evaluate(context)}")


if __name__ == "__main__":
    success1 = test_condition_system()
    test_quest_objective_integration()

    if success1:
        print("\n🎉 全テスト合格！")
        sys.exit(0)
    else:
        print("\n❌ テスト失敗")
        sys.exit(1)
