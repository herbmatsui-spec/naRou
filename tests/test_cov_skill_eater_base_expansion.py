"""Coverage tests for skill_eater_base_expansion (SlumBaseExpansionManager)."""

from __future__ import annotations

import pytest

from skill_eater_base_expansion import SlumBaseExpansionManager


@pytest.fixture
def mgr() -> SlumBaseExpansionManager:
    return SlumBaseExpansionManager()


class TestInitialState:
    def test_tier1_defaults(self, mgr: SlumBaseExpansionManager) -> None:
        assert mgr.base_tier == 1
        assert mgr.max_tier == 3
        assert mgr.invested_junk == 0
        assert mgr.invested_skill_points == 0
        assert mgr.unlocked_facilities == ["basic_workshop"]
        assert mgr.unlocked_merchants == ["junk_trader"]
        assert mgr.built_monuments == []
        assert mgr.passive_buffs["exploration_efficiency"] == 1.0

    def test_status_ui_tier1(self, mgr: SlumBaseExpansionManager) -> None:
        ui = mgr.get_base_status_ui()
        assert ui["tier"] == 1
        assert ui["base_name"].startswith("泥水のスラム")
        assert ui["total_junk"] == 0
        assert ui["monuments"] == []


class TestInvestResources:
    def test_invalid_negative_amount(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.invest_resources(junk_amount=-1)
        assert res["success"] is False
        assert mgr.invested_junk == 0

    def test_invalid_negative_skill_points(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.invest_resources(skill_point_amount=-5)
        assert res["success"] is False
        assert mgr.invested_skill_points == 0

    def test_zero_investment_counts_tier_up_event_none(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.invest_resources(0, 0)
        assert res["success"] is True
        assert res["tier_up_event"] is None
        assert res["current_tier"] == 1

    def test_accumulates(self, mgr: SlumBaseExpansionManager) -> None:
        mgr.invest_resources(100, 1)
        res = mgr.invest_resources(50, 2)
        assert res["invested_junk"] == 150
        assert res["invested_skill_points"] == 3


class TestTierProgression:
    def test_tier2_unlock(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.invest_resources(500, 5)
        assert res["current_tier"] == 2
        event = res["tier_up_event"]
        assert event is not None
        assert event["old_tier"] == 1
        assert event["new_tier"] == 2
        assert "cyber_lab" in mgr.unlocked_facilities
        assert "underground_arena" in mgr.unlocked_facilities
        assert "black_market_hacker" in mgr.unlocked_merchants
        assert mgr.passive_buffs["exploration_efficiency"] == 1.25
        assert mgr.passive_buffs["trap_damage_bonus"] == pytest.approx(0.20)

    def test_tier2_requires_both_junk_and_skills(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.invest_resources(500, 4)
        assert res["current_tier"] == 1
        assert res["tier_up_event"] is None

    def test_direct_jump_to_tier3(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.invest_resources(2000, 20)
        assert res["current_tier"] == 3
        assert res["tier_up_event"]["old_tier"] == 1
        assert res["tier_up_event"]["new_tier"] == 3
        assert "resistance_command_center" in mgr.unlocked_facilities
        assert "meta_reactor" in mgr.unlocked_facilities
        assert "legendary_broker" in mgr.unlocked_merchants
        assert mgr.passive_buffs["exploration_efficiency"] == 1.50
        assert mgr.passive_buffs["crafting_success_rate"] == pytest.approx(1.00)
        assert mgr.passive_buffs["trap_damage_bonus"] == pytest.approx(0.50)

    def test_stepwise_tier1_to_2_to_3(self, mgr: SlumBaseExpansionManager) -> None:
        r1 = mgr.invest_resources(500, 5)
        assert r1["tier_up_event"]["new_tier"] == 2
        r2 = mgr.invest_resources(1500, 15)
        assert r2["tier_up_event"]["new_tier"] == 3

    def test_no_double_tier_up(self, mgr: SlumBaseExpansionManager) -> None:
        mgr.invest_resources(2000, 20)
        res = mgr.invest_resources(100, 1)
        assert res["current_tier"] == 3
        assert res["tier_up_event"] is None

    def test_status_ui_tier3(self, mgr: SlumBaseExpansionManager) -> None:
        mgr.invest_resources(2000, 20)
        ui = mgr.get_base_status_ui()
        assert ui["tier"] == 3
        assert ui["base_name"].startswith("解放戦線")
        assert "basic_workshop" in ui["facilities"]


class TestMonuments:
    def test_unlock_monument(self, mgr: SlumBaseExpansionManager) -> None:
        res = mgr.unlock_special_monument("StarDevourer")
        assert res["success"] is True
        assert res["monument"] == "Monument of StarDevourer"
        assert "Monument of StarDevourer" in mgr.built_monuments
        assert mgr.passive_buffs["trap_damage_bonus"] == pytest.approx(0.10)

    def test_duplicate_monument_rejected(self, mgr: SlumBaseExpansionManager) -> None:
        first = mgr.unlock_special_monument("StarDevourer")
        assert first["success"] is True
        second = mgr.unlock_special_monument("StarDevourer")
        assert second["success"] is False
        assert "already exists" in second["message"]
        assert len(mgr.built_monuments) == 1

    def test_different_monuments_stack(self, mgr: SlumBaseExpansionManager) -> None:
        mgr.unlock_special_monument("A")
        mgr.unlock_special_monument("B")
        assert mgr.passive_buffs["trap_damage_bonus"] == pytest.approx(0.20)

    def test_monument_stacks_on_tier3(self, mgr: SlumBaseExpansionManager) -> None:
        mgr.invest_resources(2000, 20)
        mgr.unlock_special_monument("C")
        assert mgr.passive_buffs["trap_damage_bonus"] == pytest.approx(0.60)
