"""
Unit test for World A (Skill Eater) Package Integration (Steps 1-12)
"""
from __future__ import annotations

import unittest
from packages.core.kernel.kernel import Kernel
from packages.core.package import CorePackage
from packages.world_a.package import WorldAPackage


class TestWorldAPackageIntegration(unittest.TestCase):
    def setUp(self):
        self.kernel = Kernel()
        self.kernel.load_package(CorePackage())
        self.kernel.load_package(WorldAPackage())

    def test_systems_registered(self):
        self.assertTrue(self.kernel.has_system("skill_eater_registry"))
        self.assertTrue(self.kernel.has_system("skill_eater_combat_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_synthesis_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_presentation_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_audio_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_economy_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_servant_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_meta_quest_system"))
        self.assertTrue(self.kernel.has_system("skill_eater_exploration_system"))

    def test_engine_loads_world_a_package(self):
        from game import Engine
        from renderer import NullRenderer
        engine = Engine(renderer=NullRenderer())
        self.assertTrue(engine.kernel.has_system("skill_eater_combat_system"))
        self.assertEqual(engine.game_state_data.current_world, "main")
        self.assertIsInstance(engine.game_state_data.world_a_data, dict)


if __name__ == "__main__":
    unittest.main()
