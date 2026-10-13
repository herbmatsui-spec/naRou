"""Tests for Husk Units system"""

import pytest
from naRou.ecs.components.components import PuppetUnitComponent
from naRou.skill_eater.skill_eater_husk_units import (
    effective_bonus,
    set_order,
    set_route,
    tick_units,
    update_drone,
    update_escort,
    update_turret,
)


def test_tick_units_active_corruption():
    """Test that active units increment corruption"""
    unit = PuppetUnitComponent(unit_id='u1', role='turret', husk_ref='husk1', state='active', corruption=5)
    class MockPlayer:
        def __init__(self):
            self.units = [unit]

    player = MockPlayer()
    assert unit.corruption == 5
    tick_units(player)
    assert unit.corruption == 6


def test_tick_units_charging_corruption_loyalty():
    """Test that charging units decrease corruption and increase loyalty"""
    unit = PuppetUnitComponent(unit_id='u2', role='drone', husk_ref='husk2', state='charging', corruption=5, loyalty=10)
    class MockPlayer:
        def __init__(self):
            self.units = [unit]

    player = MockPlayer()
    assert unit.corruption == 5
    assert unit.loyalty == 10
    tick_units(player)
    assert unit.corruption == 3  # max(0, 5-2)
    assert unit.loyalty == 11    # 10 + 1


def test_set_order():
    """Test setting unit orders"""
    unit = PuppetUnitComponent(unit_id='u1', role='escort', husk_ref='husk1')

    # Test valid orders
    set_order(unit, 'follow')
    assert unit.order == 'follow'

    set_order(unit, 'hold')
    assert unit.order == 'hold'

    set_order(unit, 'patrol')
    assert unit.order == 'patrol'

    # Test invalid order
    with pytest.raises(ValueError, match="Invalid order"):
        set_order(unit, 'invalid')


def test_update_escort_follows_player():
    """Test that escort units follow the player"""
    unit = PuppetUnitComponent(unit_id='u1', role='escort', husk_ref='husk1', location='base')

    class MockPlayer:
        def __init__(self, location):
            self.location = location

    player = MockPlayer(location='dungeon')
    assert unit.location == 'base'
    update_escort(unit, player)
    assert unit.location == 'dungeon'


def test_update_turret_activates_and_fixes():
    """Test that turret units activate and fix at base"""
    unit = PuppetUnitComponent(unit_id='u1', role='turret', husk_ref='husk1', state='sleep', location='field')

    assert unit.state == 'sleep'
    assert unit.location == 'field'
    update_turret(unit)
    assert unit.state == 'active'
    assert unit.location == 'base'


def test_update_drone_collects_materials():
    """Test that drone units collect materials"""
    unit = PuppetUnitComponent(unit_id='u1', role='drone', husk_ref='husk1')

    class MockWarehouse:
        def __init__(self):
            self.materials = 0

    warehouse = MockWarehouse()
    assert warehouse.materials == 0
    update_drone(unit, warehouse)
    assert warehouse.materials == 1


def test_set_route():
    """Test setting patrol routes"""
    unit = PuppetUnitComponent(unit_id='u1', role='drone', husk_ref='husk1')

    # Test setting route
    assert unit.route == []
    set_route(unit, ['base', 'gate', 'wall'])
    assert unit.route == ['base', 'gate', 'wall']

    # Test changing route
    set_route(unit, ['headquarters'])
    assert unit.route == ['headquarters']


def test_update_escort_non_escot_unaffected():
    """Test that non-escort units are not affected by update_escort"""
    unit = PuppetUnitComponent(unit_id='u1', role='turret', husk_ref='husk1', location='base')

    class MockPlayer:
        def __init__(self, location):
            self.location = location

    player = MockPlayer(location='dungeon')
    assert unit.location == 'base'
    update_escort(unit, player)
    assert unit.location == 'base'  # Should remain unchanged


def test_update_turret_non_turret_unaffected():
    """Test that non-turret units are not affected by update_turret"""
    unit = PuppetUnitComponent(unit_id='u1', role='escort', husk_ref='husk1', location='field')

    assert unit.state == 'sleep'
    assert unit.location == 'field'
    update_turret(unit)
    assert unit.state == 'sleep'  # Should remain unchanged
    assert unit.location == 'field'  # Should remain unchanged


