"""Tests for Proposal 8 (Synergy) and Proposal 9 (Skill Tree UI)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_synergy_system import SkillSynergyManager
from ui_skill_tree import SkillTreeRenderer
from skill_tree_system import get_skill_tree_registry, get_skill_tree_manager


class FakePlayer:
    def __init__(self):
        self.recent_skills = []
        self.skill_tree_progress = {}
        self.total_skill_points_earned = 0


# ---------------- Proposal 8: Synergy ----------------
def test_synergy_load():
    mgr = SkillSynergyManager()
    assert len(mgr.all()) >= 3
    assert "fire_tornado" in mgr.all()
    print("PASS: synergy definitions loaded")


def test_synergy_trigger():
    mgr = SkillSynergyManager()
    p = FakePlayer()
    mgr.register_skill_use(p, "fireball", 1)
    mgr.register_skill_use(p, "wind_blade", 2)
    # window=3, current turn=3 -> both within window
    triggered = mgr.evaluate(p, 3)
    ids = {s.id for s in triggered}
    assert "fire_tornado" in ids
    print("PASS: fire_tornado combo triggers")


def test_synergy_window_expiry():
    mgr = SkillSynergyManager()
    p = FakePlayer()
    mgr.register_skill_use(p, "fireball", 1)
    mgr.register_skill_use(p, "wind_blade", 2)
    # turn=10 -> window of 3 expired
    assert mgr.evaluate(p, 10) == []
    print("PASS: synergy expires after window")


# ---------------- Proposal 9: UI ----------------
def test_ui_renderer():
    reg = get_skill_tree_registry()
    mgr = get_skill_tree_manager()
    if not reg.all():
        print("SKIP: no skill trees loaded")
        return
    renderer = SkillTreeRenderer(reg, mgr)
    p = FakePlayer()
    tree_id = next(iter(reg.all().keys()))
    nodes = renderer.build_nodes(p)[tree_id]
    assert len(nodes) > 0
    text = renderer.render_text(p, tree_id)
    assert "┌─" in text and "└" in text
    print("PASS: skill tree UI renders")


if __name__ == "__main__":
    test_synergy_load()
    test_synergy_trigger()
    test_synergy_window_expiry()
    test_ui_renderer()
    print("\nALL SYNERGY + UI TESTS PASSED")
