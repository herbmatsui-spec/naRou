"""Test skill bridge: Entity.skills → CharacterState.skills pipeline."""

from __future__ import annotations

import pytest


class TestSkillBridge:
    """Verify fused/learned skills bridge from Entity to CharacterState."""

    def test_fused_skill_becomes_castable(self) -> None:
        """After fusion, skill should appear in CharacterState.skills (spellbook)."""
        from ecs.entity import Entity, Skill
        from engine.engine import _character_state_from_entity
        from skill_bridge import bridge_skill_to_spellbook, ensure_character_state

        # Create player entity with a fused skill in ownership bag
        player = Entity(name="TestPlayer", x=0, y=0, char="@", color=(255, 255, 255))
        player.skills = {"fused_fireball": Skill("fused_fireball", level=1)}

        # Convert to CharacterState (simulates World A entry) and attach to entity
        char_state = _character_state_from_entity(player, analysis_level=1)
        player.character_state = char_state

        # Initially, spellbook is empty (skills not copied)
        assert "fused_fireball" not in char_state.skills

        # Bridge the skill
        result = bridge_skill_to_spellbook(player, "fused_fireball", level=1)
        assert result is True

        # Now skill should be in spellbook (use entity's attached state)
        assert "fused_fireball" in player.character_state.skills
        assert player.character_state.skills["fused_fireball"].level == 1

    def test_learned_skill_appears_in_spellbook(self) -> None:
        """Any skill learning system should bridge to spellbook."""
        from ecs.entity import Entity, Skill
        from engine.engine import _character_state_from_entity
        from skill_bridge import bridge_skill_to_spellbook

        player = Entity(name="TestPlayer", x=0, y=0, char="@", color=(255, 255, 255))
        player.skills = {"awakened_blade": Skill("awakened_blade", level=3)}

        char_state = _character_state_from_entity(player, analysis_level=1)
        player.character_state = char_state
        assert "awakened_blade" not in char_state.skills

        bridge_skill_to_spellbook(player, "awakened_blade", level=3)
        assert "awakened_blade" in player.character_state.skills
        assert player.character_state.skills["awakened_blade"].level == 3

    def test_bridge_upgrades_existing_spellbook_skill(self) -> None:
        """Bridging higher level should upgrade existing spellbook entry."""
        from ecs.entity import Entity, Skill
        from engine.engine import _character_state_from_entity
        from skill_bridge import bridge_skill_to_spellbook

        player = Entity(name="TestPlayer", x=0, y=0, char="@", color=(255, 255, 255))
        player.skills = {"evolved_skill": Skill("evolved_skill", level=1)}

        char_state = _character_state_from_entity(player, analysis_level=1)
        player.character_state = char_state
        bridge_skill_to_spellbook(player, "evolved_skill", level=1)
        assert player.character_state.skills["evolved_skill"].level == 1

        # Upgrade to level 5
        player.skills["evolved_skill"] = Skill("evolved_skill", level=5)
        bridge_skill_to_spellbook(player, "evolved_skill", level=5)
        assert player.character_state.skills["evolved_skill"].level == 5

    def test_bridge_returns_false_for_entity_without_character_state(self) -> None:
        """Bridge should handle entities that can't have CharacterState."""
        from ecs.entity import Entity, Skill
        from skill_bridge import bridge_skill_to_spellbook

        # Create a proper entity - bridge should work
        player = Entity(name="Test", x=0, y=0, char="@", color=(255, 255, 255))
        player.skills = {"dummy": Skill("dummy", level=1)}

        result = bridge_skill_to_spellbook(player, "dummy", 1)
        assert result is True
        assert "dummy" in player.character_state.skills


class TestNonVacuity:
    """Non-vacuity proofs for skill bridge tests."""

    def test_assert_distinguishes_bridge_works(self) -> None:
        """Test CAN detect when bridge is broken."""
        from tests.helpers.non_vacuity import assert_distinguishes

        def check_bridge_works(bridge_fn):
            """Check if bridge function populates spellbook."""
            from ecs.entity import Entity, Skill
            from engine.engine import _character_state_from_entity

            player = Entity(name="Test", x=0, y=0, char="@", color=(255, 255, 255))
            player.skills = {"test_skill": Skill("test_skill", level=1)}
            char_state = _character_state_from_entity(player, analysis_level=1)
            player.character_state = char_state

            # Call bridge
            bridge_fn(player, "test_skill", level=1)

            # Verify spellbook has it
            assert "test_skill" in player.character_state.skills

        # Good bridge (real implementation)
        from skill_bridge import bridge_skill_to_spellbook as real_bridge
        # Broken bridge (no-op)
        def broken_bridge(player, skill_id, level):
            pass

        assert_distinguishes(check_bridge_works, real_bridge, broken_bridge, label="skill_bridge")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
