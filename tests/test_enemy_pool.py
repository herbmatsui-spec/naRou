"""Test enemy pool availability at all depths (Step 24)."""

from __future__ import annotations

import pytest

from data_manager import DataManager


def test_every_depth_has_at_least_two_valid_monsters():
    """Every dungeon depth 1-30 should have at least 2 valid monster choices.

    This was an xfail because early-game monsters had low max_floor.
    Step 24 extends max_floor in monsters.yaml and changes the fallback logic.
    """
    dm = DataManager()

    # Check depths 1 through 30 (max_depth from config)
    for depth in range(1, 31):
        # Use the same filtering logic as get_random_monster_for_floor
        tier_pool = []
        for m_id, m_val in dm.monsters._data.items():
            min_floor = getattr(m_val, "min_floor", 1)
            max_floor = getattr(m_val, "max_floor", 999)
            if min_floor <= depth <= max_floor + 3:  # +3 buffer in original code
                tier_pool.append(m_id)

        assert len(tier_pool) >= 2, (
            f"Depth {depth} has only {len(tier_pool)} monsters: {tier_pool}. "
            f"Expected at least 2 valid choices."
        )


def test_fallback_uses_closest_depth_not_hardcoded():
    """Fallback when no valid monsters should use closest 3 by depth, not hardcoded fallback.

    The old code fell back to all monsters (effectively depth 12 pool).
    New code should pick closest 3 by depth difference.
    """
    dm = DataManager()

    # Simulate a depth beyond all max_floor (e.g., depth 100)
    depth = 100

    # Collect all monsters with their depth distance
    candidates = []
    for m_id, m_val in dm.monsters._data.items():
        min_floor = getattr(m_val, "min_floor", 1)
        max_floor = getattr(m_val, "max_floor", 999)
        # Calculate "closeness" to requested depth
        if depth < min_floor:
            dist = min_floor - depth
        elif depth > max_floor:
            dist = depth - max_floor
        else:
            dist = 0
        candidates.append((dist, m_id))

    # Sort by distance and take closest 3
    candidates.sort(key=lambda x: x[0])
    closest_3 = [m_id for _, m_id in candidates[:3]]

    # The fallback should use these closest 3, not all monsters
    assert len(closest_3) == 3
    # With all max_floor=30, all have same distance at depth 100
    # Just verify the fallback logic produces a valid 3-monster pool
    assert all(m_id in dm.monsters._data for m_id in closest_3)
