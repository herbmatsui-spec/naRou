"""Tests for skill_eater_system module."""

from __future__ import annotations

from skill_eater_system import SkillTier, SkillType


def test_skill_tier_enum():
    assert SkillTier.COMMON.value == "Common"
    assert SkillTier.RARE.value == "Rare"
    assert SkillTier.UNIQUE.value == "Unique"
    assert SkillTier.CONCEPT.value == "Concept"
    assert SkillTier.EATER.value == "Eater"


def test_skill_type_enum():
    assert SkillType.ACTIVE.value == "Active"
    assert SkillType.PASSIVE.value == "Passive"
    assert SkillType.CRAFT.value == "Craft"
    assert SkillType.META.value == "Meta"