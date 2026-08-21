"""
Master End-to-End Test Suite for World A (Skill Eater) Complete Integration (Step 71)
Tests all 6 chapters & 72 steps: Initialization -> Scan -> Devour -> Synthesis -> Base/Gimmicks -> Epilogue
"""
from __future__ import annotations

import unittest
from entity import Entity
from game import Engine
from renderer import NullRenderer


class TestWorldAMasterE2E(unittest.TestCase):
    def test_full_world_a_lifecycle(self):
        # 1. Engine & Package Initialization (Steps 1-12)
        engine = Engine(renderer=NullRenderer())
        self.assertTrue(engine.kernel.has_system("skill_eater_combat_system"))
        self.assertTrue(engine.kernel.has_system("skill_eater_synthesis_system"))
        self.assertEqual(engine.game_state_data.current_world, "main")

        # 2. World Switch to A (Steps 61-62)
        engine.switch_world("skill_eater")
        self.assertEqual(engine.game_state_data.current_world, "skill_eater")

        # 3. Spawn Enemy and Perform Deep Analysis (Steps 13-24, 38-39)
        enemy = Entity(
            x=engine.player.x + 1,
            y=engine.player.y,
            char="B",
            color=(255, 50, 50),
            name="バベルの監査官",
            is_player=False,
            is_pet=False,
        )
        enemy.hp = 10
        enemy.max_hp = 50
        enemy.faction = "monster"
        engine.entity_manager.add_entity(enemy)

        scan_res = engine.execute_scan()
        self.assertTrue(scan_res)

        # 4. Devour Enemy Skill (Steps 25-36, 40-42)
        devour_res = engine.execute_devour()
        self.assertTrue(devour_res)

        # 5. Field Gimmicks & Pet Dispatch (Steps 49-60)
        engine.execute_pet_dispatch("スラム街の物資調達", duration_turns=1, reward_gold=500)
        engine.advance_world()
        self.assertGreaterEqual(engine.game_state_data.world_a_data["toxicity"], 1)
        self.assertEqual(len(engine.game_state_data.world_a_data["pet_dispatches"]), 0)

        # 6. Chimera Skill Synthesis (Steps 43-47)
        engine.game_state_data.world_a_data["skills"] = [
            "com_magic_001",
            "com_labor_002",
        ]
        synth_res = engine.execute_synthesis("com_magic_001", "com_labor_002")
        self.assertTrue(synth_res)
        self.assertIn("rar_infrared_vision", engine.game_state_data.world_a_data["skills"])

        # 7. Base Upgrade & Environmental Puzzle (Steps 54-59)
        engine.execute_base_upgrade("black_market_stall")
        self.assertEqual(
            engine.game_state_data.world_a_data["facilities"]["black_market_stall"],
            2,
        )
        puzzle_res = engine.execute_solve_puzzle("ice_barrier", "Fire")
        self.assertTrue(puzzle_res)

        # 8. Epilogue & Dimensional Warp with Legacy Artifact (Steps 69-70)
        epilogue_res = engine.execute_epilogue_world_transition()
        self.assertTrue(epilogue_res)
        self.assertEqual(engine.game_state_data.current_world, "main")
        self.assertIn(
            "concept_eater_mark",
            engine.game_state_data.world_a_data["meta_artifacts"],
        )


if __name__ == "__main__":
    unittest.main()
