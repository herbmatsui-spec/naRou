"""Coverage tests for skill_eater_pet_dispatch (PetDispatchManager)."""

from __future__ import annotations

import pytest

from skill_eater_pet_dispatch import PetDispatchManager


@pytest.fixture
def mgr() -> PetDispatchManager:
    return PetDispatchManager()


class TestInitialState:
    def test_default_pets(self, mgr: PetDispatchManager) -> None:
        assert set(mgr.pets) == {"husk_hound_01", "cyber_homunculus_01"}
        hound = mgr.pets["husk_hound_01"]
        assert hound["level"] == 1
        assert hound["is_injured"] is False
        assert hound["max_skill_slots"] == 3

    def test_default_dungeons_and_cooldown(self, mgr: PetDispatchManager) -> None:
        assert len(mgr.dungeon_targets) == 4
        assert mgr.active_dispatches == {}
        assert mgr.market_manipulation_cooldown == 0


class TestEquipSkill:
    def test_equip_success(self, mgr: PetDispatchManager) -> None:
        res = mgr.equip_pet_skill("husk_hound_01", "Trap Detection")
        assert res["success"] is True
        assert "Trap Detection" in mgr.pets["husk_hound_01"]["equipped_skills"]

    def test_equip_unknown_pet(self, mgr: PetDispatchManager) -> None:
        res = mgr.equip_pet_skill("ghost", "Skill")
        assert res["success"] is False
        assert "not found" in res["message"]

    def test_equip_slots_full(self, mgr: PetDispatchManager) -> None:
        pet = mgr.pets["husk_hound_01"]
        pet["equipped_skills"] = ["A", "B", "C"]
        res = mgr.equip_pet_skill("husk_hound_01", "D")
        assert res["success"] is False
        assert res["message"] == "Skill slots are full."
        assert "D" not in pet["equipped_skills"]


class TestSuitability:
    def test_perfect_match(self, mgr: PetDispatchManager) -> None:
        res = mgr.check_dispatch_suitability("husk_hound_01", "midas_scrap_dump")
        assert res["can_dispatch"] is True
        assert res["match_rate"] == 1.0
        assert res["matched_skills"] == ["Physical Attack"]

    def test_partial_match(self, mgr: PetDispatchManager) -> None:
        # homunculus は Stealth Digging を持たない
        res = mgr.check_dispatch_suitability("cyber_homunculus_01", "abandoned_reactor")
        assert res["can_dispatch"] is True
        assert res["match_rate"] == pytest.approx(0.5)
        assert res["matched_skills"] == ["Analysis Helper"]

    def test_no_match(self, mgr: PetDispatchManager) -> None:
        res = mgr.check_dispatch_suitability("cyber_homunculus_01", "midas_scrap_dump")
        assert res["can_dispatch"] is True
        assert res["match_rate"] == 0.0
        assert res["matched_skills"] == []

    def test_invalid_ids(self, mgr: PetDispatchManager) -> None:
        res = mgr.check_dispatch_suitability("ghost", "midas_scrap_dump")
        assert res == {"can_dispatch": False, "reason": "Invalid pet or dungeon"}
        res2 = mgr.check_dispatch_suitability("husk_hound_01", "hell")
        assert res2["can_dispatch"] is False

    def test_injured_pet_blocked(self, mgr: PetDispatchManager) -> None:
        mgr.pets["husk_hound_01"]["is_injured"] = True
        res = mgr.check_dispatch_suitability("husk_hound_01", "midas_scrap_dump")
        assert res == {"can_dispatch": False, "reason": "Pet is currently injured"}


