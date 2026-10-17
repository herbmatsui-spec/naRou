"""
test_skill_eater_masterpiece_phase1_2.py
フェーズ1（メモリ・オーバークロック）とフェーズ2（暗号化・トラップ・解析ハック）の統合テスト
"""
import pytest

from skill_eater_combat_system import SkillEaterCombatSystem
from skill_eater_system import (
    CharacterSkillSlot,
    CharacterState,
    SkillDef,
    SkillEaterRegistry,
    SkillTier,
    SkillType,
)


@pytest.fixture
def combat_setup():
    registry = SkillEaterRegistry.get_instance()
    # テスト用スキル登録
    s1 = SkillDef(id="test_fire_01", name="爆炎魔法", tier=SkillTier.COMMON, type=SkillType.ACTIVE, memory_cost_mb=40)
    s2 = SkillDef(id="test_ice_01", name="絶対零度", tier=SkillTier.RARE, type=SkillType.ACTIVE, memory_cost_mb=50)
    s3 = SkillDef(id="test_trap_01", name="偽装ウイルス", tier=SkillTier.UNIQUE, type=SkillType.ACTIVE, memory_cost_mb=40, is_encrypted=True, is_trap=True, trap_penalty="Virus")
    s4 = SkillDef(id="test_locked_01", name="神聖防壁", tier=SkillTier.UNIQUE, type=SkillType.PASSIVE, memory_cost_mb=60, is_encrypted=True, unlock_conditions=[{"type": "element", "element": "Ice"}])

    registry._skills[s1.id] = s1
    registry._skills[s2.id] = s2
    registry._skills[s3.id] = s3
    registry._skills[s4.id] = s4

    combat_sys = SkillEaterCombatSystem(registry=registry)
    return combat_sys, registry

def test_memory_overclock_and_brain_fry(combat_setup):
    combat_sys, registry = combat_setup
    hero = CharacterState(id="hero", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10, base_memory_capacity_mb=100)

    # 1. 2つのスキルを装備（40MB + 50MB = 90MB -> 90% 容量内）
    hero.add_skill("test_fire_01")
    hero.add_skill("test_ice_01")
    assert hero.current_used_memory_mb == 90
    assert hero.overclock_level == 0

    res = combat_sys.process_turn_end(hero)
    assert res["overclock_damage"] == 0
    assert hero.hp == 100

    # 2. 3つ目（+40MB = 130MB -> 30% オーバークロック）
    hero.add_skill("test_trap_01")
    assert hero.current_used_memory_mb == 130
    assert hero.overclock_level == 30

    res = combat_sys.process_turn_end(hero)
    assert res["overclock_damage"] > 0
    assert hero.hp < 100

    # 3. 致命的オーバークロック（150%以上）
    hero.base_memory_capacity_mb = 50  # 130MB / 50MB = 160%超過
    hero.calculate_memory_usage()
    assert hero.overclock_level >= 150

    res = combat_sys.process_turn_end(hero)
    assert hero.hp == 0
    assert not res["is_alive"]

def test_encrypted_trap_and_analysis_hack(combat_setup):
    combat_sys, registry = combat_setup
    hero = CharacterState(id="hero", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10)
    enemy = CharacterState(id="enemy", name="ミダス警備兵", hp=50, max_hp=50, mp=20, max_mp=20, atk=10, defense=5, intelligence=5, speed=8)

    # 敵にトラップスキルとロック付きスキルを設定
    enemy.skills["test_trap_01"] = CharacterSkillSlot(skill_id="test_trap_01", is_encrypted=True, is_trap=True, trap_penalty="Virus")
    enemy.skills["test_locked_01"] = CharacterSkillSlot(skill_id="test_locked_01", is_encrypted=True, unlock_conditions=[{"type": "element", "element": "Ice"}])

    # 1. 暗号化トラップを無理やり喰らおうとするとトラップ発動
    res_devour = combat_sys.execute_devour(predator=hero, prey=enemy, target_skill_id="test_trap_01")
    assert not res_devour.success
    assert "Virus" in hero.status_effects
    assert hero.hp < 100

    # 2. 解析ハッキングを実行
    scan_res = combat_sys.execute_analysis_hack(analyzer=hero, target=enemy)
    assert len(scan_res.revealed_skills) == 2
    assert "Ice" in scan_res.revealed_skills[1].flavor_text

    # 3. 弱点（Ice）攻撃を当ててプロテクト解除
    unlocked = combat_sys.check_and_unlock_conditions(attacker=hero, defender=enemy, action_element="Ice")
    assert len(unlocked) == 1
    assert not enemy.skills["test_locked_01"].is_encrypted

    # 4. プロテクト解除後は安全に喰らえる
    res_devour_ok = combat_sys.execute_devour(predator=hero, prey=enemy, target_skill_id="test_locked_01", force_success=True)
    assert res_devour_ok.success
    assert hero.has_skill("test_locked_01")
