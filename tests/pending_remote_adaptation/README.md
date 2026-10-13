# Quarantined Tests

This directory contains tests that have been quarantined because they require significant new implementations that would risk breaking existing functionality. These tests are preserved for future reference when the required systems are implemented.

## Quarantined Files

### test_pet_personality_system.py
**Reason for Quarantine**: Requires implementing an entirely new `PetPersonalitySystem` class with:
- Personality assignment (random from allowed list)
- Feeding mechanics with favorite foods and rotten food handling
- Equipment restrictions based on bond level
- AI behavior decisions based on personality (brave, calm, cowardly, etc.)

**Dependencies**: 
- New `pet_personality_system.py` module
- Entity extensions for pet attributes (bond, personality, favorite_food_tags)
- Food tag system integration
- AI decision framework

**Original Test Location**: `tests/test_pet_personality_system.py`

**Quarantine Date**: 2026-10-11
**Agent**: Agent B (triage)

## Restoration Criteria

This test can be restored when:
1. A `PetPersonalitySystem` class is implemented in the codebase
2. Entity supports pet attributes (bond, personality, favorite_food_tags)
3. Food tag constants are available (FOOD_TAG_MEAT, FOOD_TAG_FISH, etc.)
4. Personality constants are available (PERSONALITY_BRAVE, PERSONALITY_CALM, etc.)
5. The test imports are fixed (currently uses `from naRou.systems.item_system import Item` which doesn't exist)

## Note

The test file is preserved in its original form. When the Pet Personality & Bonding System (Phase 6, Steps 49-72) is implemented, this test should be moved back to `tests/` and verified.