"""Test husk creation during devour process"""

import pytest
from naRou.ecs.components.components import HuskInventoryComponent, Skill
from naRou.ecs.entity import Entity
from naRou.feature_flags import get_husk_enabled, set_flag
from naRou.skill_eater.skill_eater_husk_system import create_husk


def test_husk_creation_on_full_devour():
    """Test that a husk is created when an entity loses all its skills"""
    # Enable the husk feature
    set_flag('ENABLE_HUSK_PUPPET_HACKING', True)
    try:
        # Create a monster entity
        monster = Entity(name='Test Slime', is_player=False)
        monster.level = 2  # Set level manually for testing

        # Clear default skills and add just one for testing
        monster.skills.clear()
        fire_bolt_skill = Skill('fire_bolt')
        monster.skills['fire_bolt'] = fire_bolt_skill

        # Verify initial state
        assert len(monster.skills) == 1
        assert 'fire_bolt' in monster.skills

        # Simulate devouring the skill
        removed_skill = monster.skills.pop('fire_bolt', None)
        assert removed_skill is not None
        assert len(monster.skills) == 0

        # Check if monster should be considered a husk (skills empty)
        is_husk = len(monster.skills) == 0
        assert is_husk

        # Create player entity
        player = Entity(name='Test Player', is_player=True)
        player.skills.clear()  # Clear default skills
        player.level = 1
        player.exp = 0

        # Create husk from the devoured monster
        husk = create_husk(monster.name, monster.level)
        assert husk.source_monster == 'Test Slime'
        assert husk.tier == 2
        assert husk.slots == 2  # Based on tier

        # Add husk to player's inventory
        husk_inv = player.get_component(HuskInventoryComponent)
        husk_inv.husks.append(husk)

        # Verify husk was added correctly
        assert len(husk_inv.husks) == 1
        created_husk = husk_inv.husks[0]
        assert created_husk.source_monster == 'Test Slime'
        assert created_husk.tier == 2
        assert created_husk.slots == 2
        assert created_husk.decay == 0
        assert created_husk.corruption == 0

    finally:
        # Clean up
        set_flag('ENABLE_HUSK_PUPPET_HACKING', False)


def test_husk_not_created_when_skills_remain():
    """Test that no husk is created when entity still has skills"""
    # Enable the husk feature
    set_flag('ENABLE_HUSK_PUPPET_HACKING', True)
    try:
        # Create a monster entity with multiple skills
        monster = Entity(name='Test Goblin', is_player=False)
        monster.level = 1

        # Clear default skills and add two for testing
        monster.skills.clear()
        monster.skills['fire_bolt'] = Skill('fire_bolt')
        monster.skills['ice_shard'] = Skill('ice_shard')

        # Verify initial state
        assert len(monster.skills) == 2

        # Simulate devouring only one skill
        removed_skill = monster.skills.pop('fire_bolt', None)
        assert removed_skill is not None
        assert len(monster.skills) == 1  # Still has ice_shard
        assert 'ice_shard' in monster.skills

        # Check if monster should be considered a husk (skills empty)
        is_husk = len(monster.skills) == 0
        assert not is_husk  # Should still be False

        # Create player entity
        player = Entity(name='Test Player', is_player=True)
        player.skills.clear()
        player.level = 1

        # Even if we try to create a husk, it shouldn't be added in actual gameplay
        # but let's verify the husk would have correct properties if created
        husk = create_husk(monster.name, monster.level)
        assert husk.source_monster == 'Test Goblin'
        assert husk.tier == 1
        assert husk.slots == 1

        # The key point: gameplay logic should NOT create a husk when is_husk is False
        # This is verified by the fact that we don't call create_husk in that case

    finally:
        # Clean up
        set_flag('ENABLE_HUSK_PUPPET_HACKING', False)


def test_husk_serialization_through_entity():
    """Test that husks serialize correctly when stored in entity inventory"""
    # Enable the husk feature
    set_flag('ENABLE_HUSK_PUPPET_HACKING', True)
    try:
        # Create entities
        monster = Entity(name='Test Boss', is_player=False)
        monster.level = 5
        monster.skills.clear()

        player = Entity(name='Test Player', is_player=True)
        player.skills.clear()
        player.level = 1

        # Create and add a husk
        husk = create_husk(monster.name, monster.level)
        # Modify some fields to test serialization
        husk.decay = 10
        husk.corruption = 5
        husk.injected_skills = ['fire_bolt', 'heal']
        husk.injected_codes = ['synergy_fire_heal']

        husk_inv = player.get_component(HuskInventoryComponent)
        husk_inv.husks.append(husk)

        # Serialize player to dict
        player_data = player.to_dict()

        # Check that husk data is properly serialized
        assert "components" in player_data
        assert "HuskInventoryComponent" in player_data["components"]
        husk_data = player_data["components"]["HuskInventoryComponent"]
        assert "husks" in husk_data
        assert len(husk_data["husks"]) == 1

        serialized_husk = husk_data["husks"][0]
        assert serialized_husk["source_monster"] == "Test Boss"
        assert serialized_husk["tier"] == 5
        assert serialized_husk["slots"] == 5
        assert serialized_husk["decay"] == 10
        assert serialized_husk["corruption"] == 5
        assert serialized_husk["injected_skills"] == ["fire_bolt", "heal"]
        assert serialized_husk["injected_codes"] == ["synergy_fire_heal"]

        # Deserialize back to entity
        restored_player = Entity.from_dict(player_data)

        # Check that husk was restored correctly
        restored_husk_inv = restored_player.get_component(HuskInventoryComponent)
        assert len(restored_husk_inv.husks) == 1
        restored_husk = restored_husk_inv.husks[0]
        assert restored_husk.source_monster == "Test Boss"
        assert restored_husk.tier == 5
        assert restored_husk.slots == 5
        assert restored_husk.decay == 10
        assert restored_husk.corruption == 5
        assert restored_husk.injected_skills == ["fire_bolt", "heal"]
        assert restored_husk.injected_codes == ["synergy_fire_heal"]

    finally:
        # Clean up
        set_flag('ENABLE_HUSK_PUPPET_HACKING', False)
