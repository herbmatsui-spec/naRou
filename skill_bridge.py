"""Skill Bridge: Connects Entity.skills (ownership) to CharacterState.skills (spellbook).

This module provides the pipeline for making owned skills usable in World A combat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecs.entity import Entity


def bridge_skill_to_spellbook(entity: "Entity", skill_id: str, level: int = 1) -> bool:
    """Bridge a skill from Entity.skills (ownership) to CharacterState.skills (spellbook).

    This is called after any skill acquisition (fusion, awakening, evolution, etc.)
    to make the skill actually usable in World A / Skill Eater combat.

    Args:
        entity: The Entity that owns the skill
        skill_id: The skill ID to bridge
        level: The skill level to set in the spellbook

    Returns:
        True if bridging succeeded
    """
    # Ensure entity has a CharacterState
    char_state = ensure_character_state(entity)

    # Import CharacterSkillSlot from skill_eater_system
    from skill_eater_system import CharacterSkillSlot

    # Add or upgrade the skill in the spellbook
    if skill_id in char_state.skills:
        # Upgrade to higher level if applicable
        if char_state.skills[skill_id].level < level:
            char_state.skills[skill_id].level = level
    else:
        char_state.skills[skill_id] = CharacterSkillSlot(skill_id=skill_id, level=level)

    # Recalculate memory usage after adding skill
    char_state.calculate_memory_usage()
    return True


def ensure_character_state(entity: "Entity", analysis_level: int = 1):
    """Ensure entity has a CharacterState, creating one if needed."""
    char_state = getattr(entity, "character_state", None)
    if char_state is None:
        from engine.engine import _character_state_from_entity

        char_state = _character_state_from_entity(entity, analysis_level)
        entity.character_state = char_state
    return char_state


def bridge_all_owned_skills(entity: "Entity", analysis_level: int = 1) -> int:
    """Bridge all skills from Entity.skills to CharacterState.skills.

    Useful for initial sync when entering World A.

    Returns:
        Number of skills bridged
    """
    char_state = ensure_character_state(entity, analysis_level)
    owned_skills = getattr(entity, "skills", {})
    count = 0
    for skill_id, skill_obj in owned_skills.items():
        level = getattr(skill_obj, "level", 1)
        bridge_skill_to_spellbook(entity, skill_id, level)
        count += 1
    return count
