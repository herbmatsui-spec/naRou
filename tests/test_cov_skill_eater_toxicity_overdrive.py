"""Coverage tests for skill_eater_toxicity_overdrive (ToxicityOverdriveManager)."""

from __future__ import annotations

from skill_eater_toxicity_overdrive import ToxicityOverdriveManager


class TestToxicityOverdriveManager:
    def setup_method(self) -> None:
        self.mgr = ToxicityOverdriveManager(trigger_threshold=100.0, duration_turns=3)

    def test_initial_state(self) -> None:
        assert self.mgr.trigger_threshold == 100.0
        assert self.mgr.duration_turns == 3
        assert self.mgr.is_active is False
        assert self.mgr.is_stunned is False

    def test_can_trigger_overdrive_not_met(self) -> None:
        assert self.mgr.can_trigger_overdrive(50.0) is False

    def test_can_trigger_overdrive_met(self) -> None:
        assert self.mgr.can_trigger_overdrive(100.0) is True
        assert self.mgr.can_trigger_overdrive(150.0) is True

    def test_can_trigger_overdrive_already_active(self) -> None:
        self.mgr.is_active = True
        assert self.mgr.can_trigger_overdrive(150.0) is False

    def test_can_trigger_overdrive_stunned(self) -> None:
        self.mgr.is_stunned = True
        assert self.mgr.can_trigger_overdrive(150.0) is False

    def test_trigger_overdrive_success(self) -> None:
        result = self.mgr.trigger_overdrive(150.0)
        assert result["success"] is True
        assert self.mgr.is_active is True
        assert self.mgr.remaining_turns == 3

    def test_trigger_overdrive_failure(self) -> None:
        result = self.mgr.trigger_overdrive(50.0)
        assert result["success"] is False
        assert self.mgr.is_active is False

    def test_get_overdrive_buffs_inactive(self) -> None:
        buffs = self.mgr.get_overdrive_buffs()
        assert buffs == {"atk_multiplier": 1.0, "speed_multiplier": 1.0, "crit_rate_bonus": 0.0}

    def test_get_overdrive_buffs_active(self) -> None:
        self.mgr.is_active = True
        buffs = self.mgr.get_overdrive_buffs()
        assert buffs == {"atk_multiplier": 3.0, "speed_multiplier": 2.5, "crit_rate_bonus": 0.50}

    def test_end_overdrive(self) -> None:
        self.mgr.is_active = True
        self.mgr.remaining_turns = 1
        result = self.mgr.end_overdrive(current_hp=100, max_hp=100)
        assert self.mgr.is_active is False
        assert self.mgr.is_stunned is True
        assert self.mgr.stun_remaining_turns == 2
        assert result["recoil_damage"] == 30  # 100 * 0.30
        assert result["remaining_hp"] == 70

    def test_end_overdrive_min_hp_1(self) -> None:
        self.mgr.is_active = True
        result = self.mgr.end_overdrive(current_hp=10, max_hp=100)
        assert result["remaining_hp"] == 1  # 最低1は残る

    def test_tick_turn_overdrive_active(self) -> None:
        self.mgr.is_active = True
        self.mgr.remaining_turns = 2
        result = self.mgr.tick_turn(current_hp=100, max_hp=100)
        assert result["remaining_turns"] == 1
        assert result["is_active"] is True

    def test_tick_turn_overdrive_expires(self) -> None:
        self.mgr.is_active = True
        self.mgr.remaining_turns = 1
        result = self.mgr.tick_turn(current_hp=100, max_hp=100)
        assert result["is_active"] is False
        assert result["is_stunned"] is True
        assert result["recoil_damage"] == 30

    def test_tick_turn_stunned(self) -> None:
        self.mgr.is_stunned = True
        self.mgr.stun_remaining_turns = 2
        result = self.mgr.tick_turn(current_hp=100, max_hp=100)
        assert result["stun_remaining_turns"] == 1
        assert result["is_stunned"] is True

    def test_tick_turn_stun_recovers(self) -> None:
        self.mgr.is_stunned = True
        self.mgr.stun_remaining_turns = 1
        result = self.mgr.tick_turn(current_hp=100, max_hp=100)
        assert result["is_stunned"] is False
        assert result["message"] == "Recovered from toxic stun."

    def test_hook_with_phase1_toxicity_not_enough(self) -> None:
        class FakeTox:
            toxicity = 50.0

        result = self.mgr.hook_with_phase1_toxicity(FakeTox(), 100, 100)
        assert result["success"] is False

    def test_hook_with_phase1_toxicity_enough(self) -> None:
        fake = type("FakeTox", (), {"toxicity": 150.0})()
        result = self.mgr.hook_with_phase1_toxicity(fake, 100, 100)
        assert result["success"] is True
        assert fake.toxicity == 0.0  # 全消費
