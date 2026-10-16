"""Coverage tests for skill_eater_concept_trials (ConceptTrialsManager)."""

from __future__ import annotations

from skill_eater_concept_trials import ConceptTrialsManager


class TestConceptTrialsManager:
    def setup_method(self) -> None:
        self.mgr = ConceptTrialsManager()

    def test_initial_trials(self) -> None:
        assert "trial_of_time" in self.mgr.trials
        assert "trial_of_destruction" in self.mgr.trials
        assert self.mgr.cleared_trials == []
        assert self.mgr.unlocked_passives == []

    def test_enter_trial_unknown(self) -> None:
        result = self.mgr.enter_trial("nonexistent", [])
        assert result["success"] is False
        assert result["message"] == "Trial not found."

    def test_enter_trial_missing_key(self) -> None:
        result = self.mgr.enter_trial("trial_of_time", [])
        assert result["success"] is False
        assert "Access Denied" in result["message"]
        assert "Concept Key of 投資信託部門" in result["message"]

    def test_enter_trial_with_key(self) -> None:
        result = self.mgr.enter_trial(
            "trial_of_time", ["Concept Key of 投資信託部門"]
        )
        assert result["success"] is True
        assert result["trial_name"] == "時間領域の試練 (Chrono Trial)"
        assert result["rule"] == "REVERSE_TURN_ORDER"

    def test_apply_trial_rule_unknown_trial(self) -> None:
        result = self.mgr.apply_trial_rule_effect("nonexistent", {"hp": 100})
        assert result == {"hp": 100}

    def test_apply_reverse_turn_order(self) -> None:
        result = self.mgr.apply_trial_rule_effect(
            "trial_of_time", {"hp": 100, "damage_multiplier": 1.0}
        )
        assert result["auto_regen"] == 50
        assert result["turn_penalty"] is True

    def test_apply_double_damage_reduced_max_hp(self) -> None:
        result = self.mgr.apply_trial_rule_effect(
            "trial_of_destruction", {"hp": 100, "max_hp": 100, "damage_multiplier": 1.0}
        )
        assert result["damage_multiplier"] == 2.0
        assert result["max_hp"] == 50

    def test_complete_trial_unknown(self) -> None:
        result = self.mgr.complete_trial("nonexistent")
        assert result["success"] is False
        assert result["message"] == "Trial not found."

    def test_complete_trial(self) -> None:
        result = self.mgr.complete_trial("trial_of_time")
        assert result["success"] is True
        assert result["trial_name"] == "時間領域の試練 (Chrono Trial)"
        assert result["unlocked_passive"] == "Chrono Mastery (先行確定)"
        assert "trial_of_time" in self.mgr.cleared_trials
        assert "Chrono Mastery (先行確定)" in self.mgr.unlocked_passives
        assert self.mgr.trials["trial_of_time"]["cleared"] is True

    def test_complete_all_trials(self) -> None:
        self.mgr.complete_trial("trial_of_time")
        self.mgr.complete_trial("trial_of_destruction")
        assert len(self.mgr.cleared_trials) == 2
        assert len(self.mgr.unlocked_passives) == 2
