"""Coverage tests for skill_eater_resistance_system (ResistanceMarketManager)."""

from __future__ import annotations

import pytest

from skill_eater_resistance_system import (
    DONATION_VALUE_TABLE,
    ResistanceFactionState,
    ResistanceMarketManager,
)


@pytest.fixture
def mgr() -> ResistanceMarketManager:
    return ResistanceMarketManager()


class TestDataAndDefaults:
    def test_donation_table_known_entries(self) -> None:
        assert DONATION_VALUE_TABLE["SCRAP_BEAST_FANG"] == 25
        assert DONATION_VALUE_TABLE["SECRET_TUNNEL_MARKET"] == 150

    def test_faction_state_defaults(self) -> None:
        st = ResistanceFactionState()
        assert st.reputation_points == 0
        assert st.reputation_level == 0
        assert st.unlocked_facilities == []
        assert st.main_quest_unlocked is False

    def test_manager_defaults(self, mgr: ResistanceMarketManager) -> None:
        assert mgr.liaison_npc_name == "レジスタンス連絡員カレン"
        assert mgr.state.reputation_level == 0


class TestReputationLevelUp:
    def test_level1_at_50(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SAFE_PASSWORD_MIDAS_SLUM"])  # 100
        assert mgr.state.reputation_level == 1
        assert "FREE_MEDICAL_STATION" in mgr.state.unlocked_facilities

    def test_level2_at_150(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])  # 150
        assert mgr.state.reputation_level == 2
        assert "ADVANCED_SYNTHESIS_FORGE" in mgr.state.unlocked_facilities

    def test_level3_at_300_unlocks_main_quest(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])  # 150
        mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])  # 300
        assert mgr.state.reputation_level == 3
        assert mgr.state.main_quest_unlocked is True

    def test_unknown_items_get_default_10(self, mgr: ResistanceMarketManager) -> None:
        res = mgr.donate_items_to_resistance(["MYSTERY_ITEM_A", "MYSTERY_ITEM_B"])
        assert res["earned_reputation"] == 20
        assert res["level_up"] is False
        assert mgr.state.reputation_level == 0

    def test_empty_donation(self, mgr: ResistanceMarketManager) -> None:
        res = mgr.donate_items_to_resistance([])
        assert res["earned_reputation"] == 0
        assert res["level_up"] is False

    def test_no_double_level_up_event(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])  # 150 -> Lv2
        res = mgr.donate_items_to_resistance(["MYSTERY_ITEM"])  # +10, still Lv2
        assert res["level_up"] is False
        assert mgr.state.reputation_level == 2

    def test_facility_not_duplicated(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SAFE_PASSWORD_MIDAS_SLUM"])
        mgr.donate_items_to_resistance(["SAFE_PASSWORD_MIDAS_SLUM"])
        assert mgr.state.unlocked_facilities.count("FREE_MEDICAL_STATION") == 1


class TestFacilities:
    def test_medical_station_locked(self, mgr: ResistanceMarketManager) -> None:
        res = mgr.use_medical_station()
        assert res["success"] is False
        assert res["error"] == "FACILITY_LOCKED"

    def test_medical_station_unlocked(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SAFE_PASSWORD_MIDAS_SLUM"])
        res = mgr.use_medical_station()
        assert res["success"] is True
        assert res["detox_amount"] == 100
        assert res["hp_heal"] == 100

    def test_forge_locked(self, mgr: ResistanceMarketManager) -> None:
        res = mgr.access_advanced_forge()
        assert res["success"] is False
        assert res["error"] == "FACILITY_LOCKED"

    def test_forge_unlocked(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])
        res = mgr.access_advanced_forge()
        assert res["success"] is True
        assert res["can_craft_permanent_skills"] is True


class TestMainQuest:
    def test_not_ready_initially(self, mgr: ResistanceMarketManager) -> None:
        res = mgr.check_main_quest_progression()
        assert res == {"ready": False, "required_points": 300, "current": 0}

    def test_ready_after_level3(self, mgr: ResistanceMarketManager) -> None:
        for _ in range(2):
            mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])
        res = mgr.check_main_quest_progression()
        assert res["ready"] is True
        assert res["quest_id"] == "QUEST_SE_02_MIDAS_WAREHOUSE_RAID"


class TestAmbientPresentation:
    def test_suspicious_tone_low_rep(self, mgr: ResistanceMarketManager) -> None:
        fx = mgr.get_market_ambient_presentation()
        assert fx["dialogue_tone"] == "SUSPICIOUS_WATCHFUL"
        assert len(fx["ambient_sfx"]) == 3

    def test_solidarity_tone_high_rep(self, mgr: ResistanceMarketManager) -> None:
        mgr.donate_items_to_resistance(["SECRET_TUNNEL_MARKET"])
        fx = mgr.get_market_ambient_presentation()
        assert fx["dialogue_tone"] == "REBEL_SOLIDARITY"
