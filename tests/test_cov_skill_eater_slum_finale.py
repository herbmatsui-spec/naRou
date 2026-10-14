"""Coverage tests for skill_eater_slum_finale (SlumFinaleManager)."""

from __future__ import annotations

import pytest

from skill_eater_slum_finale import SlumFinaleManager


@pytest.fixture
def mgr() -> SlumFinaleManager:
    return SlumFinaleManager()


class TestSlumFinaleDefaults:
    def test_initial_state(self) -> None:
        m = SlumFinaleManager()
        assert m.slum_defensive_power == 500
        assert m.total_raid_waves == 3
        assert m.current_raid_wave == 1
        assert m.is_base_destroyed is False
        assert m.fallen_sectors == []

    def test_custom_base_power(self) -> None:
        m = SlumFinaleManager(base_power=1200)
        assert m.slum_defensive_power == 1200


class TestSimulateConcurrentDefense:
    def test_repel_when_margin_positive(self, mgr: SlumFinaleManager) -> None:
        res = mgr.simulate_concurrent_defense(400)
        assert res["wave"] == 1
        assert res["result"] == "WAVE_REPELLED_PERFECTLY"
        assert res["fallen_sectors"] == []
        assert res["is_base_destroyed"] is False
        assert "Wave 1" in res["message"]

    def test_repel_when_margin_exactly_zero(self, mgr: SlumFinaleManager) -> None:
        res = mgr.simulate_concurrent_defense(500)
        assert res["result"] == "WAVE_REPELLED_PERFECTLY"
        assert res["fallen_sectors"] == []

    def test_sector_breach_records_fallen_sector(self, mgr: SlumFinaleManager) -> None:
        res = mgr.simulate_concurrent_defense(900)
        assert res["result"] == "SECTOR_BREACHED"
        assert res["fallen_sectors"] == ["Sector-1 (Slum Market)"]
        assert mgr.fallen_sectors == ["Sector-1 (Slum Market)"]
        assert res["is_base_destroyed"] is False
        assert "Sector-1 (Slum Market)" in res["message"]
        assert mgr.current_raid_wave == 2

    def test_breach_wave_number_increments_per_call(self, mgr: SlumFinaleManager) -> None:
        first = mgr.simulate_concurrent_defense(900)
        second = mgr.simulate_concurrent_defense(900)
        assert first["wave"] == 1
        assert second["wave"] == 2
        assert second["fallen_sectors"] == [
            "Sector-1 (Slum Market)",
            "Sector-2 (Slum Market)",
        ]

    def test_annihilation_on_third_loss(self, mgr: SlumFinaleManager) -> None:
        mgr.simulate_concurrent_defense(1000)
        mgr.simulate_concurrent_defense(1000)
        res = mgr.simulate_concurrent_defense(1000)
        assert res["result"] == "SLUM_ANNIHILATED"
        assert len(mgr.fallen_sectors) == 3
        assert res["wave"] == 3
        assert res["is_base_destroyed"] is True
        assert mgr.is_base_destroyed is True

    def test_after_annihilation_rejects_further_simulations(
        self, mgr: SlumFinaleManager
    ) -> None:
        for _ in range(3):
            mgr.simulate_concurrent_defense(1000)
        res = mgr.simulate_concurrent_defense(1)
        assert res == {"status": "BASE_ALREADY_DESTROYED"}

    def test_fallen_sector_label_uses_current_wave(self, mgr: SlumFinaleManager) -> None:
        mgr.simulate_concurrent_defense(1000)
        res = mgr.simulate_concurrent_defense(1000)
        assert "Sector-2" in mgr.fallen_sectors[1]
        assert "Sector-2" in res["message"]


class TestFinalStandBoost:
    def test_boost_adds_buff_to_defensive_power(self, mgr: SlumFinaleManager) -> None:
        res = mgr.trigger_final_stand_boost(300)
        assert res["success"] is True
        assert res["boosted_defensive_power"] == 800
        assert mgr.slum_defensive_power == 800

    def test_default_buff_is_300(self, mgr: SlumFinaleManager) -> None:
        res = mgr.trigger_final_stand_boost()
        assert res["boosted_defensive_power"] == 800

    def test_message_mentions_final_stand(self, mgr: SlumFinaleManager) -> None:
        res = mgr.trigger_final_stand_boost()
        assert "FINAL STAND" in res["message"]

    def test_boost_applies_to_subsequent_defense(self, mgr: SlumFinaleManager) -> None:
        mgr.trigger_final_stand_boost(600)
        res = mgr.simulate_concurrent_defense(1000)
        assert res["result"] == "WAVE_REPELLED_PERFECTLY"

    def test_boost_after_annihilation_still_applies(self, mgr: SlumFinaleManager) -> None:
        for _ in range(3):
            mgr.simulate_concurrent_defense(1000)
        assert mgr.is_base_destroyed is True
        res = mgr.trigger_final_stand_boost(100)
        assert res["success"] is True
        assert res["boosted_defensive_power"] == 600
