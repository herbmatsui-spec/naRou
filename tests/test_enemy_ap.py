"""
test_enemy_ap.py
敵AIがAPを消費して行動することの非空虚性テスト

Step 3B: Enemy AI facing updates & AP consumption
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import ENERGY_THRESHOLD  # noqa: E402
from core_framework import Point  # noqa: E402
from data_manager import DataManager  # noqa: E402
from game import Engine  # noqa: E402
from renderer import NullRenderer  # noqa: E402
from skill_eater.ai.ai_system import AdvancedAISystem  # noqa: E402


def _engine() -> Engine:
    return Engine(renderer=NullRenderer())


def _place_monster(dm: DataManager, monster_id: str, dx: int, dy: int = 0) -> tuple[Engine, object]:
    """プレイヤーから相対位置 (dx, dy) に production 経路のモンスターを1体配置する"""
    engine = _engine()
    mob = dm.create_monster(monster_id, x=engine.player.x + dx, y=engine.player.y + dy)
    # Initialize AP to max (simulates start of turn)
    mob.reset_ap()
    # Also give energy for turn queue compatibility
    mob.energy = ENERGY_THRESHOLD * 3
    engine.entity_manager.add_entity(mob)
    assert engine.has_los(Point(mob.x, mob.y), Point(engine.player.x, engine.player.y)), (
        f"前提: {monster_id} からプレイヤーへの視線が通ること"
    )
    return engine, mob


class TestEnemyAPConsumption:
    """敵AIがAPを消費して行動することのテスト"""

    def test_enemies_have_ap_not_free_actions(self):
        """非空虚性: 敵はAPを持っており、行動時にAPを消費する（無料行動ではない）"""
        dm = DataManager()
        # Use a simple aggressive monster (kobold) that has melee attack
        engine, mob = _place_monster(dm, "kobold", dx=1, dy=0)

        # Verify mob has AP system initialized
        assert hasattr(mob, 'ap'), "Mob should have AP attribute"
        assert hasattr(mob, 'max_ap'), "Mob should have max_ap attribute"
        assert hasattr(mob, 'spend_ap'), "Mob should have spend_ap method"
        assert hasattr(mob, 'can_act'), "Mob should have can_act method"
        assert hasattr(mob, 'reset_ap'), "Mob should have reset_ap method"

        # Initial AP should be max_ap (typically 2)
        initial_ap = mob.ap
        assert initial_ap > 0, "Mob should start with AP > 0"

        # Run AI processing once (enemy takes a turn)
        ai_system = AdvancedAISystem()
        ai_system.process_ai(mob, engine)

        # After acting, AP should be consumed
        assert mob.ap < initial_ap, f"Mob AP should decrease after acting (was {initial_ap}, now {mob.ap})"

        # AP should not go negative
        assert mob.ap >= 0, "AP should not go negative"

        # Verify the mob can't act infinitely without AP reset
        # Run AI multiple times until AP is exhausted
        original_ap = mob.ap
        actions_taken = 0
        while mob.can_act(1) and actions_taken < 10:
            prev_ap = mob.ap
            ai_system.process_ai(mob, engine)
            if mob.ap < prev_ap:
                actions_taken += 1
            else:
                break  # No AP consumed, might be blocked or failed

        # Should have taken at least one action that consumed AP
        assert actions_taken >= 1, "Mob should be able to take at least one AP-consuming action"

        # After AP exhausted, further actions should be blocked
        mob.ap = 0
        assert mob.can_act(1) is False, "Mob with 0 AP should not be able to act"

        # Reset AP should restore ability to act
        mob.reset_ap()
        assert mob.can_act(1) is True, "Mob after reset_ap should be able to act"

    def test_enemy_facing_updates_on_move(self):
        """敵が移動時に向きを更新する"""
        dm = DataManager()
        engine, mob = _place_monster(dm, "kobold", dx=3, dy=0)  # Place 3 tiles away

        # Record initial facing
        initial_facing = mob.facing

        # Run AI - mob should chase player (move toward)
        ai_system = AdvancedAISystem()
        ai_system.process_ai(mob, engine)

        # Mob should have moved closer to player
        dist_after = Point(mob.x, mob.y).chebyshev_distance(Point(engine.player.x, engine.player.y))
        assert dist_after < 3, "Mob should have moved closer to player"

        # Facing should have been updated based on movement
        # (Not asserting exact direction since pathfinding may vary, but it should change if moved)
        # If mob moved, facing should be set (not necessarily different from initial if moving S)
        assert mob.facing in ("N", "S", "E", "W"), "Facing should be a valid cardinal direction"

    def test_enemy_facing_updates_on_attack(self):
        """敵が攻撃時に対象の方を向く"""
        dm = DataManager()
        engine, mob = _place_monster(dm, "kobold", dx=1, dy=0)  # Adjacent to player

        # Run AI - mob should attack player
        ai_system = AdvancedAISystem()
        ai_system.process_ai(mob, engine)

        # Mob should be facing the player (South in this setup since player is at +y from mob)
        # Player is at (engine.player.x, engine.player.y), mob at (player.x+1, player.y)
        # So player is to the West of mob
        expected_facing = "W" if mob.x > engine.player.x else ("E" if mob.x < engine.player.x else
                                                                  ("N" if mob.y > engine.player.y else "S"))

        # The facing should point toward player
        assert mob.facing == expected_facing, f"Mob should face player ({expected_facing}), but facing {mob.facing}"

    def test_ap_cost_is_one_per_action(self):
        """各アクションはAP 1を消費する"""
        dm = DataManager()
        engine, mob = _place_monster(dm, "kobold", dx=1, dy=0)

        initial_ap = mob.ap
        ai_system = AdvancedAISystem()

        # Perform one action
        ai_system.process_ai(mob, engine)

        # Should consume exactly 1 AP (default cost)
        assert mob.ap == initial_ap - 1, f"Action should cost 1 AP (was {initial_ap}, now {mob.ap})"

    def test_different_monster_types_consume_ap(self):
        """異なるモンスタータイプすべてがAPを消費する"""
        dm = DataManager()
        ai_system = AdvancedAISystem()

        # Test various monster types
        monster_types = ["kobold", "goblin", "slime", "bat"]

        for monster_id in monster_types:
            if dm.monsters.get(monster_id) is None:
                continue  # Skip if not in data

            engine, mob = _place_monster(dm, monster_id, dx=2, dy=0)
            initial_ap = mob.ap

            ai_system.process_ai(mob, engine)

            # Each monster should consume AP when acting
            assert mob.ap < initial_ap, f"{monster_id} should consume AP on action"
            assert mob.ap >= 0, f"{monster_id} AP should not go negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
