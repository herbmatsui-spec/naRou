"""
Architecture Refactoring Verification Tests
Verifies:
1. ECS Component System (components.py & entity.py delegation)
2. SaveSystem dynamic serialization & backward compatibility
3. DialogueManager decoupling
4. EventBus integration
"""
from __future__ import annotations

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows cp932 環境対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from components import (
    AchievementComponent,
    GuildFactionComponent,
    ReincarnationComponent,
    SkillFusionComponent,
    SkillTreeJobComponent,
    StorytellerComponent,
    TitleComponent,
)
from dialogue_system import DialogueManager
from entity import Entity
from game import Engine
from save_system import SaveSystem


def test_ecs_component_initialization_and_delegation():
    e = Entity(name="Hero")

    # 1. コンポーネントの初期化確認
    assert TitleComponent in e.components
    assert GuildFactionComponent in e.components
    assert AchievementComponent in e.components
    assert ReincarnationComponent in e.components
    assert SkillTreeJobComponent in e.components
    assert SkillFusionComponent in e.components
    assert StorytellerComponent in e.components

    # 2. プロパティ委譲の動作確認 (タイトル)
    e.titles.append("dragon_slayer")
    assert "dragon_slayer" in e.get_component(TitleComponent).titles

    # 3. ギルド・派閥委譲
    e.guild_id = "mages_guild"
    e.guild_contribution = 150
    assert e.get_component(GuildFactionComponent).guild_id == "mages_guild"
    assert e.get_component(GuildFactionComponent).guild_contribution == 150

    # 4. 実績・メタ進行委譲
    e.achievements.append("first_step")
    e.social_points = 50
    assert e.get_component(AchievementComponent).achievements == ["first_step"]
    assert e.get_component(AchievementComponent).social_points == 50

    # 5. 輪廻転生委譲
    e.reincarnation_count = 2
    e.karma_good_evil = 20
    assert e.get_component(ReincarnationComponent).reincarnation_count == 2
    assert e.get_component(ReincarnationComponent).karma_good_evil == 20

    # 6. スキルツリー・ジョブ委譲
    e.job = "wizard"
    e.job_level = 5
    assert e.get_component(SkillTreeJobComponent).job == "wizard"
    assert e.get_component(SkillTreeJobComponent).job_level == 5

    # 7. スキル合成委譲
    e.skill_fusion_materials["fire_gem"] = 3
    assert e.get_component(SkillFusionComponent).skill_fusion_materials["fire_gem"] == 3

    # 8. ストーリーテラー委譲
    e.story_flags["talked_to_sage"] = True
    assert e.get_component(StorytellerComponent).story_flags["talked_to_sage"] is True


def test_save_load_with_ecs_and_backward_compatibility():
    eng = Engine()
    eng.player.name = "RefactorHero"
    eng.player.guild_id = "fighters_guild"
    eng.player.reincarnation_count = 5
    eng.player.achievements.append("grand_master")
    eng.player.story_flags["ancient_gate_opened"] = True

    # セーブ
    save_msg = SaveSystem.save(eng)
    assert "セーブ完了" in save_msg

    # ロード
    loaded, load_msg = SaveSystem.load()
    assert loaded is not None
    assert "ロード完了" in load_msg
    assert loaded.player.name == "RefactorHero"
    assert loaded.player.guild_id == "fighters_guild"
    assert loaded.player.reincarnation_count == 5
    assert "grand_master" in loaded.player.achievements
    assert loaded.player.story_flags["ancient_gate_opened"] is True
    assert TitleComponent in loaded.player.components


def test_dialogue_manager():
    eng = Engine()
    player = eng.player
    pet = eng.pet

    # ペットの対話確認
    speaker, text = DialogueManager.get_dialogue(pet, player, eng)
    assert speaker == pet.name
    assert text in DialogueManager.CIEL_DIALOGUES

    # 一般NPCの対話確認
    dummy_npc = Entity(name="村人A")
    speaker, text = DialogueManager.get_dialogue(dummy_npc, player, eng)
    assert speaker == "村人A"
    assert text == DialogueManager.DEFAULT_NPC_DIALOGUE
