"""
test_skill_eater_masterpiece_phase3.py
フェーズ3（ダーク・エコノミー＆脳拡張インプラント）の統合テスト
"""
import pytest

from skill_eater_black_market import (
    CyberDoctorSurgery,
    MarketTrends,
    calculate_skill_market_value,
    sell_skill_to_black_market,
)
from skill_eater_system import CharacterState, SkillDef, SkillEaterRegistry, SkillTier, SkillType


@pytest.fixture
def market_setup():
    registry = SkillEaterRegistry.get_instance()
    s1 = SkillDef(id="mkt_fire_01", name="地獄の業火", tier=SkillTier.RARE, type=SkillType.ACTIVE, memory_cost_mb=30, tags=["Fire", "Combat"])
    s2 = SkillDef(id="mkt_def_01", name="鉄壁防御", tier=SkillTier.COMMON, type=SkillType.PASSIVE, memory_cost_mb=20, tags=["Defense"])
    registry._skills[s1.id] = s1
    registry._skills[s2.id] = s2
    return registry

def test_market_trends_and_pricing(market_setup):
    registry = market_setup
    s_fire = registry.get_skill("mkt_fire_01")
    s_def = registry.get_skill("mkt_def_01")

    trends = MarketTrends(high_demand_tags=["Fire"], low_demand_tags=["Defense"])

    # 流行中のFire属性は1.5倍
    price_fire = calculate_skill_market_value(s_fire, trends)
    base_fire = 30 * 50 * 2.5  # 3750
    assert price_fire == int(base_fire * 1.5)

    # 不人気のDefense属性は0.6倍
    price_def = calculate_skill_market_value(s_def, trends)
    base_def = 20 * 50 * 1.0  # 1000
    assert price_def == int(base_def * 0.6)

    # トレンドのシフト
    shifted = trends.shift_trends()
    assert len(shifted["high_demand"]) == 2
    assert trends.turn_counter == 1

def test_skill_selling_and_memory_recovery(market_setup):
    registry = market_setup
    hero = CharacterState(id="hero", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10, base_memory_capacity_mb=100)
    hero.add_skill("mkt_fire_01")
    assert hero.has_skill("mkt_fire_01")
    assert hero.current_used_memory_mb == 30

    trends = MarketTrends(high_demand_tags=["Fire"], low_demand_tags=[])
    success, credits_gained, msg = sell_skill_to_black_market(hero, "mkt_fire_01", trends)

    assert success
    assert credits_gained > 0
    assert not hero.has_skill("mkt_fire_01")
    assert hero.current_used_memory_mb == 0  # スキル売却でメモリ解放

def test_cyber_doctor_surgery():
    hero = CharacterState(id="hero", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=15, speed=10, base_memory_capacity_mb=100)

    # 1. クレジット不足で失敗
    ok, cost, msg = CyberDoctorSurgery.perform_memory_expansion(hero, credits_available=100, expansion_mb=20)
    assert not ok
    assert hero.base_memory_capacity_mb == 100

    # 2. クレジット十分で成功（100MB -> 120MB）
    first_cost = CyberDoctorSurgery.calculate_expansion_cost(100)
    ok, spent, msg = CyberDoctorSurgery.perform_memory_expansion(hero, credits_available=10000, expansion_mb=20)
    assert ok
    assert spent == first_cost
    assert hero.base_memory_capacity_mb == 120

    # 3. 2回目の手術は費用が上がる（指数関数的）
    second_cost = CyberDoctorSurgery.calculate_expansion_cost(120)
    assert second_cost > first_cost
