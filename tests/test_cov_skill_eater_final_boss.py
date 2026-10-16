"""Coverage tests for skill_eater_final_boss (FinalBossCausalityManager)."""

from __future__ import annotations

from skill_eater_final_boss import FinalBossCausalityManager


class TestFinalBossCausalityManager:
    def setup_method(self) -> None:
        self.boss = FinalBossCausalityManager()

    def test_initial_state(self) -> None:
        assert self.boss.boss_name == "ドン・ミダス (Don Midas)"
        assert self.boss.phase == 1
        assert self.boss.hp == 15000
        assert self.boss.max_hp == 15000
        assert self.boss.is_defeated is False
        assert self.boss.is_frozen is False
        assert self.boss.stolen_player_actions == []

    def test_attack_phase1_normal(self) -> None:
        result = self.boss.attack_don_midas("Slash", 3000)
        assert result["phase"] == 1
        assert result["boss_hp"] == 12000
        assert result["damage_dealt"] == 3000

    def test_attack_phase1_triggers_phase2(self) -> None:
        # HP を 7500 以下にする攻撃でフェーズ2へ
        result = self.boss.attack_don_midas("Slash", 8000)
        assert result["transition"] is True
        assert result["phase"] == 2
        assert self.boss.hp == 25000
        assert self.boss.max_hp == 25000

    def test_attack_already_defeated(self) -> None:
        # 先にボスを倒す
        self.boss.hp = 0
        self.boss.is_defeated = True
        result = self.boss.attack_don_midas("Slash", 1000)
        assert result["status"] == "BOSS_ALREADY_DEFEATED"

    def test_phase2_causality_cancels_action(self) -> None:
        self.boss.phase = 2
        self.boss.hp = 25000
        result = self.boss.attack_don_midas("Fire Bolt", 5000, is_paradox_combo=False)
        assert result["action_cancelled"] is True
        assert result["cancelled_action"] == "Fire Bolt"
        assert result["damage_dealt"] == 0
        assert "Fire Bolt" in self.boss.stolen_player_actions

    def test_phase2_paradox_freezes_boss(self) -> None:
        self.boss.phase = 2
        self.boss.hp = 25000
        result = self.boss.attack_don_midas("Paradox", 1, is_paradox_combo=True)
        assert result["paradox_triggered"] is True
        assert result["boss_frozen"] is True
        assert self.boss.is_frozen is True
        assert self.boss.freeze_turns == 2

    def test_attack_while_frozen_triple_damage(self) -> None:
        self.boss.phase = 2
        self.boss.hp = 25000
        self.boss.is_frozen = True
        self.boss.freeze_turns = 3
        result = self.boss.attack_don_midas("Slash", 2000)
        assert result["boss_frozen"] is True
        assert result["damage_dealt"] == 6000  # 2000 * 3
        assert result["boss_hp"] == 19000

    def test_execute_core_extraction_not_frozen(self) -> None:
        result = self.boss.execute_core_extraction()
        assert result["success"] is False
        assert "frozen" in result["message"]

    def test_execute_core_extraction_frozen_wins(self) -> None:
        self.boss.phase = 2
        self.boss.hp = 25000
        self.boss.is_frozen = True
        result = self.boss.execute_core_extraction()
        assert result["boss_defeated"] is True
        assert result["unlocked_phase"] == 4
        assert self.boss.is_defeated is True

    def test_conclude_battle(self) -> None:
        result = self.boss.conclude_battle()
        assert result["boss_defeated"] is True
        assert result["phase3_completed"] is True
        assert result["unlocked_phase"] == 4
        assert "Phase 4" in result["message"]
