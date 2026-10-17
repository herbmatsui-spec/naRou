"""Unit tests for constants.py - Game constants."""

from __future__ import annotations

import pytest

import constants


class TestGodConstants:
    """Tests for god-related constants."""

    def test_god_ids_exist(self):
        """God-related constants are defined."""
        # Check for god-related constants that actually exist
        assert hasattr(constants, "DEFAULT_GOD_ID")
        assert hasattr(constants, "STARTING_GOD_ID")
        assert constants.DEFAULT_GOD_ID == "lulwy"
        assert constants.STARTING_GOD_ID == "lulwy"


class TestItemQualityConstants:
    """Tests for item quality constants."""

    def test_quality_constants_exist(self):
        """Quality constants are defined."""
        assert hasattr(constants, "QUALITY_BAD")
        assert hasattr(constants, "QUALITY_NORMAL")
        assert hasattr(constants, "QUALITY_GOOD")
        assert hasattr(constants, "QUALITY_GOD")
        assert hasattr(constants, "QUALITY_MIRACLE")

    def test_quality_values(self):
        """Quality constants have expected string values."""
        assert constants.QUALITY_BAD == "bad"
        assert constants.QUALITY_NORMAL == "normal"
        assert constants.QUALITY_GOOD == "good"
        assert constants.QUALITY_GOD == "god"
        assert constants.QUALITY_MIRACLE == "miracle"

    def test_all_qualities_tuple(self):
        """ALL_QUALITIES tuple contains all qualities."""
        assert hasattr(constants, "ALL_QUALITIES")
        assert isinstance(constants.ALL_QUALITIES, tuple)
        assert "bad" in constants.ALL_QUALITIES
        assert "normal" in constants.ALL_QUALITIES
        assert "good" in constants.ALL_QUALITIES
        assert "miracle" in constants.ALL_QUALITIES
        assert "god" in constants.ALL_QUALITIES


class TestItemCategoryConstants:
    """Tests for item category constants."""

    def test_categories_exist(self):
        """Item category constants are defined."""
        assert hasattr(constants, "CAT_WEAPON")
        assert hasattr(constants, "CAT_SHIELD")
        assert hasattr(constants, "CAT_HELM")
        assert hasattr(constants, "CAT_ARMOR")
        assert hasattr(constants, "CAT_RING")
        assert hasattr(constants, "CAT_POTION")
        assert hasattr(constants, "CAT_SCROLL")
        assert hasattr(constants, "CAT_FOOD")
        assert hasattr(constants, "CAT_SPELLBOOK")
        assert hasattr(constants, "CAT_TOOL")
        assert hasattr(constants, "CAT_ROD")
        assert hasattr(constants, "CAT_ORE")
        assert hasattr(constants, "CAT_GOLD")

    def test_category_values(self):
        """Category constants have expected values."""
        assert constants.CAT_WEAPON == "weapon"
        assert constants.CAT_SHIELD == "shield"
        assert constants.CAT_HELM == "helm"
        assert constants.CAT_ARMOR == "armor"
        assert constants.CAT_RING == "ring"
        assert constants.CAT_POTION == "potion"
        assert constants.CAT_SCROLL == "scroll"
        assert constants.CAT_FOOD == "food"
        assert constants.CAT_SPELLBOOK == "spellbook"
        assert constants.CAT_TOOL == "tool"
        assert constants.CAT_ROD == "rod"
        assert constants.CAT_ORE == "ore"
        assert constants.CAT_GOLD == "gold"


