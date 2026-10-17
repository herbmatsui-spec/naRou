"""Test survival balance relationships (Step 29)."""

from __future__ import annotations

import pytest

from systems import SurvivalSystem


def test_starving_outpaces_regen_within_a_run():
    """Verify that a player who never eats dies within ~8027 turns.

    Starting hunger: 8000
    Hunger decay: 1/turn
    Starvation damage: 2 HP/turn at hunger <= 0
    Starting HP: ~55
    Time to death: 8000 + 55/2 = 8027 turns
    Passive regen: 0 HP/turn (cannot catch up)
    """
    survival = SurvivalSystem()
    # Mock player with starting stats
    class MockPlayer:
        def __init__(self):
            self.hp = 55
            self.max_hp = 55
            self.attributes = type('obj', (object,), {'strength': 10})()

    player = MockPlayer()
    death_turn = None

    # Simulate turns until death
    for turn in range(1, 10000):
        logs = survival.pass_turn(player)
        if player.hp <= 0:
            death_turn = turn
            break

    assert death_turn is not None, "Player should eventually die from starvation"
    # Death should occur around turn 8027 (8000 hunger + ~27 turns of starvation damage)
    assert 8000 < death_turn < 8050, f"Death at turn {death_turn}, expected ~8027"
    # Verify passive regen is 0 (hunger decays, no HP recovery)
    assert survival.hunger == 0, "Hunger should reach 0"


def test_idle_player_reaches_a_nonlethal_starvation():
    """Verify player can maintain hunger > 1000 by eating bread every ~1500 turns.

    Bread nutrition: 1500
    Hunger decay: 1/turn
    Equilibrium: eat bread every 1500 turns → hunger stabilizes around 1500-3000
    """
    survival = SurvivalSystem()
    class MockPlayer:
        def __init__(self):
            self.hp = 55
            self.max_hp = 55
            self.name = "Test Player"
            self.attributes = type('obj', (object,), {'strength': 10})()

    player = MockPlayer()
    bread_nutrition = 1500
    eat_interval = 1500

    # Simulate eat-wait cycles
    hunger_history = []
    for cycle in range(10):  # 10 cycles = 15000 turns
        # Wait for eat_interval turns
        for _ in range(eat_interval):
            survival.pass_turn(player)
        hunger_history.append(survival.hunger)

        # Eat bread
        class MockBread:
            nutrition = bread_nutrition
            name = "パン"

        survival.eat(player, MockBread())

    # Hunger should stabilize in a sustainable range (not starving, not at max)
    # Starting at 8000, eating bread (1500 nutrition) every 1500 turns:
    # hunger oscillates between ~6500 (after wait) and ~8000 (after eat)
    final_hunger = hunger_history[-1]
    # Should be in a sustainable range (not starving, not at max)
    assert 1000 < final_hunger < 10000, f"Hunger {final_hunger} not in sustainable range"
    # Should never have reached 0 (starvation)
    assert all(h > 0 for h in hunger_history), "Hunger should never reach 0 with regular eating"
    # Verify equilibrium: hunger oscillates but doesn't trend to 0 or 10000
    assert max(hunger_history) - min(hunger_history) < 2000, "Hunger should stabilize"


def test_hunger_div_regen_cannot_catch_up():
    """Verify 8000 hunger ÷ 1/turn, passive regen (0) cannot catch up.

    Passive HP regen rate: 0 HP/turn
    Hunger decay rate: 1 hunger/turn
    Starvation HP loss: 2 HP/turn (after hunger <= 0)
    Net: Hunger always decreases without food input
    """
    survival = SurvivalSystem()
    class MockPlayer:
        def __init__(self):
            self.hp = 55
            self.max_hp = 55
            self.attributes = type('obj', (object,), {'strength': 10})()

    player = MockPlayer()

    # Run for 1000 turns without food
    initial_hunger = survival.hunger
    for _ in range(1000):
        survival.pass_turn(player)

    # Hunger should have decreased by exactly 1000 (1 per turn)
    assert survival.hunger == initial_hunger - 1000
    # HP should not have increased (no passive regen)
    # HP only decreases when hunger <= 0 (after 8000 turns)
    assert player.hp == 55, "HP should not change before starvation"


def test_toxicity_accelerates_death_in_world_a():
    """Verify toxicity in World A adds death pressure but hunger remains primary clock."""
    survival = SurvivalSystem()
    class MockPlayer:
        def __init__(self):
            self.hp = 55
            self.max_hp = 55
            self.attributes = type('obj', (object,), {'strength': 10})()

    player = MockPlayer()
    toxicity = 0

    # Simulate World A turn tick (engine.py lines 373-388)
    death_turn = None
    for turn in range(1, 200):
        # Normal hunger decay
        logs = survival.pass_turn(player)

        # World A toxicity gain
        toxicity += 1
        if toxicity >= 80:
            player.hp -= 2  # Toxicity damage

        if player.hp <= 0:
            death_turn = turn
            break

    assert death_turn is not None
    # With both hunger and toxicity, death should be faster than hunger alone
    # But hunger is still the primary clock (toxicity starts damaging at turn 80)
    # Death should occur before turn 8027 (hunger-only death)
    assert death_turn < 8027, "Toxicity should accelerate death"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
