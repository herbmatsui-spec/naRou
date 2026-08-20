"""
Tests for MetaProgressionSystem:
1. Dynamic memory fragment procedural generation
2. Randomized cycle modifiers rolling
3. Multi-generation meta goals evaluation and permanent bonus aggregation
4. Reincarnation integration with memory fragments and cycle modifiers
5. SaveSystem serialization & restoration of memory fragments & cycle modifiers
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows cp932 環境対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from components import AchievementComponent
from entity import Entity
from game import Engine
from meta_progression_system import (
    MemoryFragmentData,
    MemoryFragmentGenerator,
    MetaProgressionManager,
)
from save_system import SaveSystem


def test_dynamic_memory_fragment_generation():
    player = Entity(name="BraveHero")
    player.reincarnation_count = 2

    # 1. 戦闘系トリガーでの動的生成
    combat_frag = MemoryFragmentGenerator.generate(
        player=player,
        trigger_type="boss_kill",
        context={"enemy_name": "Ancient Red Dragon"},
    )
    assert combat_frag.category == "combat"
    assert "第3世代" in combat_frag.name
    assert combat_frag.generation == 3
    assert len(combat_frag.buff_traits) > 0
    assert (
        "physical_atk_bonus" in combat_frag.buff_traits
        or "str_bonus" in combat_frag.buff_traits
    )

    # 2. 魔導系トリガーでの動的生成
    magic_frag = MemoryFragmentGenerator.generate(
        player=player, trigger_type="spell_mastery"
    )
    assert magic_frag.category == "magic"
    assert "第3世代" in magic_frag.name
    assert len(magic_frag.buff_traits) > 0

    # 3. 探索系トリガーでの動的生成
    explore_frag = MemoryFragmentGenerator.generate(
        player=player, trigger_type="deep_dungeon"
    )
    assert explore_frag.category == "exploration"
    assert len(explore_frag.buff_traits) > 0


def test_cycle_modifiers_rolling():
    mgr = MetaProgressionManager()
    mgr.registry.load()

    # 固定シードでの決定論的テスト
    mods1 = mgr.roll_cycle_modifiers(count=2, seed=42)
    assert len(mods1) == 2
    assert "name" in mods1[0]
    assert "positive_effects" in mods1[0]

    # ランダム抽選テスト
    mods_rand = mgr.roll_cycle_modifiers(count=2)
    assert len(mods_rand) == 2


def test_meta_goals_evaluation_and_bonuses():
    eng = Engine()
    player = eng.player
    mgr = eng.meta_progression_manager

    # 初期状態
    initial_str = player.attributes.strength

    # 10個の記憶の欠片を付与
    categories = ["combat", "magic", "survival", "exploration", "social"]
    for i in range(10):
        cat = categories[i % len(categories)]
        frag = MemoryFragmentData(
            fragment_id=f"test_frag_{i}",
            name=f"テスト記憶_{i}",
            description="テスト用フレーバー",
            generation=1,
            category=cat,
            buff_traits={"str_bonus": 1.0}
            if cat == "combat"
            else {"magic_atk_bonus": 2.0},
        )
        mgr.add_memory_fragment(player, frag, eng)

    # 記憶の欠片が ReincarnationComponent および StorytellerComponent に登録されていることを確認
    assert len(player.collected_fragments) == 10
    assert len(player.memory_fragments) >= 10

    # メタゴール: fragment_collector_10 (10個収集) と elemental_mastery (4属性以上) が達成されているはず
    assert (
        player.get_component(AchievementComponent).meta_progression.get(
            "fragment_collector_10", 0
        )
        == 1
    )
    assert (
        player.get_component(AchievementComponent).meta_progression.get(
            "elemental_mastery", 0
        )
        == 1
    )

    # 永続ボーナスが適用されていること
    perm_bonuses = player.get_component(AchievementComponent).permanent_bonuses
    assert "magic_power" in perm_bonuses
    assert "resistance_all" in perm_bonuses


def test_reincarnation_with_meta_progression():
    eng = Engine()
    player = eng.player
    player.level = 50

    # 転生実行
    eng.reincarnate()

    # 転生回数・レベルリセットの確認
    assert player.reincarnation_count == 1
    assert player.level == 1
    assert player.exp == 0

    # 動的記憶の欠片が自動生成・付与されていること
    assert len(player.collected_fragments) >= 1
    assert len(player.cycle_modifiers) == 2


def test_save_load_meta_progression_persistence():
    eng = Engine()
    player = eng.player
    mgr = eng.meta_progression_manager

    # 動的記憶と周回特異点を追加
    frag = MemoryFragmentData(
        fragment_id="frag_persist_test",
        name="【第1世代】不朽の刻印",
        description="セーブテスト用",
        generation=1,
        category="combat",
        buff_traits={"str_bonus": 5.0},
    )
    mgr.add_memory_fragment(player, frag, eng)
    player.cycle_modifiers = [{"id": "mod_mana_surge", "name": "魔力奔流の時代"}]

    # セーブ
    save_msg = SaveSystem.save(eng)
    assert "セーブ完了" in save_msg

    # ロード
    loaded, load_msg = SaveSystem.load()
    assert loaded is not None
    assert "ロード完了" in load_msg

    loaded_player = loaded.player
    assert len(loaded_player.collected_fragments) >= 1
    assert any(
        f.get("fragment_id") == "frag_persist_test"
        for f in loaded_player.collected_fragments
        if isinstance(f, dict)
    )
    assert len(loaded_player.cycle_modifiers) == 1
    assert loaded_player.cycle_modifiers[0]["id"] == "mod_mana_surge"


def test_recalculate_bonuses_idempotency_no_inflation():
    eng = Engine()
    player = eng.player
    mgr = eng.meta_progression_manager

    # 筋力ボーナス付きの記憶の欠片を付与
    frag = MemoryFragmentData(
        fragment_id="frag_idempotent_test",
        name="【第1世代】剛腕の残照",
        description="冪等性テスト用",
        generation=1,
        category="combat",
        buff_traits={"str_bonus": 3.0, "speed_bonus": 2.0},
    )
    mgr.add_memory_fragment(player, frag, eng)

    str_after_first = player.attributes.strength
    speed_after_first = player.speed
    hp_after_first = player.max_hp

    # 複数回再計算を呼んでもステータスが増殖しないことを検証
    for _ in range(5):
        mgr.recalculate_and_apply_bonuses(player)

    assert player.attributes.strength == str_after_first
    assert player.speed == speed_after_first
    assert player.max_hp == hp_after_first