class TestFoodTagConstants:
    """Tests for food tag constants."""

    def test_food_tags_exist(self):
        """Food tag constants are defined."""
        assert hasattr(constants, "FOOD_TAG_MEAT")
        assert hasattr(constants, "FOOD_TAG_FISH")
        assert hasattr(constants, "FOOD_TAG_VEGETABLE")
        assert hasattr(constants, "FOOD_TAG_FRUIT")
        assert hasattr(constants, "FOOD_TAG_SWEET")
        assert hasattr(constants, "FOOD_TAG_GRAIN")
        assert hasattr(constants, "FOOD_TAG_HERB")
        assert hasattr(constants, "FOOD_TAG_SEAFOOD")
        assert hasattr(constants, "FOOD_TAG_SEASONING")
        assert hasattr(constants, "FOOD_TAG_MEDICINE")

    def test_food_tag_values(self):
        """Food tag constants have expected values."""
        assert constants.FOOD_TAG_MEAT == "meat"
        assert constants.FOOD_TAG_FISH == "fish"
        assert constants.FOOD_TAG_VEGETABLE == "vegetable"
        assert constants.FOOD_TAG_FRUIT == "fruit"
        assert constants.FOOD_TAG_SWEET == "sweet"
        assert constants.FOOD_TAG_GRAIN == "grain"
        assert constants.FOOD_TAG_HERB == "herb"
        assert constants.FOOD_TAG_SEAFOOD == "seafood"
        assert constants.FOOD_TAG_SEASONING == "seasoning"
        assert constants.FOOD_TAG_MEDICINE == "medicine"


class TestPersonalityConstants:
    """Tests for personality constants."""

    def test_personality_constants_exist(self):
        """Personality constants are defined."""
        assert hasattr(constants, "PERSONALITY_BRAVE")
        assert hasattr(constants, "PERSONALITY_CALM")
        assert hasattr(constants, "PERSONALITY_COWARDLY")
        assert hasattr(constants, "PERSONALITY_AGGRESSIVE")
        assert hasattr(constants, "PERSONALITY_GLUTTONOUS")

    def test_personality_values(self):
        """Personality constants have expected values."""
        assert constants.PERSONALITY_BRAVE == "brave"
        assert constants.PERSONALITY_CALM == "calm"
        assert constants.PERSONALITY_COWARDLY == "cowardly"
        assert constants.PERSONALITY_AGGRESSIVE == "aggressive"
        assert constants.PERSONALITY_GLUTTONOUS == "gluttonous"

    def test_personality_labels(self):
        """Personality labels dictionary exists."""
        assert hasattr(constants, "PERSONALITY_LABELS")
        assert isinstance(constants.PERSONALITY_LABELS, dict)
        assert "brave" in constants.PERSONALITY_LABELS
        assert "cowardly" in constants.PERSONALITY_LABELS


class TestAIConstants:
    """Tests for AI-related constants."""

    def test_ai_role_constants(self):
        """AI role constants are defined."""
        assert hasattr(constants, "AI_ROLE_BRUTE")
        assert hasattr(constants, "AI_ROLE_FLANKER")
        assert hasattr(constants, "AI_ROLE_KITER")
        assert hasattr(constants, "AI_ROLE_SUPPORT")

    def test_ai_role_values(self):
        """AI role constants have expected values."""
        assert constants.AI_ROLE_BRUTE == "brute"
        assert constants.AI_ROLE_FLANKER == "flanker"
        assert constants.AI_ROLE_KITER == "kiter"
        assert constants.AI_ROLE_SUPPORT == "support"

    def test_kiter_preferred_range(self):
        """Kiter preferred range is defined."""
        assert hasattr(constants, "KITER_PREFERRED_RANGE")
        assert isinstance(constants.KITER_PREFERRED_RANGE, int)
        assert constants.KITER_PREFERRED_RANGE > 0


class TestColorConstants:
    """Tests for color constants."""

    def test_color_constants_exist(self):
        """Color constants are defined."""
        assert hasattr(constants, "COLOR_WHITE")
        assert hasattr(constants, "COLOR_RED")
        assert hasattr(constants, "COLOR_GREEN")
        assert hasattr(constants, "COLOR_BLUE")
        assert hasattr(constants, "COLOR_YELLOW")
        assert hasattr(constants, "COLOR_GOLD_YELLOW")
        assert hasattr(constants, "COLOR_ORANGE")
        assert hasattr(constants, "COLOR_CYAN")
        assert hasattr(constants, "COLOR_MAGENTA")
        assert hasattr(constants, "COLOR_PINK")
        assert hasattr(constants, "COLOR_GRAY")
        assert hasattr(constants, "COLOR_CYAN")

    def test_color_values(self):
        """Color constants are RGB tuples."""
        for attr in dir(constants):
            if attr.startswith("COLOR_"):
                value = getattr(constants, attr)
                assert isinstance(value, tuple)
                assert len(value) == 3
                for channel in value:
                    assert isinstance(channel, int)
                    assert 0 <= channel <= 255


