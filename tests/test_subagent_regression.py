"""
CI/CD Automated Regression Test Suite for Autonomous Subagent AI
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

NAROU_DIR = Path(__file__).resolve().parent.parent
for p in [str(NAROU_DIR), str(NAROU_DIR.parent)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ai_autonomous_subagent import AutonomousSubagentAI
from game import Engine
from ecs.entity import Entity
from item_system import Item


class TestAutonomousSubagentRegression(unittest.TestCase):

    def setUp(self):
        self.engine = Engine()
        self.ai = AutonomousSubagentAI(self.engine, strategy_name="hybrid")

    def test_01_fsm_initialization(self):
        """Verify all 8 HFSM states are registered."""
        self.assertGreaterEqual(len(self.ai.fsm.states), 8)
        self.assertEqual(self.ai.fsm.current_state_name, "explore")

    def test_02_danger_heatmap_evaluation(self):
        """Verify potential field calculation runs without errors."""
        step = self.ai.safety_grid.find_best_safe_step()
        self.assertTrue(step is None or len(step) == 2)

    def test_03_item_autonomous_healing(self):
        """Verify low HP triggers potion use."""
        self.engine.player.hp = 5
        act = self.ai.item_decider.decide_item_action()
        self.assertIsNotNone(act)
        self.assertEqual(act[0], "use_item")

    def test_04_floor_exploration_ratio(self):
        """Verify exploration ratio calculation."""
        ratio = self.ai.floor_progression.compute_exploration_ratio()
        self.assertTrue(0.0 <= ratio <= 1.0)


if __name__ == "__main__":
    unittest.main()
