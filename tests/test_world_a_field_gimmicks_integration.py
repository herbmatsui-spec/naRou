"""
Unit test for World A Field Gimmicks & Base Expansion (Steps 49-60)
"""
from __future__ import annotations

import unittest
from game import Engine
from renderer import NullRenderer


class TestWorldAFieldGimmicksIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(renderer=NullRenderer())
        self.engine.game_state_data.current_world = "skill_eater"

    def test_toxicity_accumulation_on_advance_world(self):
        self.engine.game_state_data.world_a_data["toxicity"] = 10
        self.engine.advance_world()
        self.assertGreaterEqual(
            self.engine.game_state_data.world_a_data["toxicity"], 11
        )

    def test_pet_dispatch_and_return(self):
        self.engine.execute_pet_dispatch("スラム街の廃品回収", duration_turns=2, reward_gold=300)
        self.assertEqual(len(self.engine.game_state_data.world_a_data["pet_dispatches"]), 1)
        
        # Advance 2 turns
        self.engine.advance_world()
        self.engine.advance_world()
        self.assertEqual(len(self.engine.game_state_data.world_a_data["pet_dispatches"]), 0)

    def test_base_upgrade(self):
        self.engine.execute_base_upgrade("alchemy_lab")
        facs = self.engine.game_state_data.world_a_data["facilities"]
        self.assertEqual(facs["alchemy_lab"], 2)

    def test_solve_puzzle(self):
        res_ok = self.engine.execute_solve_puzzle("ice_barrier", "Fire")
        self.assertTrue(res_ok)
        res_fail = self.engine.execute_solve_puzzle("ice_barrier", "Water")
        self.assertFalse(res_fail)


if __name__ == "__main__":
    unittest.main()
