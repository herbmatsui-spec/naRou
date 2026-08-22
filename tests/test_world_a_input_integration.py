"""
Unit test for World A Input & Actions (Steps 13-24)
"""

from __future__ import annotations

import unittest

from game import Engine
from input_actions import ActionDevour, ActionScan, ActionSynthesisMenu
from input_handler import InputHandler
from renderer import NullRenderer


class TestWorldAInputIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(renderer=NullRenderer())
        InputHandler.register_default_actions()

    def test_scan_action_main_world(self):
        action = ActionScan()
        self.engine.game_state_data.current_world = "main"
        res = action.execute(self.engine, None)
        self.assertTrue(res)

    def test_scan_action_world_a(self):
        action = ActionScan()
        self.engine.game_state_data.current_world = "skill_eater"
        res = action.execute(self.engine, None)
        self.assertTrue(res)

    def test_devour_action_dispatch(self):
        action = ActionDevour()
        self.engine.game_state_data.current_world = "skill_eater"
        res = action.execute(self.engine, None)
        self.assertTrue(res)

    def test_synthesis_action_dispatch(self):
        action = ActionSynthesisMenu()
        self.engine.game_state_data.current_world = "skill_eater"
        res = action.execute(self.engine, None)
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