class TestReincarnationConstants:
    """Tests for reincarnation-related constants."""

    def test_reincarnation_constants_exist(self):
        """Reincarnation constants are defined."""
        assert hasattr(constants, "REINCARNATION_XP_PENALTY_BASE")
        assert hasattr(constants, "REINCARNATION_XP_PENALTY_STEP")
        assert hasattr(constants, "MAX_REINCARNATIONS")

    def test_reincarnation_values(self):
        """Reincarnation constants have expected types."""
        assert isinstance(constants.REINCARNATION_XP_PENALTY_BASE, (int, float))
        assert isinstance(constants.REINCARNATION_XP_PENALTY_STEP, (int, float))
        assert 0 <= constants.REINCARNATION_XP_PENALTY_BASE <= 1
        assert constants.REINCARNATION_XP_PENALTY_STEP > 0
        assert constants.MAX_REINCARNATIONS == 10


class TestNaturalRegenConstants:
    """Tests for natural regeneration constants."""

    def test_natural_regen_constants_exist(self):
        """Natural regen constants are defined."""
        assert hasattr(constants, "NATURAL_REGEN_HUNGER_THRESHOLD")
        assert hasattr(constants, "NATURAL_REGEN_INTERVAL")

    def test_natural_regen_values(self):
        """Natural regen constants have expected types."""
        assert isinstance(constants.NATURAL_REGEN_HUNGER_THRESHOLD, int)
        assert isinstance(constants.NATURAL_REGEN_INTERVAL, int)
        assert constants.NATURAL_REGEN_HUNGER_THRESHOLD >= 0
        assert constants.NATURAL_REGEN_INTERVAL > 0


class TestCombatConstants:
    """Tests for combat-related constants."""

    def test_combat_constants_exist(self):
        """Combat constants are defined."""
        assert hasattr(constants, "CRIT_DAMAGE_MULTIPLIER")
        assert hasattr(constants, "CRIT_RATE_BASE")
        assert hasattr(constants, "CRIT_RATE_DEX_MULTIPLIER")
        assert hasattr(constants, "HIT_RATE_BASE")
        assert hasattr(constants, "HIT_RATE_DEX_MULTIPLIER")

    def test_combat_values(self):
        """Combat constants have expected types."""
        assert isinstance(constants.CRIT_DAMAGE_MULTIPLIER, (int, float))
        assert isinstance(constants.CRIT_RATE_BASE, (int, float))
        assert isinstance(constants.HIT_RATE_BASE, (int, float))


class TestGameplayConstants:
    """Tests for general gameplay constants."""

    def test_max_level(self):
        """Max level constant exists."""
        assert hasattr(constants, "MAX_LEVEL")
        assert isinstance(constants.MAX_LEVEL, int)
        assert constants.MAX_LEVEL > 0

    def test_experience_formula(self):
        """Experience formula constants exist."""
        assert hasattr(constants, "EXP_BASE")
        assert hasattr(constants, "EXP_GROWTH_FACTOR")
        assert isinstance(constants.EXP_BASE, int)
        assert isinstance(constants.EXP_GROWTH_FACTOR, (int, float))

    def test_difficulty_constants(self):
        """Difficulty constants exist."""
        assert hasattr(constants, "DIFFICULTY_EASY")
        assert hasattr(constants, "DIFFICULTY_NORMAL")
        assert hasattr(constants, "DIFFICULTY_HARD")
        assert hasattr(constants, "DIFFICULTY_NIGHTMARE")
        assert hasattr(constants, "DIFFICULTY_MODIFIERS")

    def test_hunger_constants(self):
        """Hunger-related constants exist."""
        assert hasattr(constants, "HUNGER_MAX")
        assert hasattr(constants, "HUNGER_PER_TURN")
        assert hasattr(constants, "FULL_THRESHOLD")
        assert hasattr(constants, "STARVING_THRESHOLD")

    def test_equip_slots(self):
        """Equipment slots tuple exists."""
        assert hasattr(constants, "EQUIP_SLOTS")
        assert isinstance(constants.EQUIP_SLOTS, tuple)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
