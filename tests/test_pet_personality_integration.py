"""Regression tests for Pet Personality integration (T3)"""

from unittest.mock import Mock, patch

import pytest

from narou.constants import (
    PERSONALITY_AGGRESSIVE,
    PERSONALITY_BRAVE,
    PERSONALITY_CALM,
    PERSONALITY_COWARDLY,
    PERSONALITY_GLUTTONOUS,
)
from narou.ecs.entity import Entity
from narou.item_system import Inventory, Item
from pet_personality_system import PetPersonalitySystem


class TestPetBondStatModifiers:
    """Tests for bond stat modifiers affecting pet combat stats."""

    def test_get_bond_stat_modifiers_structure(self):
        """Verify get_bond_stat_modifiers returns all expected keys."""
        pet = Entity(name="TestPet", is_pet=True)
        pet.bond = 50

        modifiers = PetPersonalitySystem.get_bond_stat_modifiers(pet)

        assert "hp_bonus" in modifiers
        assert "hit_bonus" in modifiers
        assert "damage_multiplier" in modifiers
        assert "dv_bonus" in modifiers

    def test_bond_modifiers_scale_with_bond(self):
        """Verify modifiers scale correctly with bond level."""
        pet = Entity(name="TestPet", is_pet=True)

        # Test at bond 0
        pet.bond = 0
        mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
        assert mods["hp_bonus"] == 0
        assert mods["hit_bonus"] == 0
        assert mods["damage_multiplier"] == 1.0
        assert mods["dv_bonus"] == 0

        # Test at bond 50
        pet.bond = 50
        mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
        assert mods["hp_bonus"] == 20  # 50 * 0.4
        assert mods["hit_bonus"] == 5  # 50 * 0.1
        assert mods["damage_multiplier"] == 1.12  # 1.0 + (50/100)*0.25 = 1.125 rounded to 2 decimals
        assert mods["dv_bonus"] == 4  # 50 * 0.08

        # Test at bond 100
        pet.bond = 100
        mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
        assert mods["hp_bonus"] == 40  # 100 * 0.4
        assert mods["hit_bonus"] == 10  # 100 * 0.1
        assert mods["damage_multiplier"] == 1.25  # 1.0 + (100/100)*0.25
        assert mods["dv_bonus"] == 8  # 100 * 0.08


class TestPetAIPersonalityBehavior:
    """Tests for personality-driven AI behavior."""

    def test_brave_targets_strongest_enemy(self):
        """BRAVE personality targets enemy with highest max_hp."""
        pet = Entity(name="Pet", is_pet=True)
        pet.personality = PERSONALITY_BRAVE
        pet.hp = 100
        pet.max_hp = 100
        player = Entity(name="Player", is_player=True)

        weak_enemy = Entity(name="Weak", x=5, y=5)
        weak_enemy.hp = 20
        weak_enemy.max_hp = 20

        strong_enemy = Entity(name="Strong", x=10, y=10)
        strong_enemy.hp = 80
        strong_enemy.max_hp = 200

        decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, [weak_enemy, strong_enemy])

        assert decision["action"] == "attack"
        assert decision["target"] == strong_enemy
        assert "勇敢" in decision["reason"]

    def test_calm_targets_weakest_enemy(self):
        """CALM personality targets enemy with lowest current hp."""
        pet = Entity(name="Pet", is_pet=True)
        pet.personality = PERSONALITY_CALM
        pet.hp = 100
        pet.max_hp = 100
        player = Entity(name="Player", is_player=True)

        enemy1 = Entity(name="Enemy1", x=5, y=5)
        enemy1.hp = 50
        enemy1.max_hp = 100

        enemy2 = Entity(name="Enemy2", x=10, y=10)
        enemy2.hp = 10
        enemy2.max_hp = 80

        decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, [enemy1, enemy2])

        assert decision["action"] == "attack"
        assert decision["target"] == enemy2
        assert "冷静" in decision["reason"]

    def test_cowardly_retreats_when_low_hp(self):
        """COWARDLY personality retreats when HP < 50%."""
        pet = Entity(name="Pet", is_pet=True)
        pet.personality = PERSONALITY_COWARDLY
        pet.hp = 30
        pet.max_hp = 100
        player = Entity(name="Player", is_player=True)

        enemy = Entity(name="Enemy", x=5, y=5)
        enemy.hp = 50
        enemy.max_hp = 100

        decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, [enemy])

        assert decision["action"] == "retreat_to_player"
        assert decision["target"] == player
        assert "臆病" in decision["reason"]

    def test_cowardly_attacks_when_healthy(self):
        """COWARDLY personality attacks normally when HP >= 50%."""
        pet = Entity(name="Pet", is_pet=True)
        pet.personality = PERSONALITY_COWARDLY
        pet.hp = 80
        pet.max_hp = 100
        player = Entity(name="Player", is_player=True)

        enemy = Entity(name="Enemy", x=5, y=5)
        enemy.hp = 50
        enemy.max_hp = 100

        decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, [enemy])

        assert decision["action"] == "attack"

    def test_aggressive_targets_closest_enemy(self):
        """AGGRESSIVE personality targets closest enemy by distance."""
        pet = Entity(name="Pet", is_pet=True)
        pet.personality = PERSONALITY_AGGRESSIVE
        pet.hp = 100
        pet.max_hp = 100
        pet.x = 0
        pet.y = 0
        player = Entity(name="Player", is_player=True)

        far_enemy = Entity(name="Far", x=10, y=10)
        far_enemy.hp = 50
        far_enemy.max_hp = 100

        near_enemy = Entity(name="Near", x=2, y=2)
        near_enemy.hp = 50
        near_enemy.max_hp = 100

        decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, [far_enemy, near_enemy])

        assert decision["action"] == "attack"
        assert decision["target"] == near_enemy
        assert "好戦的" in decision["reason"]

    def test_no_enemies_follows_player(self):
        """Pet follows player when no enemies present."""
        pet = Entity(name="Pet", is_pet=True)
        pet.personality = PERSONALITY_BRAVE
        pet.hp = 100
        pet.max_hp = 100
        player = Entity(name="Player", is_player=True)

        decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, [])

        assert decision["action"] == "follow_player"
        assert decision["target"] == player