def test_update_drone_non_drone_unaffected():
    """Test that non-drone units are not affected by update_drone"""
    unit = PuppetUnitComponent(unit_id='u1', role='escort', husk_ref='husk1')

    class MockWarehouse:
        def __init__(self):
            self.materials = 5

    warehouse = MockWarehouse()
    assert warehouse.materials == 5
    update_drone(unit, warehouse)
    assert warehouse.materials == 5  # Should remain unchanged


def test_set_route_non_drone_still_works():
    """Test that set_route works on non-drone units (they still have route attribute)"""
    unit = PuppetUnitComponent(unit_id='u1', role='escort', husk_ref='husk1')

    assert unit.route == []
    set_route(unit, ['a', 'b', 'c'])
    assert unit.route == ['a', 'b', 'c']


def test_effective_bonus():
    """Test the effective bonus based on loyalty"""
    # Test 1: Loyalty below 50
    unit = PuppetUnitComponent(unit_id='u1', role='escort', husk_ref='husk1', loyalty=49)
    assert effective_bonus(unit) == 1.0

    # Test 2: Loyalty exactly 50
    unit2 = PuppetUnitComponent(unit_id='u2', role='turret', husk_ref='husk2', loyalty=50)
    assert effective_bonus(unit2) == 1.2

    # Test 3: Loyalty above 50
    unit3 = PuppetUnitComponent(unit_id='u3', role='drone', husk_ref='husk3', loyalty=75)
    assert effective_bonus(unit3) == 1.2

    # Test 4: Loyalty exactly 0
    unit4 = PuppetUnitComponent(unit_id='u4', role='escort', husk_ref='husk4', loyalty=0)
    assert effective_bonus(unit4) == 1.0

    # Test 5: Unit without loyalty attribute
    unit5 = PuppetUnitComponent(unit_id='u5', role='escot', husk_ref='husk5')
    # Remove loyalty attribute if it exists
    if hasattr(unit5, 'loyalty'):
        delattr(unit5, 'loyalty')
    assert effective_bonus(unit5) == 1.0  # Should default to 1.0


def test_tick_units_reboot_state():
    """Test that units with 0 HP enter reboot state (Step 53)"""
    unit = PuppetUnitComponent(unit_id='u1', role='turret', husk_ref='husk1', hp=0, state='active')
    class MockPlayer:
        def __init__(self):
            self.units = [unit]

    player = MockPlayer()
    assert unit.state == 'active'  # Before tick
    assert unit.hp == 0

    tick_units(player)

    assert unit.state == 'reboot'  # Should change to reboot state
    assert unit.hp == 0  # HP should remain 0


def test_tick_units_reboot_state_preserved():
    """Test that units already in reboot state stay in reboot state"""
    unit = PuppetUnitComponent(unit_id='u1', role='turret', husk_ref='husk1', hp=0, state='reboot')
    class MockPlayer:
        def __init__(self):
            self.units = [unit]

    player = MockPlayer()
    assert unit.state == 'reboot'  # Before tick

    tick_units(player)

    assert unit.state == 'reboot'  # Should remain in reboot state


def test_tick_units_negative_hp_reboot():
    """Test that units with negative HP also enter reboot state"""
    unit = PuppetUnitComponent(unit_id='u1', role='turret', husk_ref='husk1', hp=-5, state='active')
    class MockPlayer:
        def __init__(self):
            self.units = [unit]

    player = MockPlayer()
    assert unit.state == 'active'  # Before tick
    assert unit.hp == -5

    tick_units(player)

    assert unit.state == 'reboot'  # Should change to reboot state
    assert unit.hp == -5  # HP should remain unchanged


if __name__ == "__main__":
    test_tick_units_active_corruption()
    test_tick_units_charging_corruption_loyalty()
    test_set_order()
    test_update_escort_follows_player()
    test_update_turret_activates_and_fixes()
    test_update_drone_collects_materials()
    test_set_route()
    test_update_escort_non_escot_unaffected()
    test_update_turret_non_turret_unaffected()
    test_update_drone_non_drone_unaffected()
    test_set_route_non_drone_still_works()
    test_effective_bonus()
    test_tick_units_reboot_state()
    test_tick_units_reboot_state_preserved()
    test_tick_units_negative_hp_reboot()
    print("All tests passed!")
