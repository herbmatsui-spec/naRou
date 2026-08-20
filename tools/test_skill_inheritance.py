"""Tests for Proposal 7: Skill Inheritance / Reincarnation Bonuses."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_tree_system import SkillInheritanceManager


class FakeComp:
    def __init__(self):
        self.inherited_skills = []
        self.inherited_stat_bonus = 0


class FakePlayer:
    def __init__(self):
        self._comp = FakeComp()

    def get_component(self, _):
        return self._comp


def test_rules_loaded():
    mgr = SkillInheritanceManager()
    assert len(mgr.all_rules()) >= 2
    assert "bloodline_skills" in mgr.all_rules()
    print("PASS: inheritance rules loaded")


def test_availability_by_reincarnation():
    mgr = SkillInheritanceManager()
    # reincarnation 0 -> none available (both require >=1)
    assert mgr.available_rules(0) == []
    avail = mgr.available_rules(2)
    ids = {r.id for r in avail}
    assert "bloodline_skills" in ids and "mastery_inheritance" in ids
    print("PASS: availability gated by requirement")


def test_inheritance_points():
    mgr = SkillInheritanceManager()
    pts = mgr.compute_inheritance_points(level=100, mastered_jobs=2, awakened_skills=1)
    # 10 + (100//10)*2=20 + 2*5=10 + 1*10=10 = 50
    assert pts == 50
    print("PASS: inheritance points computed")


def test_apply_rule():
    mgr = SkillInheritanceManager()
    p = FakePlayer()
    assert mgr.apply_rule(p, "mastery_inheritance")
    assert "swordsmanship" in p._comp.inherited_skills
    assert p._comp.inherited_stat_bonus == 10
    print("PASS: rule applied to player")


if __name__ == "__main__":
    test_rules_loaded()
    test_availability_by_reincarnation()
    test_inheritance_points()
    test_apply_rule()
    print("\nALL SKILL INHERITANCE TESTS PASSED")