class TestStartDispatch:
    def test_start_success_and_rate_cap(self, mgr: PetDispatchManager) -> None:
        res = mgr.start_dispatch("husk_hound_01", "midas_scrap_dump", duration_turns=3)
        assert res["success"] is True
        assert res["dungeon_name"] == "ミダス廃棄物処分場"
        assert res["turns"] == 3
        # 0.85 + 1.0*0.20 + 1*0.02 = 1.07 -> cap 0.95
        assert res["calculated_success_rate"] == pytest.approx(0.95)
        assert "husk_hound_01" in mgr.active_dispatches
        assert mgr.active_dispatches["husk_hound_01"]["remaining_turns"] == 3

    def test_start_accumulates_rate_without_cap(self, mgr: PetDispatchManager) -> None:
        mgr.equip_pet_skill("cyber_homunculus_01", "Stealth Digging")
        res = mgr.start_dispatch("cyber_homunculus_01", "abandoned_reactor")
        # 0.65 + 1.0*0.20 + 1*0.02 = 0.87 < 0.95
        assert res["calculated_success_rate"] == pytest.approx(0.87)

    def test_duplicate_dispatch_blocked(self, mgr: PetDispatchManager) -> None:
        mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        res = mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        assert res["success"] is False
        assert "already on dispatch" in res["message"]

    def test_injured_pet_cannot_start(self, mgr: PetDispatchManager) -> None:
        mgr.pets["husk_hound_01"]["is_injured"] = True
        res = mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        assert res["success"] is False

    def test_invalid_pet_cannot_start(self, mgr: PetDispatchManager) -> None:
        res = mgr.start_dispatch("ghost", "midas_scrap_dump")
        assert res["success"] is False


class TestResolveDispatch:
    def test_resolve_success_grants_rewards_and_exp(self, mgr: PetDispatchManager) -> None:
        mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        res = mgr.resolve_dispatch("husk_hound_01", force_success=True)
        assert res["success"] is True
        assert res["result"] == "MISSION_ACCOMPLISHED"
        assert res["rewards"] == {"junk": 150, "skill_fragments": 2}
        assert res["pet_exp"] == 50
        assert res["pet_level"] == 1
        assert "husk_hound_01" not in mgr.active_dispatches

    def test_level_up_at_100_exp(self, mgr: PetDispatchManager) -> None:
        mgr.pets["husk_hound_01"]["exp"] = 60
        mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        res = mgr.resolve_dispatch("husk_hound_01", force_success=True)
        assert res["pet_level"] == 2
        assert res["pet_exp"] == 10

    def test_resolve_failure_injures_pet(self, mgr: PetDispatchManager) -> None:
        mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        res = mgr.resolve_dispatch("husk_hound_01", force_success=False)
        assert res["success"] is False
        assert res["result"] == "MISSION_FAILED"
        assert res["pet_injured"] is True
        assert mgr.pets["husk_hound_01"]["is_injured"] is True

    def test_resolve_without_active_dispatch(self, mgr: PetDispatchManager) -> None:
        res = mgr.resolve_dispatch("husk_hound_01")
        assert res == {"success": False, "message": "No active dispatch for this pet."}


class TestTreatPet:
    def test_treat_injured_pet(self, mgr: PetDispatchManager) -> None:
        mgr.pets["husk_hound_01"]["is_injured"] = True
        res = mgr.treat_pet("husk_hound_01")
        assert res["success"] is True
        assert mgr.pets["husk_hound_01"]["is_injured"] is False

    def test_treat_healthy_pet_fails(self, mgr: PetDispatchManager) -> None:
        res = mgr.treat_pet("husk_hound_01")
        assert res["success"] is False
        assert res["message"] == "Pet is not injured."

    def test_treat_unknown_pet_fails(self, mgr: PetDispatchManager) -> None:
        res = mgr.treat_pet("ghost")
        assert res["success"] is False
        assert res["message"] == "Pet not found."


class TestFullCycle:
    def test_injury_blocks_then_treat_allows_dispatch(self, mgr: PetDispatchManager) -> None:
        mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        mgr.resolve_dispatch("husk_hound_01", force_success=False)
        assert mgr.check_dispatch_suitability("husk_hound_01", "midas_scrap_dump")[
            "can_dispatch"
        ] is False
        mgr.treat_pet("husk_hound_01")
        res = mgr.start_dispatch("husk_hound_01", "midas_scrap_dump")
        assert res["success"] is True
