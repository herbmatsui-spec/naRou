"""Coverage tests for skill_eater_toxicity_system (SkillToxicityManager)."""

from __future__ import annotations

from skill_eater_toxicity_system import SafehouseLocation, SkillToxicityManager


class TestSkillToxicityManager:
    def setup_method(self) -> None:
        self.mgr = SkillToxicityManager()

    def test_initial_state(self) -> None:
        assert self.mgr.state.current_toxicity == 0
        assert self.mgr.state.max_toxicity == 100
        assert self.mgr.state.debuff_threshold == 80
        assert self.mgr.state.is_overloaded is False

    def test_add_toxicity_below_threshold(self) -> None:
        result = self.mgr.add_toxicity(30, "Test Skill")
        assert result["current_toxicity"] == 30
        assert result["is_overloaded"] is False
        assert result["action"] == "Test Skill"

    def test_add_toxicity_crosses_threshold(self) -> None:
        result = self.mgr.add_toxicity(80, "Devour")
        assert result["current_toxicity"] == 80
        assert result["is_overloaded"] is True
        assert self.mgr.state.movement_speed_penalty == 0.5
        assert self.mgr.state.atk_multiplier == 0.5

    def test_add_toxicity_clamped_at_max(self) -> None:
        self.mgr.add_toxicity(100)
        result = self.mgr.add_toxicity(50, "Overflow")
        assert result["current_toxicity"] == 100

    def test_render_toxicity_gauge_green(self) -> None:
        self.mgr.add_toxicity(20)
        ui = self.mgr.render_toxicity_gauge_ui()
        assert ui["percent"] == 20
        assert ui["color"] == "GREEN_SAFE"
        assert ui["is_overloaded"] is False

    def test_render_toxicity_gauge_yellow(self) -> None:
        self.mgr.add_toxicity(50)
        ui = self.mgr.render_toxicity_gauge_ui()
        assert ui["color"] == "YELLOW_WARN"
        assert ui["is_overloaded"] is False

    def test_render_toxicity_gauge_red(self) -> None:
        self.mgr.add_toxicity(90)
        ui = self.mgr.render_toxicity_gauge_ui()
        assert ui["color"] == "RED_FLASHING"
        assert ui["is_overloaded"] is True

    def test_rest_at_safehouse(self) -> None:
        self.mgr.add_toxicity(90)
        safehouse = SafehouseLocation("safe_01", "隠れ家", recovery_rate=50)
        result = self.mgr.rest_at_safehouse(safehouse)
        assert result["success"] is True
        assert result["recovered_toxicity"] == 50
        assert result["current_toxicity"] == 40
        assert result["is_overloaded"] is False

    def test_rest_at_safehouse_full_recovery(self) -> None:
        self.mgr.add_toxicity(30)
        safehouse = SafehouseLocation("safe_02", "医療ステーション", recovery_rate=100)
        result = self.mgr.rest_at_safehouse(safehouse)
        assert result["current_toxicity"] == 0
        assert result["is_overloaded"] is False

    def test_validate_skill_slot_toxicity_cost_ok(self) -> None:
        result = self.mgr.validate_skill_slot_toxicity_cost([10, 20, 15])
        assert result["can_equip"] is True
        assert result["total_load"] == 45
        assert result["error"] is None

    def test_validate_skill_slot_toxicity_cost_exceeded(self) -> None:
        result = self.mgr.validate_skill_slot_toxicity_cost([30, 25])
        assert result["can_equip"] is False
        assert result["total_load"] == 55
        assert result["error"] == "TOXICITY_LOAD_EXCEEDED"

    def test_get_rest_presentation_fx(self) -> None:
        fx = self.mgr.get_rest_presentation_fx()
        assert fx["sound"] == "se_safehouse_rest_heal.ogg"
        assert fx["screen_effect"] == "FADE_TO_BLACK_CALM"
        assert fx["duration_ms"] == 1500
