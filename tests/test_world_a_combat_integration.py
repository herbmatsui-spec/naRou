"""
Unit test for World A Combat & Devour Integration (Steps 25-36)
"""
from __future__ import annotations

import unittest
from entity import Entity
from game import Engine
from renderer import NullRenderer


class TestWorldACombatIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(renderer=NullRenderer())
        self.engine.game_state_data.current_world = "skill_eater"

    def test_execute_scan_nearest_target(self):
        enemy = Entity(
            x=self.engine.player.x + 1,
            y=self.engine.player.y,
            char="o",
            color=(200, 50, 50),
            name="オーク戦士",
            is_player=False,
            is_pet=False,
        )
        enemy.hp = 30
        enemy.max_hp = 30
        enemy.faction = "monster"
        self.engine.entity_manager.add_entity(enemy)
        res = self.engine.execute_scan()
        self.assertTrue(res)

    def test_execute_devour_success_and_husk(self):
        enemy = Entity(
            x=self.engine.player.x + 1,
            y=self.engine.player.y,
            char="g",
            color=(50, 200, 50),
            name="ゴブリン",
            is_player=False,
            is_pet=False,
        )
        enemy.hp = 5
        enemy.max_hp = 30
        enemy.faction = "monster"
        self.engine.entity_manager.add_entity(enemy)
        res = self.engine.execute_devour()
        self.assertTrue(res)
        self.assertTrue(len(self.engine.message_log.messages) > 0)


if __name__ == "__main__":
    unittest.main()
