"""Coverage tests for skill_eater_bank_dungeon (BankDungeonManager)."""

from __future__ import annotations

import pytest

from skill_eater_bank_dungeon import BankDungeonManager


@pytest.fixture
def mgr() -> BankDungeonManager:
    return BankDungeonManager()


class TestDefaults:
    def test_four_floors_defined(self, mgr: BankDungeonManager) -> None:
        assert [f["floor"] for f in mgr.floors] == [1, 2, 3, 4]
        assert all(f["cleared"] is False for f in mgr.floors)
        assert "投資信託部門" in mgr.floors[0]["name"]
        assert "世界コア制御室" in mgr.floors[3]["name"]

    def test_initial_state(self, mgr: BankDungeonManager) -> None:
        assert mgr.current_floor_index == 0
        assert mgr.hazard_level == 0
        assert mgr.active_debuffs == []
        assert mgr.is_shortcut_blocked is False


class TestAdvanceExploration:
    def test_first_step_hazard_15_no_debuffs(self, mgr: BankDungeonManager) -> None:
        res = mgr.advance_exploration_step()
        assert res["hazard_level"] == 15
        assert res["active_debuffs"] == []
        assert res["map_event"] == "Path stable."
        assert res["is_shortcut_blocked"] is False
        assert res["current_floor"] == mgr.floors[0]["name"]

    def test_hazard_30_unlocks_mp_debuff(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 15
        res = mgr.advance_exploration_step()  # 30
        assert res["hazard_level"] == 30
        assert res["active_debuffs"] == ["Concept Leaking: MP Cost +20%"]

    def test_hazard_60_unlocks_two_debuffs(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 45
        res = mgr.advance_exploration_step()  # 60
        assert res["hazard_level"] == 60
        assert len(res["active_debuffs"]) == 2
        assert "Gravity Distortion: Turn Time -30%" in res["active_debuffs"]

    def test_hazard_90_unlocks_all_debuffs(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 75
        res = mgr.advance_exploration_step()  # 90
        assert res["hazard_level"] == 90
        assert len(res["active_debuffs"]) == 3
        assert "Total Reality Breakdown: Continuous HP Erosion" in res["active_debuffs"]

    def test_hazard_capped_at_100(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 95
        res = mgr.advance_exploration_step()
        assert res["hazard_level"] == 100

    def test_shortcut_blocked_once_at_hazard_50(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 35
        first = mgr.advance_exploration_step()  # 50 → blocked
        assert first["map_event"].startswith("ALERT:")
        assert first["is_shortcut_blocked"] is True
        mgr.hazard_level = 0
        second = mgr.advance_exploration_step()  # 15, already blocked stays blocked
        assert second["is_shortcut_blocked"] is True
        assert second["map_event"] == "Path stable."

    def test_below_50_no_block(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 30
        res = mgr.advance_exploration_step()  # 45
        assert res["is_shortcut_blocked"] is False


class TestClearFloor:
    def test_clear_first_floor_advances(self, mgr: BankDungeonManager) -> None:
        mgr.advance_exploration_step()  # hazard 15
        res = mgr.clear_current_floor()
        assert res["success"] is True
        assert res["cleared_floor"] == mgr.floors[0]["name"]
        assert res["next_floor"] == mgr.floors[1]["name"]
        assert res["has_next_floor"] is True
        assert res["hazard_level_after_purge"] == 0
        assert mgr.floors[0]["cleared"] is True
        assert mgr.current_floor_index == 1
        assert mgr.is_shortcut_blocked is False

    def test_purge_reduces_hazard_by_50(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 70
        res = mgr.clear_current_floor()
        assert res["hazard_level_after_purge"] == 20

    def test_purge_floors_at_zero(self, mgr: BankDungeonManager) -> None:
        mgr.hazard_level = 30
        res = mgr.clear_current_floor()
        assert res["hazard_level_after_purge"] == 0

    def test_final_floor_has_no_next(self, mgr: BankDungeonManager) -> None:
        mgr.current_floor_index = 3
        res = mgr.clear_current_floor()
        assert res["has_next_floor"] is False
        assert res["next_floor"] == "None (Final Boss Floor)"
        assert mgr.current_floor_index == 3
        assert mgr.floors[3]["cleared"] is True

    def test_rewards_constant(self, mgr: BankDungeonManager) -> None:
        res = mgr.clear_current_floor()
        assert res["rewards"] == "High-Grade Concept Shard & Floor Clearance Token"

    def test_full_run_through_all_floors(self, mgr: BankDungeonManager) -> None:
        for i in range(4):
            res = mgr.clear_current_floor()
            assert res["success"] is True
        assert all(f["cleared"] for f in mgr.floors)
        assert mgr.current_floor_index == 3
