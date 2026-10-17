"""Coverage tests for skill_eater_temporal_vault (TemporalVaultManager)."""

from __future__ import annotations

import pytest

from skill_eater_temporal_vault import TemporalVaultManager


@pytest.fixture
def mgr() -> TemporalVaultManager:
    return TemporalVaultManager()


def skill(name: str) -> dict:
    return {"name": name, "id": name.lower().replace(" ", "_")}


class TestVaultDefaults:
    def test_initial_state(self) -> None:
        m = TemporalVaultManager()
        assert m.max_carry_slots == 5
        assert m.max_vault_slots == 3
        assert m.carry_over_slots == []
        assert m.vault_slots == []
        assert m.is_selection_locked is False

    def test_custom_slot_sizes(self) -> None:
        m = TemporalVaultManager(max_carry_slots=2, max_vault_slots=1)
        assert m.max_carry_slots == 2
        assert m.max_vault_slots == 1


class TestAddToCarryOver:
    def test_add_first_skill(self, mgr: TemporalVaultManager) -> None:
        res = mgr.add_to_carry_over(skill("Fire Bolt"))
        assert res["success"] is True
        assert res["carried_count"] == 1
        assert res["remaining_slots"] == 4
        assert "Fire Bolt" in res["message"]
        assert mgr.carry_over_slots[0]["name"] == "Fire Bolt"

    def test_add_until_full_then_reject(self, mgr: TemporalVaultManager) -> None:
        for i in range(5):
            res = mgr.add_to_carry_over(skill(f"Skill {i}"))
            assert res["success"] is True
        res = mgr.add_to_carry_over(skill("Overflow Skill"))
        assert res["success"] is False
        assert res["message"] == "Carry-over slots full (Max 5)."
        assert len(mgr.carry_over_slots) == 5

    def test_add_rejected_after_lock(self, mgr: TemporalVaultManager) -> None:
        mgr.add_to_carry_over(skill("Kept Skill"))
        mgr.lock_and_finalize_selection()
        res = mgr.add_to_carry_over(skill("Late Skill"))
        assert res["success"] is False
        assert res["message"] == "Selection is already locked."
        assert len(mgr.carry_over_slots) == 1


class TestRemoveFromCarryOver:
    def test_remove_existing_skill(self, mgr: TemporalVaultManager) -> None:
        mgr.add_to_carry_over(skill("Fire Bolt"))
        mgr.add_to_carry_over(skill("Ice Bolt"))
        res = mgr.remove_from_carry_over("Fire Bolt")
        assert res["success"] is True
        assert res["removed"]["name"] == "Fire Bolt"
        assert "Fire Bolt" in res["message"]
        assert [s["name"] for s in mgr.carry_over_slots] == ["Ice Bolt"]

    def test_remove_second_skill_iterates_past_first(
        self, mgr: TemporalVaultManager
    ) -> None:
        mgr.add_to_carry_over(skill("Fire Bolt"))
        mgr.add_to_carry_over(skill("Ice Bolt"))
        res = mgr.remove_from_carry_over("Ice Bolt")
        assert res["success"] is True
        assert res["removed"]["name"] == "Ice Bolt"
        assert [s["name"] for s in mgr.carry_over_slots] == ["Fire Bolt"]

    def test_remove_missing_skill(self, mgr: TemporalVaultManager) -> None:
        res = mgr.remove_from_carry_over("Nonexistent")
        assert res["success"] is False
        assert res["message"] == "Skill [Nonexistent] not found in carry-over slots."

    def test_remove_rejected_after_lock(self, mgr: TemporalVaultManager) -> None:
        mgr.add_to_carry_over(skill("Kept Skill"))
        mgr.lock_and_finalize_selection()
        res = mgr.remove_from_carry_over("Kept Skill")
        assert res["success"] is False
        assert res["message"] == "Selection is already locked."
        assert len(mgr.carry_over_slots) == 1


