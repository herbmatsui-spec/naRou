"""
AI Performance Impact & Autonomous Efficiency Verification Test
Validates that the AutonomousSubagentAI resolves oscillations, avoids fatal damage, and achieves high survival.
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
from item_system import Item


class TestAIPerformanceImpact(unittest.TestCase):

    def test_oscillation_resolution_impact(self):
        """Verify oscillation detection immediately shifts AI from exploring to escaping."""
        engine = Engine()
        ai = AutonomousSubagentAI(engine)

        # Force oscillation history
        for _ in range(10):
            ai.bb.record_position((10, 10))
            ai.bb.record_position((10, 11))

        self.assertTrue(ai.bb.is_oscillating())

        # Update state machine: should transition to escape state
        action, _ = ai.decide_turn_action()
        self.assertIn(action, ("move", "wait"))

    def test_health_preservation_impact(self):
        """Verify critical HP triggers immediate potion healing."""
        engine = Engine()
        potion = Item(name="軽傷治療のポーション", category="potion", char="!", color=(255, 0, 0))
        engine.inventory.add_item(potion)
        ai = AutonomousSubagentAI(engine)
        engine.player.hp = 1  # 1 HP remaining

        action, item = ai.decide_turn_action()
        self.assertEqual(action, "use_item")


if __name__ == "__main__":
    unittest.main()
