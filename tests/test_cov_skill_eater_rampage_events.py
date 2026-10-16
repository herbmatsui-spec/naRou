"""Coverage tests for skill_eater_rampage_events (SkillRampageManager)."""

from __future__ import annotations

import random

from skill_eater_rampage_events import SkillRampageManager


class TestSkillRampageManager:
    def setup_method(self) -> None:
        self.mgr = SkillRampageManager()

    def test_calculate_rampage_chance_tier_scaling(self) -> None:
        # Tier 1: 0.10 * 1 * (2.0 - 1.0) = 0.10
        assert self.mgr.calculate_rampage_chance(1) == 0.1
        # Tier 3: 0.10 * 3 * (2.0 - 1.0) = 0.30
        assert self.mgr.calculate_rampage_chance(3) == 0.3
        # Tier 5: 0.10 * 5 * (2.0 - 1.0) = 0.50
        assert self.mgr.calculate_rampage_chance(5) == 0.5

    def test_calculate_rampage_chance_buff_reduction(self) -> None:
        # buff=2.0 で (2.0 - 2.0) = 0 → 最大 0.02 にクランプ
        assert self.mgr.calculate_rampage_chance(5, player_crafting_buff=2.0) == 0.02
        # buff=0.0 で (2.0 - 0.0) = 2.0 → 2倍
        assert self.mgr.calculate_rampage_chance(1, player_crafting_buff=0.0) == 0.2

    def test_trigger_synthesis_no_rampage(self) -> None:
        random.seed(0)
        self.mgr = SkillRampageManager()
        result = self.mgr.trigger_synthesis_with_rampage_check(
            "Fire Bolt", 1, player_crafting_buff=1.0, force_rampage=False
        )
        assert result["success"] is True
        assert result["rampage"] is False
        assert result["created_skill"] == "Fire Bolt"

    def test_trigger_synthesis_force_rampage(self) -> None:
        result = self.mgr.trigger_synthesis_with_rampage_check(
            "Fire Bolt", 3, player_crafting_buff=1.0, force_rampage=True
        )
        assert result["success"] is False
        assert result["rampage"] is True
        assert "went out of control" in result["message"]
        assert "spawned_boss" in result
        boss = result["spawned_boss"]
        assert boss["origin_skill"] == "Fire Bolt"
        assert boss["hp"] == 1500 * 3
        assert boss["atk"] == 120 * 3
        assert boss["is_defeated"] is False
        assert boss["boss_id"] in self.mgr.active_rampages

    def test_wander_and_tick_expires_bosses(self) -> None:
        self.mgr.trigger_synthesis_with_rampage_check(
            "Fire Bolt", 1, force_rampage=True
        )
        boss_id = list(self.mgr.active_rampages.keys())[0]
        # time_limit_turns は 10 なので 10 ターン経過で期限切れ
        for _ in range(10):
            expired = self.mgr.wander_and_tick()
        assert len(expired) == 1
        assert expired[0]["boss_id"] == boss_id
        assert boss_id not in self.mgr.active_rampages

    def test_defeat_rampage_boss(self) -> None:
        self.mgr.trigger_synthesis_with_rampage_check(
            "Fire Bolt", 2, force_rampage=True
        )
        boss_id = list(self.mgr.active_rampages.keys())[0]
        result = self.mgr.defeat_rampage_boss(boss_id)
        assert result["success"] is True
        assert result["reward_skill"] == "Stabilized Fire Bolt (Pure Edition)"
        assert boss_id not in self.mgr.active_rampages

    def test_defeat_nonexistent_boss(self) -> None:
        result = self.mgr.defeat_rampage_boss("nonexistent_id")
        assert result["success"] is False
        assert "not found" in result["message"]
