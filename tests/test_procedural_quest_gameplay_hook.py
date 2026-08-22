"""
プロシージャル・クエスト生成システム ゲームプレイ統合テスト
実際のゲームイベント（撃破/採取/探索）から生成クエストが進捗・達成されることを検証。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from entity import Entity
from game import Engine
from procedural_quest_generator import (
    REGISTRY,
    GeneratedQuest,
    ProceduralQuestGenerator,
    ProceduralQuestManager,
    QuestObjectiveSpec,
)


def _make_kill_quest(quest_id: str, target: str = "goblin", count: int = 3) -> dict:
    q = GeneratedQuest(
        quest_id=quest_id,
        title="t",
        source_type="board",
        archetype_id="slay",
        difficulty_id="tutorial",
        reward_id="copper",
        setting_id="forest",
        objectives=[QuestObjectiveSpec("slay_obj", "討伐", "kill", target, count)],
        reward={"gold": 100, "exp": 10, "items": [], "bonus": {"fame": 1}},
    )
    return q.to_dict()


def test_procedural_quest_gameplay_hooks():
    print("=== プロシージャル・クエスト ゲームプレイ統合検証開始 ===")
    REGISTRY.load()
    gen = ProceduralQuestGenerator(REGISTRY)
    mgr = ProceduralQuestManager(gen)

    # 1) 曖昧照合: 生成時 target="goblin" に対し、実体名 "ゴブリン" で進捗する
    p = Entity()
    p.procedural_quest.accepted_quests.append(_make_kill_quest("gen_fuzzy"))
    gold_before = p.gold
    mgr.update_progress(p, "kill", "ゴブリン", 1)
    mgr.update_progress(p, "kill", "ゴブリン", 1)
    mgr.update_progress(p, "kill", "ゴブリン", 1)  # 3回で自動達成
    assert (
        p.gold > gold_before and p.procedural_quest.completed_count >= 1
    ), "Fuzzy kill matching failed"
    print("[OK] 曖昧照合: target='goblin' に 実体名='ゴブリン' の撃破で進捗・達成")

    # 2) Engine フック: _progress_generated_quests 経由で報酬が付与される
    eng = Engine()
    eng.player.procedural_quest.accepted_quests.append(_make_kill_quest("gen_hook"))
    g_before = eng.player.gold
    eng._progress_generated_quests("kill", "ゴブリン", 1)
    eng._progress_generated_quests("kill", "ゴブリン", 1)
    eng._progress_generated_quests("kill", "ゴブリン", 1)
    assert eng.player.gold > g_before, "Engine hook did not grant reward"
    print("[OK] Engine フック: _progress_generated_quests で討伐進捗→報酬付与")

    # 3) 採取イベント: collect で進捗（アイテム名で照合）
    p2 = Entity()
    cq = GeneratedQuest(
        quest_id="gen_collect",
        title="c",
        source_type="board",
        archetype_id="gather",
        difficulty_id="tutorial",
        reward_id="copper",
        setting_id="forest",
        objectives=[QuestObjectiveSpec("gather_obj", "採取", "collect", "herb", 2)],
        reward={"gold": 50, "exp": 5, "items": [], "bonus": {}},
    )
    p2.procedural_quest.accepted_quests.append(cq.to_dict())
    gc = p2.gold
    mgr.update_progress(p2, "collect", "herb", 1)
    mgr.update_progress(p2, "collect", "herb", 1)
    assert p2.gold > gc, "Collect progress failed"
    print("[OK] 採取イベント: collect で進捗・達成")

    # 4) 探索イベント: explore(depth) で進捗
    p3 = Entity()
    eq = GeneratedQuest(
        quest_id="gen_explore",
        title="e",
        source_type="dungeon",
        archetype_id="explore",
        difficulty_id="normal",
        reward_id="gold",
        setting_id="cave",
        objectives=[QuestObjectiveSpec("explore_obj", "探索", "explore", "depth", 3)],
        reward={"gold": 200, "exp": 50, "items": [], "bonus": {}},
    )
    p3.procedural_quest.accepted_quests.append(eq.to_dict())
    ge = p3.gold
    mgr.update_progress(p3, "explore", "depth", 1)
    mgr.update_progress(p3, "explore", "depth", 1)
    mgr.update_progress(p3, "explore", "depth", 1)
    assert p3.gold > ge, "Explore progress failed"
    print("[OK] 探索イベント: explore(depth) で進捗・達成")

    print("\nPROCEDURAL QUEST GAMEPLAY HOOKS VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    test_procedural_quest_gameplay_hooks()
