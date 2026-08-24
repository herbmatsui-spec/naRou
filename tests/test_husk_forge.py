"""Tests for Husk Forge system"""

import pytest
from naRou.systems.skill_eater_husk_forge import PuppetForgeSystem
from naRou.ecs.components.components import HuskComponent


def test_calc_control_load():
    """Test control load calculation"""
    forge = PuppetForgeSystem()
    husk = HuskComponent(husk_id='test', source_monster='test', tier=1)
    
    # No skills or codes
    assert forge.calc_control_load(husk) == 0
    
    # Add skills
    husk.injected_skills = ['fire_bolt', 'heal']
    assert forge.calc_control_load(husk) == 20  # 2 * 10
    
    # Add codes
    husk.injected_codes = ['synergy_fire_heal']
    assert forge.calc_control_load(husk) == 25  # 20 + (1 * 5)
    
    # More skills and codes
    husk.injected_skills = ['a', 'b', 'c', 'd']  # 4 skills
    husk.injected_codes = ['x', 'y', 'z']  # 3 codes
    assert forge.calc_control_load(husk) == (4 * 10) + (3 * 5)  # 40 + 15 = 55


def test_inject_skill():
    """Test skill injection"""
    forge = PuppetForgeSystem()
    husk = HuskComponent(husk_id='test', source_monster='test', tier=2, slots=2)
    
    # Inject skills
    forge.inject_skill(husk, 'fire_bolt')
    assert husk.injected_skills == ['fire_bolt']
    
    forge.inject_skill(husk, 'heal')
    assert husk.injected_skills == ['fire_bolt', 'heal']
    
    # Test capacity limit
    with pytest.raises(ValueError, match="slots full"):
        forge.inject_skill(husk, 'third_skill')


def test_inject_code():
    """Test code injection"""
    forge = PuppetForgeSystem()
    
    # Test 2-slot husk (1 code slot)
    husk = HuskComponent(husk_id='test', source_monster='test', tier=2, slots=2)
    forge.inject_code(husk, 'chimera_a')
    assert husk.injected_codes == ['chimera_a']
    
    with pytest.raises(ValueError, match="code slots full"):
        forge.inject_code(husk, 'chimera_b')
    
    # Test 1-slot husk (1 code slot minimum)
    husk2 = HuskComponent(husk_id='test2', source_monster='test', tier=1, slots=1)
    forge2 = PuppetForgeSystem()
    forge2.inject_code(husk2, 'chimera_single')
    assert husk2.injected_codes == ['chimera_single']
    
    with pytest.raises(ValueError, match="code slots full"):
        forge2.inject_code(husk2, 'chimera_second')
    
    # Test 4-slot husk (2 code slots)
    husk3 = HuskComponent(husk_id='test3', source_monster='test', tier=4, slots=4)
    forge3 = PuppetForgeSystem()
    forge3.inject_code(husk3, 'chimera_x')
    forge3.inject_code(husk3, 'chimera_y')
    assert husk3.injected_codes == ['chimera_x', 'chimera_y']
    
    with pytest.raises(ValueError, match="code slots full"):
        forge3.inject_code(husk3, 'chimera_z')


def test_role_of():
    """Test role determination"""
    forge = PuppetForgeSystem()
    
    # No skills - default to escort
    husk = HuskComponent(husk_id='test', source_monster='test', tier=1)
    assert forge.role_of(husk) == 'escort'
    
    # Attack skills - escort
    husk2 = HuskComponent(husk_id='test2', source_monster='test', tier=2)
    husk2.injected_skills = ['fire_bolt', 'ice_shard']
    assert forge.role_of(husk2) == 'escort'
    
    # Defense skills - turret
    husk3 = HuskComponent(husk_id='test3', source_monster='test', tier=2)
    husk3.injected_skills = ['heal', 'shield']
    assert forge.role_of(husk3) == 'turret'
    
    # Movement skills - drone
    husk4 = HuskComponent(husk_id='test4', source_monster='test', tier=2)
    husk4.injected_skills = ['dash', 'teleport']
    assert forge.role_of(husk4) == 'drone'
    
    # Tie breaking: attack > defense > movement
    husk5 = HuskComponent(husk_id='test5', source_monster='test', tier=2)
    husk5.injected_skills = ['fire_bolt', 'heal']  # 1 attack, 1 defense
    assert forge.role_of(husk5) == 'escort'
    
    husk6 = HuskComponent(husk_id='test6', source_monster='test', tier=2)
    husk6.injected_skills = ['heal', 'dash']  # 1 defense, 1 movement
    assert forge.role_of(husk6) == 'turret'
    
    # Unknown skill defaults to attack
    husk7 = HuskComponent(husk_id='test7', source_monster='test', tier=1)
    husk7.injected_skills = ['unknown_skill']
    assert forge.role_of(husk7) == 'escort'


