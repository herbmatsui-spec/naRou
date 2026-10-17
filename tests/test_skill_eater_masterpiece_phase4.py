"""
test_skill_eater_masterpiece_phase4.py
フェーズ4（既存サブシステムとの有機的結合：派遣＆防衛）の統合テスト
"""
import pytest

from skill_eater_base_defense import BaseDefenseManager
from skill_eater_pet_dispatch import PetDispatchManager
from skill_eater_system import CharacterState, SkillDef, SkillEaterRegistry, SkillTier, SkillType


@pytest.fixture
def setup_subsystems():
    registry = SkillEaterRegistry.get_instance()
    s = SkillDef(id="sub_test_01", name="防衛テストスキル", tier=SkillTier.COMMON, type=SkillType.PASSIVE, memory_cost_mb=20)
    registry._skills[s.id] = s
    return registry

def test_pet_dispatch_market_missions():
    mgr = PetDispatchManager()

    # 1. 闇市場インテリジェンス偵察ミッション
    res_intel = mgr.start_dispatch(pet_id="cyber_homunculus_01", dungeon_id="black_market_recon", duration_turns=2)
    assert res_intel["success"]

    # 成功解決
    res_resolve = mgr.resolve_dispatch(pet_id="cyber_homunculus_01", force_success=True)
    assert res_resolve["success"]
    assert "market_forecast" in res_resolve["rewards"]
    assert "Fire" in res_resolve["rewards"]["market_forecast"]

    # 2. 相場操作ミッション
    mgr.pets["husk_hound_01"]["equipped_skills"].append("Analysis Helper")
    res_rumor = mgr.start_dispatch(pet_id="husk_hound_01", dungeon_id="rumor_manipulation", duration_turns=3)
    assert res_rumor["success"]

    res_rumor_resolve = mgr.resolve_dispatch(pet_id="husk_hound_01", force_success=True)
    assert res_rumor_resolve["success"]
    assert res_rumor_resolve["rewards"].get("market_manipulation_applied")

def test_base_defense_rewards_and_penalties(setup_subsystems):
    defense_mgr = BaseDefenseManager()
    hero = CharacterState(id="hero", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10, base_memory_capacity_mb=100)
    hero.add_skill("sub_test_01")

    # 1. 防衛成功：脳拡張インプラント素材ドロップで容量 +5MB
    victory_res = defense_mgr.resolve_raid_outcome(is_victory=True, character=hero)
    assert victory_res["success"]
    assert hero.base_memory_capacity_mb == 105
    assert "brain_implant_chip_5mb" in victory_res["reward_drops"]

    # 2. 防衛失敗：スキル略奪ペナルティ
    defeat_res = defense_mgr.resolve_raid_outcome(is_victory=False, character=hero)
    assert not defeat_res["success"]
    assert defeat_res["looted_skill_id"] == "sub_test_01"
    assert not hero.has_skill("sub_test_01")  # 略奪されて消失
