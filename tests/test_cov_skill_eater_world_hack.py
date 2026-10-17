"""Coverage tests for skill_eater_world_hack (WorldLawOverrideManager)."""

from __future__ import annotations

import pytest

from skill_eater_world_hack import WorldLawOverrideManager


@pytest.fixture
def mgr() -> WorldLawOverrideManager:
    return WorldLawOverrideManager()


@pytest.fixture
def rooted(mgr: WorldLawOverrideManager) -> WorldLawOverrideManager:
    assert mgr.grant_root_access(2)["success"] is True
    return mgr


class TestDefaults:
    def test_initial_state(self, mgr: WorldLawOverrideManager) -> None:
        assert mgr.root_access_granted is False
        assert mgr.laws == {
            "damage_limit": 9999,
            "elemental_inversion": False,
            "fatal_damage_survive": False,
            "crit_multiplier": 1.5,
        }
        assert mgr.system_alerts == []


class TestRootAccess:
    def test_denied_with_one_key(self, mgr: WorldLawOverrideManager) -> None:
        res = mgr.grant_root_access(1)
        assert res["success"] is False
        assert "Need at least 2 Concept Keys" in res["message"]
        assert mgr.root_access_granted is False

    def test_denied_with_zero_keys(self, mgr: WorldLawOverrideManager) -> None:
        res = mgr.grant_root_access(0)
        assert res["success"] is False
        assert mgr.root_access_granted is False

    def test_granted_with_two_keys(self, mgr: WorldLawOverrideManager) -> None:
        res = mgr.grant_root_access(2)
        assert res["success"] is True
        assert mgr.root_access_granted is True
        assert "ROOT ACCESS GRANTED" in res["message"]
        assert res["editable_laws"] == [
            "damage_limit",
            "elemental_inversion",
            "fatal_damage_survive",
            "crit_multiplier",
        ]

    def test_granted_with_many_keys(self, mgr: WorldLawOverrideManager) -> None:
        assert mgr.grant_root_access(99)["success"] is True


class TestDamageLimitOverride:
    def test_requires_root_access(self, mgr: WorldLawOverrideManager) -> None:
        res = mgr.override_damage_limit(100000)
        assert res["success"] is False
        assert res["message"] == "Root access required."
        assert mgr.laws["damage_limit"] == 9999

    def test_override_updates_law_and_alert(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        res = rooted.override_damage_limit(123456)
        assert res["success"] is True
        assert res["damage_limit"] == 123456
        assert rooted.laws["damage_limit"] == 123456
        assert len(rooted.system_alerts) == 1
        assert "SYSTEM OVERRIDE" in rooted.system_alerts[0]

    def test_default_new_limit(self, rooted: WorldLawOverrideManager) -> None:
        res = rooted.override_damage_limit()
        assert res["damage_limit"] == 999999
        assert rooted.laws["damage_limit"] == 999999


class TestElementalInversionOverride:
    def test_requires_root_access(self, mgr: WorldLawOverrideManager) -> None:
        res = mgr.override_elemental_inversion(True)
        assert res["success"] is False
        assert res["message"] == "Root access required."
        assert mgr.laws["elemental_inversion"] is False

    def test_enable_inversion(self, rooted: WorldLawOverrideManager) -> None:
        res = rooted.override_elemental_inversion(True)
        assert res["success"] is True
        assert res["elemental_inversion"] is True
        assert rooted.laws["elemental_inversion"] is True
        assert "inversion = True" in rooted.system_alerts[0]

    def test_disable_inversion(self, rooted: WorldLawOverrideManager) -> None:
        rooted.override_elemental_inversion(True)
        res = rooted.override_elemental_inversion(False)
        assert res["success"] is True
        assert rooted.laws["elemental_inversion"] is False
        assert "inversion = False" in rooted.system_alerts[-1]


class TestFatalSurviveOverride:
    def test_requires_root_access(self, mgr: WorldLawOverrideManager) -> None:
        res = mgr.override_fatal_survive(True)
        assert res["success"] is False
        assert res["message"] == "Root access required."
        assert mgr.laws["fatal_damage_survive"] is False

    def test_enable_fatal_survive(self, rooted: WorldLawOverrideManager) -> None:
        res = rooted.override_fatal_survive(True)
        assert res["success"] is True
        assert res["fatal_damage_survive"] is True
        assert rooted.laws["fatal_damage_survive"] is True
        assert "kernel hook = True" in rooted.system_alerts[0]

    def test_disable_fatal_survive(self, rooted: WorldLawOverrideManager) -> None:
        rooted.override_fatal_survive(True)
        res = rooted.override_fatal_survive(False)
        assert res["success"] is True
        assert rooted.laws["fatal_damage_survive"] is False


class TestCalculateModifiedDamage:
    def test_ordinary_damage_without_hacks(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        res = rooted.calculate_modified_damage(300, is_fatal=False, current_hp=1000)
        assert res["effective_damage"] == 300
        assert res["remaining_hp"] == 700
        assert res["survived_fatal_by_hack"] is False
        assert res["laws_applied"] == rooted.laws

    def test_damage_capped_by_damage_limit(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        res = rooted.calculate_modified_damage(20000, current_hp=99999)
        assert res["effective_damage"] == 9999
        assert res["remaining_hp"] == 90000

    def test_capped_damage_can_still_be_fatal(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        res = rooted.calculate_modified_damage(20000, is_fatal=True, current_hp=50)
        assert res["effective_damage"] == 9999
        assert res["remaining_hp"] <= 0
        assert res["survived_fatal_by_hack"] is False

    def test_fatal_survive_rescues_at_one_hp(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        rooted.override_fatal_survive(True)
        res = rooted.calculate_modified_damage(500, is_fatal=True, current_hp=100)
        assert res["effective_damage"] == 500
        assert res["remaining_hp"] == 1
        assert res["survived_fatal_by_hack"] is True

    def test_fatal_survive_needs_law_enabled(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        res = rooted.calculate_modified_damage(500, is_fatal=True, current_hp=100)
        assert res["remaining_hp"] == -400
        assert res["survived_fatal_by_hack"] is False

    def test_fatal_survive_not_applied_to_survivable_hit(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        rooted.override_fatal_survive(True)
        res = rooted.calculate_modified_damage(10, is_fatal=True, current_hp=100)
        assert res["remaining_hp"] == 90
        assert res["survived_fatal_by_hack"] is False

    def test_modified_damage_respects_new_damage_limit(
        self, rooted: WorldLawOverrideManager
    ) -> None:
        rooted.override_damage_limit(500)
        res = rooted.calculate_modified_damage(300, current_hp=1000)
        assert res["effective_damage"] == 300

    def test_works_even_without_root_access(
        self, mgr: WorldLawOverrideManager
    ) -> None:
        # 計算自体は既存法則値に基づき実行できる
        res = mgr.calculate_modified_damage(100, current_hp=200)
        assert res["effective_damage"] == 100
        assert res["remaining_hp"] == 100