def test_rebellion_risk():
    """Test rebellion risk calculation"""
    forge = PuppetForgeSystem()
    
    # No skills, no loyalty
    husk = HuskComponent(husk_id='test', source_monster='test', tier=1)
    assert forge.rebellion_risk(husk) == 0.0
    
    # With skills, no loyalty
    husk2 = HuskComponent(husk_id='test2', source_monster='test', tier=2)
    husk2.injected_skills = ['fire_bolt', 'ice_shard']  # 2 skills = 20 control load
    assert forge.rebellion_risk(husk2) == 0.2  # (20 - 0)/100 = 0.2
    
    # With loyalty reducing risk
    husk3 = HuskComponent(husk_id='test3', source_monster='test', tier=2)
    husk3.injected_skills = ['fire_bolt', 'ice_shard']  # 20 control load
    husk3.loyalty = 5  # 5 loyalty
    assert forge.rebellion_risk(husk3) == 0.1  # (20 - 5*2)/100 = 0.1
    
    # High loyalty eliminating risk
    husk4 = HuskComponent(husk_id='test4', source_monster='test', tier=2)
    husk4.injected_skills = ['fire_bolt', 'ice_shard']  # 20 control load
    husk4.loyalty = 15  # 15 loyalty
    assert forge.rebellion_risk(husk4) == 0.0  # (20 - 15*2)/100 = -0.1 -> 0.0
    
    # Risk can exceed 1.0
    husk5 = HuskComponent(husk_id='test5', source_monster='test', tier=3)
    husk5.injected_skills = ['fire_bolt'] * 10  # 10 skills = 100 control load
    husk5.loyalty = 0
    assert forge.rebellion_risk(husk5) == 1.0  # (100 - 0)/100 = 1.0
    
    husk6 = HuskComponent(husk_id='test6', source_monster='test', tier=3)
    husk6.injected_skills = ['fire_bolt'] * 15  # 15 skills = 150 control load
    husk6.loyalty = 0
    assert forge.rebellion_risk(husk6) == 1.5  # (150 - 0)/100 = 1.5


def test_effective_power():
    """Test effective power calculation"""
    forge = PuppetForgeSystem()
    
    # Base case: no skills, no loyalty, protocol rank 0
    husk = HuskComponent(husk_id='test', source_monster='test', tier=1)
    assert forge.effective_power(husk, 0) == 1.0  # 1.0 + 0.0 - 0.0 = 1.0
    
    # With skills reducing power
    husk2 = HuskComponent(husk_id='test2', source_monster='test', tier=2)
    husk2.injected_skills = ['fire_bolt', 'ice_shard']  # 2 skills = 20 control load
    assert forge.effective_power(husk2, 0) == 0.8  # 1.0 + 0.0 - 0.2 = 0.8
    
    # With loyalty increasing power (by reducing risk)
    husk3 = HuskComponent(husk_id='test3', source_monster='test', tier=2)
    husk3.injected_skills = ['fire_bolt', 'ice_shard']  # 20 control load
    husk3.loyalty = 5
    assert forge.effective_power(husk3, 0) == 0.9  # 1.0 + 0.0 - 0.1 = 0.9
    
    # With protocol rank increasing base power
    husk4 = HuskComponent(husk_id='test4', source_monster='test', tier=2)
    husk4.injected_skills = ['fire_bolt']  # 1 skill = 10 control load
    husk4.loyalty = 0
    assert forge.effective_power(husk4, 5) == 1.4  # 1.0 + 0.5 - 0.1 = 1.4
    
    # Power clamped to minimum 0.1
    husk5 = HuskComponent(husk_id='test5', source_monster='test', tier=2)
    husk5.injected_skills = ['fire_bolt'] * 20  # 20 skills = 200 control load
    husk5.loyalty = 0
    assert forge.effective_power(husk5, 0) == 0.1  # 1.0 + 0.0 - 2.0 = -1.0 -> clamped to 0.1
    
    # Test with high protocol rank and high loyalty
    husk6 = HuskComponent(husk_id='test6', source_monster='test', tier=1)
    husk6.injected_skills = ['heal']  # 1 skill = 10 control load (defense)
    husk6.loyalty = 10  # 10 loyalty
    assert forge.effective_power(husk6, 10) == 2.0  # 1.0 + 1.0 - 0.0 = 2.0 (risk = (10-10*2)/100 = 0.0)


