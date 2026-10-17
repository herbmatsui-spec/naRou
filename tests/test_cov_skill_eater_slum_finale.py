"""Coverage tests for skill_eater_slum_finale (SlumFinaleManager)."""

from __future__ import annotations

from skill_eater_slum_finale import SlumFinaleManager


class TestSlumFinaleManager:
    def setup_method(self) -> None:
        self.mgr = SlumFinaleManager(base_power=500)

    def test_initial_state(self) -> None:
        assert self.mgr.slum_defensive_power == 500
        assert self.mgr.total_raid_waves == 3
        assert self.mgr.current_raid_wave == 1
        assert self.mgr.is_base_destroyed is False
        assert self.mgr.fallen_sectors == []

    def test_defense_repelled_perfectly(self) -> None:
        result = self.mgr.simulate_concurrent_defense(300)
        assert result["result"] == "WAVE_REPELLED_PERFECTLY"
        assert result["fallen_sectors"] == []
        assert result["is_base_destroyed"] is False
        assert self.mgr.current_raid_wave == 2

    def test_defense_sector_breached(self) -> None:
        result = self.mgr.simulate_concurrent_defense(800)
        assert result["result"] == "SECTOR_BREACHED"
        assert any("Sector-1" in s for s in result["fallen_sectors"])
        assert result["is_base_destroyed"] is False

    def test_defense_base_destroyed_after_3_sectors(self) -> None:
        for _ in range(3):
            self.mgr.simulate_concurrent_defense(800)
        assert self.mgr.is_base_destroyed is True
        result = self.mgr.simulate_concurrent_defense(100)
        assert result["status"] == "BASE_ALREADY_DESTROYED"

    def test_trigger_final_stand_boost(self) -> None:
        result = self.mgr.trigger_final_stand_boost(300)
        assert result["success"] is True
        assert result["boosted_defensive_power"] == 800
        assert self.mgr.slum_defensive_power == 800

    def test_trigger_final_stand_boost_default(self) -> None:
        result = self.mgr.trigger_final_stand_boost()
        assert result["boosted_defensive_power"] == 800  # 500 + 300
