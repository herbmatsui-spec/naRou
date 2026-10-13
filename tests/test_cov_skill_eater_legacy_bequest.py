"""Coverage tests for skill_eater_legacy_bequest (LegacyBequestManager)."""

from __future__ import annotations

import pytest

from skill_eater_legacy_bequest import LegacyBequestManager


@pytest.fixture
def mgr() -> LegacyBequestManager:
    return LegacyBequestManager()


class TestDefaults:
    def test_initial_scores(self, mgr: LegacyBequestManager) -> None:
        assert mgr.bequest_scores == {"Combat": 0, "Recovery": 0, "Production": 0}
        assert mgr.donated_skills == []


class TestDonation:
    def test_excluded_skills_not_donated(self, mgr: LegacyBequestManager) -> None:
        inventory = [
            {"name": "Kept Skill", "tags": ["Combat"], "power": 100},
            {"name": "Leftover Fire", "tags": ["Fire"], "power": 10},
        ]
        res = mgr.donate_leftover_skills(inventory, ["Kept Skill"])
        assert res["donated_count"] == 1
        assert mgr.donated_skills[0]["name"] == "Leftover Fire"
        assert mgr.bequest_scores["Combat"] == 10

    def test_no_exclusions_donates_all(self, mgr: LegacyBequestManager) -> None:
        inventory = [{"name": "a", "tags": [], "power": 1}, {"name": "b", "tags": [], "power": 1}]
        res = mgr.donate_leftover_skills(inventory, [])
        assert res["donated_count"] == 2

    def test_combat_tags_scored(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills(
            [{"name": "s", "tags": ["Sword", "Destruction"], "power": 30}], []
        )
        assert res["bequest_scores"]["Combat"] == 30
        assert res["bequest_scores"]["Recovery"] == 0

    def test_recovery_tags_scored(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills(
            [{"name": "s", "tags": ["Heal", "Barrier", "Shield"]}, {"name": "t", "tags": ["Defense"], "power": 20}], []
        )
        assert res["bequest_scores"]["Recovery"] == 50 + 20

    def test_production_tags_scored(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills(
            [{"name": "s", "tags": ["Craft", "Analysis", "Cyber"]}, {"name": "t", "tags": ["Magic"], "power": 15}], []
        )
        assert res["bequest_scores"]["Production"] == 50 + 15

    def test_multi_category_scores_all(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills(
            [{"name": "s", "tags": ["Fire", "Heal", "Craft"], "power": 40}], []
        )
        scores = res["bequest_scores"]
        assert scores == {"Combat": 40, "Recovery": 40, "Production": 40}

    def test_default_power_50_when_missing(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills([{"name": "s", "tags": ["Combat"]}], [])
        assert res["bequest_scores"]["Combat"] == 50

    def test_unrelated_tags_score_nothing(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills([{"name": "s", "tags": ["Life", "Social"], "power": 99}], [])
        assert res["bequest_scores"] == {"Combat": 0, "Recovery": 0, "Production": 0}

    def test_dominant_type_reported(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills(
            [{"name": "s", "tags": ["Recovery"], "power": 80}], []
        )
        assert res["dominant_reconstruction_type"] == "Recovery"

    def test_empty_donation_defaults_to_combat(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills([], [])
        assert res["donated_count"] == 0
        assert res["dominant_reconstruction_type"] == "Combat"

    def test_message_contains_count(self, mgr: LegacyBequestManager) -> None:
        res = mgr.donate_leftover_skills([{"name": "s", "tags": []}], [])
        assert "Donated 1 skills" in res["message"]

    def test_scores_accumulate_across_calls(self, mgr: LegacyBequestManager) -> None:
        mgr.donate_leftover_skills([{"name": "a", "tags": ["Combat"], "power": 10}], [])
        res = mgr.donate_leftover_skills([{"name": "b", "tags": ["Combat"], "power": 15}], [])
        assert res["bequest_scores"]["Combat"] == 25
        assert len(mgr.donated_skills) == 2
