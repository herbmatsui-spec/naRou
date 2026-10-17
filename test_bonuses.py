#!/usr/bin/env python3
"""Script to test different player attribute bonuses for stability."""

import sys

sys.path.insert(0, '.')

from unittest.mock import patch

import yaml
from naRou.engine.engine import Engine

from packages.character.package import _initialize_player_and_pet as original_init
from packages.core.kernel.kernel import Kernel
from tests.balance_simulator import BalanceSimulator


def create_engine_with_bonuses(str_bonus=0, dex_bonus=0, end_bonus=0):
    """Create an engine with modified player attribute bonuses."""
    # We'll monkey-patch the _initialize_player_and_pet function
    def patched_init(kernel, engine):
        original_init(kernel, engine)
        player = engine.player
        player.attributes.strength += str_bonus
        player.attributes.dexterity += dex_bonus
        player.attributes.endurance += end_bonus
        player.recalculate_stats()

    # We need to patch the function in the kernel's system registry?
    # Instead, let's directly create an engine and then modify the player after creation.
    engine = Engine(headless=True)  # headless to avoid rendering issues
    # Apply bonuses
    player = engine.player
    player.attributes.strength += str_bonus
    player.attributes.dexterity += dex_bonus
    player.attributes.endurance += end_bonus
    player.recalculate_stats()
    return engine

def test_win_rate(str_bonus, dex_bonus, end_bonus, trials=20):
    sim = BalanceSimulator()
    # We need to make the simulator use our custom engine.
    # The simulator uses acquire_world() which creates a new Engine each time.
    # We'll monkey-patch acquire_world to return our engine with bonuses.
    from tests.balance_simulator import _WORLD, acquire_world
    original_acquire = acquire_world

    def patched_acquire_world():
        engine, arena = original_acquire()
        # Apply bonuses to the player
        player = engine.player
        player.attributes.strength += str_bonus
        player.attributes.dexterity += dex_bonus
        player.attributes.endurance += end_bonus
        player.recalculate_stats()
        return engine, arena

    # Temporarily replace
    import tests.balance_simulator as bs
    bs.acquire_world = patched_acquire_world
    # Also need to reset _WORLD so that it picks up the new engine
    bs._WORLD.clear()

    try:
        res = sim.simulate_battle(player_level=1, monster_type='slime', trials=trials)
        return res
    finally:
        # Restore
        bs.acquire_world = original_acquire
        bs._WORLD.clear()

if __name__ == '__main__':
    # Test a few combinations
    combos = [
        (0, 0, 0),   # baseline
        (4, 4, 4),
        (8, 8, 8),
        (10, 10, 10),
        (4, 8, 4),
        (8, 4, 8),
        (2, 10, 2),
        (0, 12, 0),
        (0, 0, 12),
        (12, 0, 0),
    ]
    for str_b, dex_b, end_b in combos:
        res = test_win_rate(str_b, dex_b, end_b, trials=20)
        print(f"S{str_b:+2d} D{dex_b:+2d} E{end_b:+2d}: win={res['win_rate']:.3f} one-shot={res['one_shot_rate']:.3f} stall={res['stalled_rate']:.3f} dmg_dealt={res['avg_dmg_dealt']:.1f} dmg_taken={res['avg_dmg_taken']:.1f}")
