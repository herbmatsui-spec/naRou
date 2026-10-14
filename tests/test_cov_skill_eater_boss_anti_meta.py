"""Coverage tests for skill_eater_boss_anti_meta (AntiMetaBossBattleManager)."""

from __future__ import annotations

import pytest

from skill_eater_boss_anti_meta import AntiMetaBossBattleManager

COUNTER_SKILL = "Glitched Junk Shot"


@pytest.fixture
def mgr() -> AntiMetaBossBattleManager:
    return AntiMetaBossBattleManager()


class TestDefaults:
    def test_initial_state(self, mgr: AntiMetaBossBattleManager) -> None:
        assert mgr.boss_name == "監査官オプティマス (Auditor Optimus)"
        assert mgr.max_hp == 10000
        assert mgr.current_hp == 10000
        assert mgr.phase == 1
        assert mgr.is_defeated is False
        assert mgr.meta_barriers == {
            "high_dps_nullification": True,
            "future_prediction": False,
        }
        assert mgr.required_counter_skill == COUNTER_SKILL


class TestProcessPlayerAttack:
    def test_normal_attack_below_barrier_threshold(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.process_player_attack(200, "Basic Strike")
        assert res["phase"] == 1
        assert res["damage_taken"] == 200
        assert res["current_hp"] == 9800
        assert res["max_hp"] == 10000
        assert res["barrier_triggered"] is False
        assert res["message"] == ""

    def test_high_dps_attack_nullified_to_one(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.process_player_attack(5000, "Ultimate Nuke")
        assert res["damage_taken"] == 1
        assert res["current_hp"] == 9999
        assert res["barrier_triggered"] is True
        assert "OPTIMIZATION NULLIFIED" in res["message"]

    def test_threshold_boundary_300_not_nullified(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.process_player_attack(300, "Medium Hit")
        assert res["damage_taken"] == 300
        assert res["barrier_triggered"] is False

    def test_counter_skill_breaches_barrier_and_triples_damage(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.process_player_attack(100, COUNTER_SKILL)
        assert res["damage_taken"] == 300
        assert mgr.meta_barriers["high_dps_nullification"] is False
        assert "CRITICAL BREACH" in res["message"]
        assert res["barrier_triggered"] is False

    def test_after_breach_high_dps_passes_through(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        mgr.process_player_attack(100, COUNTER_SKILL)
        res = mgr.process_player_attack(400, "Ultimate Nuke")
        assert res["damage_taken"] == 400
        assert res["barrier_triggered"] is False
        assert res["message"] == ""

    def test_counter_breach_is_idempotent_when_barrier_already_off(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        mgr.process_player_attack(100, COUNTER_SKILL)
        res = mgr.process_player_attack(100, COUNTER_SKILL)
        assert res["damage_taken"] == 300
        assert "CRITICAL BREACH" in res["message"]

    def test_phase2_triggers_at_half_hp(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.process_player_attack(2000, COUNTER_SKILL)
        # 2000 * 3 = 6000 -> HP 4000 (<= 5000)
        assert res["phase"] == 2
        assert res["current_hp"] == 4000
        assert res["damage_taken"] == 6000
        assert mgr.meta_barriers["future_prediction"] is True
        assert "PHASE 2 TRIGGERED" in res["message"]

    def test_phase2_does_not_retrigger(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        mgr.process_player_attack(2000, COUNTER_SKILL)
        first_phase2_msg = mgr.process_player_attack(200, "Basic Strike")
        assert mgr.phase == 2
        assert "PHASE 2 TRIGGERED" not in first_phase2_msg["message"]

    def test_phase2_prediction_barrier_activates(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        mgr.process_player_attack(2000, COUNTER_SKILL)
        assert mgr.meta_barriers["high_dps_nullification"] is False
        assert mgr.meta_barriers["future_prediction"] is True

    def test_defeat_returns_conclusion_payload(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.process_player_attack(5000, COUNTER_SKILL)
        assert res["boss_defeated"] is True
        assert res["phase2_completed"] is True
        assert res["unlocked_phase"] == 3
        assert res["dropped_mastery_core"] == "Concept Key: Meta Bypass Core"
        assert "Phase 3 Unlocked" in res["message"]
        assert mgr.is_defeated is True
        assert mgr.current_hp == 0

    def test_attack_after_defeat_is_rejected(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        mgr.process_player_attack(5000, COUNTER_SKILL)
        res = mgr.process_player_attack(10, "Basic Strike")
        assert res == {"error": "Boss is already defeated"}

    def test_exact_lethal_damage_defeats_boss(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        # 素通りダメージでちょうど 0 になるケース (バリア貫通後の 10000)
        mgr.process_player_attack(100, COUNTER_SKILL)
        res = mgr.process_player_attack(9700, "Piercing Lance")
        assert res["boss_defeated"] is True

    def test_hp_never_goes_below_zero(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        mgr.process_player_attack(100, COUNTER_SKILL)
        mgr.process_player_attack(99999, "Piercing Lance")
        assert mgr.current_hp == 0


class TestConcludeBossBattle:
    def test_conclude_payload_direct_call(
        self, mgr: AntiMetaBossBattleManager
    ) -> None:
        res = mgr.conclude_boss_battle()
        assert res["boss_defeated"] is True
        assert res["phase2_completed"] is True
        assert res["unlocked_phase"] == 3
        assert res["dropped_mastery_core"] == "Concept Key: Meta Bypass Core"
        assert "Auditor Optimus fell!" in res["message"]