def test_integration():
    """Test integration of all forge functions"""
    forge = PuppetForgeSystem()
    husk = HuskComponent(husk_id='integration_test', source_monster='slime', tier=3, slots=3)
    
    # Start with no injections
    assert forge.calc_control_load(husk) == 0
    assert forge.role_of(husk) == 'escort'
    assert forge.rebellion_risk(husk) == 0.0
    assert forge.effective_power(husk, 0) == 1.0
    
    # Add attack skills
    forge.inject_skill(husk, 'fire_bolt')
    forge.inject_skill(husk, 'ice_shard')
    assert len(husk.injected_skills) == 2
    assert forge.calc_control_load(husk) == 20
    assert forge.role_of(husk) == 'escort'
    assert forge.rebellion_risk(husk) == 0.2  # (20 - 0)/100
    assert forge.effective_power(husk, 0) == 0.8  # 1.0 - 0.2
    
    # Add a defense skill
    forge.inject_skill(husk, 'heal')
    assert len(husk.injected_skills) == 3
    assert forge.calc_control_load(husk) == 30
    assert forge.role_of(husk) == 'escort'  # Still attack majority (2 vs 1)
    assert forge.rebellion_risk(husk) == 0.3  # (30 - 0)/100
    assert forge.effective_power(husk, 0) == 0.7  # 1.0 - 0.3
    
    # Add codes (3 skill slots -> 1 code slot)
    forge.inject_code(husk, 'synergy_fire_ice')
    assert len(husk.injected_codes) == 1
    assert forge.calc_control_load(husk) == 35  # 30 + (1*5)
    assert forge.rebellion_risk(husk) == 0.35  # (35 - 0)/100
    assert forge.effective_power(husk, 0) == 0.65  # 1.0 - 0.35
    
    # Test code capacity limit
    with pytest.raises(ValueError, match="code slots full"):
        forge.inject_code(husk, 'synergy_fire_heal')
    
    # Test with loyalty and protocol rank
    husk.loyalty = 10
    assert forge.rebellion_risk(husk) == 0.15  # (35 - 10*2)/100 = (35-20)/100 = 0.15
    assert forge.effective_power(husk, 5) == 1.35  # 1.0 + 0.5 - 0.15 = 1.35
    
    # Recreate with correct expectations for 4-slot husk
    husk2 = HuskComponent(husk_id='integration_test2', source_monster='slime', tier=4, slots=4)
    forge2 = PuppetForgeSystem()
    
    # Add skills
    forge2.inject_skill(husk2, 'fire_bolt')
    forge2.inject_skill(husk2, 'ice_shard')
    forge2.inject_skill(husk2, 'heal')
    forge2.inject_skill(husk2, 'shield')
    assert len(husk2.injected_skills) == 4
    
    # Add codes (4 skill slots -> 2 code slots)
    forge2.inject_code(husk2, 'synergy_fire_ice')
    forge2.inject_code(husk2, 'synergy_heal_shield')
    assert len(husk2.injected_codes) == 2
    
    # Check final state
    assert forge2.calc_control_load(husk2) == (4 * 10) + (2 * 5)  # 40 + 10 = 50
    assert forge2.role_of(husk2) == 'escort'  # 2 attack, 2 defense -> attack wins tie
    assert forge2.rebellion_risk(husk2) == 0.5  # (50 - 0*2)/100 = 0.5
    assert forge2.effective_power(husk2, 0) == 0.5  # 1.0 - 0.5 = 0.5
    
    # Test capacity limits
    with pytest.raises(ValueError, match="slots full"):
        forge2.inject_skill(husk2, 'extra_skill')
    
    with pytest.raises(ValueError, match="code slots full"):
        forge2.inject_code(husk2, 'extra_code')