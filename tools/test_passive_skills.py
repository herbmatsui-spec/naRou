"""Tests for Proposal 6: Passive Skills System."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_tree_system import (
    PassiveSkill,
    get_passive_skill_manager,
    get_passive_skill_registry,
)


class FakePlayer:
    """Minimal stand-in exposing the attributes PassiveSkillManager needs."""

    def __init__(self):
        self.learned_passive_skills = []
        self.skill_points = 1000
        self.total_skill_points_earned = 0


def test_registry_loads():
    reg = get_passive_skill_registry()
    assert len(reg.all()) >= 4, "expected at least 4 passive skills"
    iron = reg.get("iron_body")
    assert isinstance(iron, PassiveSkill)
    assert iron.cost == 20
    assert iron.prerequisites == ["basic_constitution"]
    print("PASS: registry loads passive skills")


def test_learn_and_aggregate():
    mgr = get_passive_skill_manager()
    p = FakePlayer()
    # Learn iron_body directly (prereq not met -> should fail)
    assert not mgr.can_learn(p, "iron_body")
    # Satisfy prerequisite
    p.learned_passive_skills.append("basic_constitution")
    assert mgr.can_learn(p, "iron_body")
    assert mgr.learn(p, "iron_body")
    # Already learned -> cannot learn again
    assert not mgr.can_learn(p, "iron_body")
    assert "iron_body" in p.learned_passive_skills
    # Aggregate bonuses
    bonuses = mgr.aggregate_bonuses(p)
    assert bonuses["max_hp_bonus"] == 50
    assert bonuses["physical_resistance"] == 10
    assert bonuses["knockback_resistance"] == 0.5
    print("PASS: learn + aggregate works")


def test_multiple_skills_sum():
    mgr = get_passive_skill_manager()
    p = FakePlayer()
    p.learned_passive_skills.extend(
        ["basic_constitution", "magic_basic", "fortune_favor", "survivor_instinct"]
    )
    assert mgr.learn(p, "mana_efficiency")
    assert mgr.learn(p, "lucky_find")
    bonuses = mgr.aggregate_bonuses(p)
    # item_find_rate + rare_drop_rate are separate keys
    assert bonuses["item_find_rate"] == 0.3
    assert bonuses["rare_drop_rate"] == 0.15
    assert bonuses["mp_cost_reduction"] == 0.2
    assert bonuses["mp_regen_bonus"] == 2
    print("PASS: multiple skills aggregate independently")


if __name__ == "__main__":
    test_registry_loads()
    test_learn_and_aggregate()
    test_multiple_skills_sum()
    print("\nALL PASSIVE SKILL TESTS PASSED")
