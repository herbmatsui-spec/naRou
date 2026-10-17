"""
test_skill_eater_masterpiece_phase5.py
フェーズ5（Lv40義眼獲得クエストとダイエジェティックUI）の統合テスト
"""
import pytest

from skill_eater_meta_quest_system import SkillEaterQuestSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import (
    CharacterSkillSlot,
    CharacterState,
    SkillDef,
    SkillEaterRegistry,
    SkillTier,
    SkillType,
)


@pytest.fixture
def setup_phase5():
    registry = SkillEaterRegistry.get_instance()
    s_fire = SkillDef(id="eye_fire_01", name="紅蓮剣", tier=SkillTier.RARE, type=SkillType.ACTIVE, memory_cost_mb=25, tags=["Fire", "Combat"])
    s_concept = SkillDef(id="eye_concept_01", name="創世の概念", tier=SkillTier.CONCEPT, type=SkillType.ACTIVE, memory_cost_mb=60)
    registry._skills[s_fire.id] = s_fire
    registry._skills[s_concept.id] = s_concept
    return registry

def test_lv40_cyber_eye_quest():
    quest_sys = SkillEaterQuestSystem()
    hero = CharacterState(id="hero", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10)

    # 1. Lv39では発生しない
    triggered, msg, q = quest_sys.trigger_lv40_cyber_eye_event(hero, current_level=39)
    assert not triggered
    assert not hero.has_cyberpunk_eye

    # 2. Lv40で緊急通信イベント発生
    triggered_ok, msg_ok, quest_obj = quest_sys.trigger_lv40_cyber_eye_event(hero, current_level=40)
    assert triggered_ok
    assert quest_obj.quest_id == "q_cyber_eye_lv40"

    # 3. クエスト完了で義眼覚醒
    done, done_msg = quest_sys.complete_cyber_eye_quest(hero)
    assert done
    assert hero.has_cyberpunk_eye

def test_diegetic_ui_switching(setup_phase5):
    presentation = SkillEaterPresentationSystem.get_instance()
    hero_normal = CharacterState(id="hero1", name="序盤主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10, has_cyberpunk_eye=False)
    hero_cyber = CharacterState(id="hero2", name="Lv40主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10, has_cyberpunk_eye=True)

    enemy_fire = CharacterState(id="enemy1", name="火炎兵", hp=50, max_hp=50, mp=20, max_mp=20, atk=15, defense=5, intelligence=5, speed=8)
    enemy_fire.skills["eye_fire_01"] = CharacterSkillSlot(skill_id="eye_fire_01", is_encrypted=True)

    # 1. 義眼なし：従来テキストUI
    ui_legacy = presentation.build_diegetic_ui_data(analyzer=hero_normal, target=enemy_fire)
    assert not ui_legacy["is_diegetic"]
    assert ui_legacy["ui_mode"] == "LEGACY_TEXT_UI"

    # 2. 義眼あり：ダイエジェティックAR（赤オーラ＋暗号化グリッチ）
    ui_ar = presentation.build_diegetic_ui_data(analyzer=hero_cyber, target=enemy_fire)
    assert ui_ar["is_diegetic"]
    assert ui_ar["ui_mode"] == "CYBERPUNK_AR_HUD"
    assert ui_ar["aura_color"] == "#FF0033"  # 赤
    assert ui_ar["glitch_intensity"] > 0.5   # 暗号化グリッチ
    assert ui_ar["absorption_particle_stream"]

    # 3. 概念スキル持ち：金オーラ
    enemy_god = CharacterState(id="enemy2", name="神官", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=20, intelligence=30, speed=10)
    enemy_god.skills["eye_concept_01"] = CharacterSkillSlot(skill_id="eye_concept_01")
    ui_god = presentation.build_diegetic_ui_data(analyzer=hero_cyber, target=enemy_god)
    assert ui_god["aura_color"] == "#FFD700"  # 金