class TestDepositWithdrawVault:
    def test_deposit_to_vault(self, mgr: TemporalVaultManager) -> None:
        res = mgr.deposit_to_vault(skill("Vaulted Skill"))
        assert res["success"] is True
        assert res["vault_count"] == 1
        assert "Vaulted Skill" in res["message"]
        assert mgr.vault_slots[0]["name"] == "Vaulted Skill"

    def test_deposit_when_vault_full(self, mgr: TemporalVaultManager) -> None:
        for i in range(3):
            assert mgr.deposit_to_vault(skill(f"Vault {i}"))["success"] is True
        res = mgr.deposit_to_vault(skill("Vault Overflow"))
        assert res["success"] is False
        assert res["message"] == "Vault is full (Max 3)."
        assert len(mgr.vault_slots) == 3

    def test_withdraw_existing_skill(self, mgr: TemporalVaultManager) -> None:
        mgr.deposit_to_vault(skill("Stored Skill"))
        res = mgr.withdraw_from_vault("Stored Skill")
        assert res["success"] is True
        assert res["withdrawn"]["name"] == "Stored Skill"
        assert "Stored Skill" in res["message"]
        assert mgr.vault_slots == []

    def test_withdraw_second_skill_iterates_past_first(
        self, mgr: TemporalVaultManager
    ) -> None:
        mgr.deposit_to_vault(skill("Stored Skill"))
        mgr.deposit_to_vault(skill("Deep Skill"))
        res = mgr.withdraw_from_vault("Deep Skill")
        assert res["success"] is True
        assert res["withdrawn"]["name"] == "Deep Skill"
        assert [s["name"] for s in mgr.vault_slots] == ["Stored Skill"]

    def test_withdraw_missing_skill(self, mgr: TemporalVaultManager) -> None:
        res = mgr.withdraw_from_vault("Ghost Skill")
        assert res["success"] is False
        assert res["message"] == "Skill [Ghost Skill] not found in Vault."

    def test_deposit_allowed_even_after_selection_lock(
        self, mgr: TemporalVaultManager
    ) -> None:
        # 金庫への出し入れはロック対象外 (持ち込み枠のみ確定対象)
        mgr.add_to_carry_over(skill("Kept Skill"))
        mgr.lock_and_finalize_selection()
        res = mgr.deposit_to_vault(skill("Late Vault Skill"))
        assert res["success"] is True
        assert mgr.vault_slots[0]["name"] == "Late Vault Skill"


class TestLockAndFinalize:
    def test_finalize_with_zero_skills_fails(self, mgr: TemporalVaultManager) -> None:
        res = mgr.lock_and_finalize_selection()
        assert res["success"] is False
        assert res["message"] == "Cannot finalize with 0 skills selected."
        assert mgr.is_selection_locked is False

    def test_finalize_reports_carry_and_vault_names(
        self, mgr: TemporalVaultManager
    ) -> None:
        mgr.add_to_carry_over(skill("Carry A"))
        mgr.add_to_carry_over(skill("Carry B"))
        mgr.deposit_to_vault(skill("Vaulted C"))
        res = mgr.lock_and_finalize_selection()
        assert res["success"] is True
        assert res["phase4_completed"] is True
        assert res["final_carry_skills"] == ["Carry A", "Carry B"]
        assert res["vaulted_skills"] == ["Vaulted C"]
        assert mgr.is_selection_locked is True

    def test_finalize_message(self, mgr: TemporalVaultManager) -> None:
        mgr.add_to_carry_over(skill("Carry A"))
        res = mgr.lock_and_finalize_selection()
        assert "SELECTION LOCKED" in res["message"]

    def test_double_finalize_keeps_lock(self, mgr: TemporalVaultManager) -> None:
        mgr.add_to_carry_over(skill("Carry A"))
        assert mgr.lock_and_finalize_selection()["success"] is True
        second = mgr.lock_and_finalize_selection()
        assert second["success"] is True
        assert second["final_carry_skills"] == ["Carry A"]
