"""
Unit test for World A Presentation & Synthesis Integration (Steps 37-48)
"""

from __future__ import annotations

import unittest

from game import Engine
from input_actions import ActionSynthesisMenu
from renderer import NullRenderer


class TestWorldAPresentationIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(renderer=NullRenderer())
        self.engine.game_state_data.current_world = "skill_eater"

    def test_synthesis_execution_not_enough_skills(self):
        self.engine.game_state_data.world_a_data["skills"] = ["com_magic_001"]
        res = self.engine.execute_synthesis()
        self.assertTrue(res)
        self.assertEqual(len(self.engine.game_state_data.world_a_data["skills"]), 1)

    def test_synthesis_execution_success(self):
        self.engine.game_state_data.world_a_data["skills"] = [
            "com_magic_001",
            "com_labor_002",
        ]
        res = self.engine.execute_synthesis("com_magic_001", "com_labor_002")
        self.assertTrue(res)
        skills = self.engine.game_state_data.world_a_data["skills"]
        self.assertIn("rar_infrared_vision", skills)
        self.assertNotIn("com_magic_001", skills)
        self.assertNotIn("com_labor_002", skills)

    def test_action_synthesis_menu_triggers_engine_synthesis(self):
        self.engine.game_state_data.world_a_data["skills"] = [
            "com_magic_001",
            "com_labor_002",
        ]
        action = ActionSynthesisMenu()
        res = action.execute(self.engine, None)
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