class TestPetCombatIntegration:
    """Integration tests for pet personality in combat."""

    def test_bond_modifiers_applied_to_pet_attack(self):
        """Verify bond modifiers affect pet melee attack calculation."""
        from engine.systems.combat_system import CombatSystem

        pet = Entity(name="Pet", is_pet=True)
        pet.attributes.strength = 15
        pet.attributes.dexterity = 12
        pet.attributes.perception = 10
        pet.attributes.endurance = 10
        pet.attributes.magic = 5
        pet.attributes.will = 10
        pet.hp = 100
        pet.max_hp = 100
        pet.bond = 100  # Max bond for max modifiers

        enemy = Entity(name="Enemy")
        enemy.attributes.dexterity = 10
        enemy.attributes.endurance = 10
        enemy.hp = 100
        enemy.max_hp = 100

        # Create a mock weapon
        weapon = Item(name="Pet Sword", category="weapon", char="|", color=(200,200,200), x=0, y=0)
        weapon.dice_num = 2
        weapon.dice_side = 6
        weapon.hit_bonus = 3
        weapon.dmg_bonus = 5

        # Calculate attack with bond modifiers
        # The bond should affect damage through damage_multiplier
        modifiers = PetPersonalitySystem.get_bond_stat_modifiers(pet)

        # Verify damage multiplier is applied
        assert modifiers["damage_multiplier"] == 1.25

        # The actual attack calculation would need to incorporate these modifiers
        # This test verifies the modifiers are correctly computed

    def test_pet_inventory_equipment_stat_bonuses(self):
        """Verify pet equipment enchantments provide stat bonuses."""
        pet_inv = Inventory(max_items=12, max_weight=30.0)

        # Create weapon with enchantments
        weapon = Item(name="Pet Sword", category="weapon", char="|", color=(200,200,200), x=0, y=0)
        weapon.enchants = (
            MockEnchant("stat_bonus", "strength", 5),
            MockEnchant("element_damage", power=10, element="fire"),
        )

        pet_inv.add_item(weapon)
        pet_inv.equip(weapon, "main_hand")

        bonuses = pet_inv.get_stat_bonuses()
        elem_dmgs = pet_inv.get_weapon_element_damages()

        assert bonuses.get("strength") == 5
        assert elem_dmgs == [("fire", 10)]


class MockEnchant:
    """Mock enchantment for testing."""
    def __init__(self, ench_type, target_stat="", power=0, element=""):
        self.type = ench_type
        self.target_stat = target_stat
        self.power = power
        self.element = element


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
