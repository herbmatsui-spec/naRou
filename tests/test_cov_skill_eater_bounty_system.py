"""Coverage tests for skill_eater_bounty_system (MidasBountyManager)."""

from __future__ import annotations

import random
from types import SimpleNamespace

from skill_eater_bounty_system import MidasBountyManager


class TestMidasBountyManager:
    def setup_method(self) -> None:
        self.mgr = MidasBountyManager()

    def test_initial_executives(self) -> None:
        assert "exec_01_valerius" in self.mgr.executives
        assert "exec_02_morgan" in self.mgr.executives
        assert self.mgr.defeated_count == 0

    def test_gather_intel_unknown_target(self) -> None:
        result = self.mgr.gather_intel("nonexistent")
        assert result["success"] is False
        assert result["message"] == "Target not found."

    def test_gather_intel_executive(self) -> None:
        result = self.mgr.gather_intel("exec_01_valerius")
        assert result["success"] is True
        assert "Intelligence acquired" in result["message"]
        assert self.mgr.executives["exec_01_valerius"]["intel_gathered"] is True

    def test_gather_intel_already_gathered(self) -> None:
        self.mgr.gather_intel("exec_01_valerius")
        result = self.mgr.gather_intel("exec_01_valerius")
        assert result["success"] is True
        assert result["message"] == "Intel already gathered."

    def test_set_ambush_trap_unknown_target(self) -> None:
        result = self.mgr.set_ambush_trap("nonexistent")
        assert result["success"] is False
        assert result["message"] == "Target not found."

    def test_set_ambush_trap_success(self) -> None:
        result = self.mgr.set_ambush_trap("exec_01_valerius", "EMP_ShortCircuit")
        assert result["success"] is True
        assert self.mgr.executives["exec_01_valerius"]["trap_set"] is True

    def test_initiate_combat_unknown_target(self) -> None:
        result = self.mgr.initiate_combat("nonexistent")
        assert result["error"] == "Target not found"

    def test_initiate_combat_already_defeated(self) -> None:
        self.mgr.executives["exec_01_valerius"]["is_defeated"] = True
        result = self.mgr.initiate_combat("exec_01_valerius")
        assert result["error"] == "Target already eliminated"

    def test_initiate_combat_no_debuffs(self) -> None:
        result = self.mgr.initiate_combat("exec_01_valerius")
        assert result["target_name"] == "徴税卿ヴァレリウス"
        assert result["effective_hp"] == 3000
        assert result["effective_atk"] == 180
        assert result["debuffs"] == []

    def test_initiate_combat_with_intel_and_trap(self) -> None:
        self.mgr.gather_intel("exec_01_valerius")
        self.mgr.set_ambush_trap("exec_01_valerius")
        result = self.mgr.initiate_combat("exec_01_valerius")
        assert result["effective_hp"] == int(3000 * 0.7)  # HP -30%
        assert result["effective_atk"] == int(180 * 0.8)  # ATK -20%
        assert len(result["debuffs"]) == 2

    def test_eliminate_executive_unknown(self) -> None:
        result = self.mgr.eliminate_executive("nonexistent")
        assert result["success"] is False
        assert result["message"] == "Executive not found."

    def test_eliminate_executive_already_defeated(self) -> None:
        self.mgr.executives["exec_01_valerius"]["is_defeated"] = True
        result = self.mgr.eliminate_executive("exec_01_valerius")
        assert result["success"] is False
        assert result["message"] == "Already defeated."

    def test_eliminate_executive_success(self) -> None:
        result = self.mgr.eliminate_executive("exec_01_valerius")
        assert result["success"] is True
        assert result["stolen_skill"] == "Skill Taxation (スキル課税)"
        assert result["defeated_count"] == 1
        assert self.mgr.executives["exec_01_valerius"]["is_defeated"] is True

    def test_generate_deep_dungeon_bounties_shallow_depth(self) -> None:
        # 深度10では min_depth 100 のアビス・ウォーデンは出現しない
        bounties = self.mgr.generate_deep_dungeon_bounties(current_depth=10)
        deep_targets = [b for b in bounties if b["type"] == "deep_target"]
        assert len(deep_targets) == 0

    def test_generate_deep_dungeon_bounties_deep_depth(self) -> None:
        # 深度150ではアビス・ウォーデン(100)とヴォイド・ストーカー(150)が出現
        bounties = self.mgr.generate_deep_dungeon_bounties(current_depth=150)
        deep_targets = [b for b in bounties if b["type"] == "deep_target"]
        assert len(deep_targets) == 2
        names = {b["name"] for b in deep_targets}
        assert "深淵の守護者 アビス・ウォーデン" in names
        assert "虚空の追跡者 ヴォイド・ストーカー" in names

    def test_eliminate_deep_target_unknown(self) -> None:
        result = self.mgr.eliminate_deep_target("nonexistent")
        assert result["success"] is False
        assert result["message"] == "Target not found."

    def test_eliminate_deep_target_already_defeated(self) -> None:
        self.mgr.deep_targets["abyss_warden"]["is_defeated"] = True
        result = self.mgr.eliminate_deep_target("abyss_warden")
        assert result["success"] is False
        assert result["message"] == "Already defeated."

    def test_eliminate_deep_target_success(self) -> None:
        result = self.mgr.eliminate_deep_target("abyss_warden")
        assert result["success"] is True
        assert result["target_type"] == "deep_target"
        assert result["reward_aldo"] == 50000
        assert result["defeated_count"] == 1

    def test_check_secret_boss_spawn_not_met(self) -> None:
        rank = SimpleNamespace(secret_rooms_found=0)
        result = self.mgr.check_secret_boss_spawn(current_depth=100, exploration_rank=rank)
        assert result is None

    def test_check_secret_boss_spawn_secret_rooms(self) -> None:
        rank = SimpleNamespace(secret_rooms_found=50)
        result = self.mgr.check_secret_boss_spawn(current_depth=10, exploration_rank=rank)
        assert result == "shadow_monarch"

    def test_roll_shadow_broker_encounter_shallow(self) -> None:
        # 深度1では遭遇率 0.5% で、ほぼ出現しない
        random.seed(0)
        result = self.mgr.roll_shadow_broker_encounter(current_depth=1)
        assert result is None or result["type"] == "shadow_broker" or "id" in result

    def test_roll_shadow_broker_encounter_deep(self) -> None:
        # 深度200では遭遇率 100% で出現
        random.seed(0)
        result = self.mgr.roll_shadow_broker_encounter(current_depth=200)
        assert result is not None
        assert result["id"] == "shadow_broker_01"

    def test_get_available_bounties(self) -> None:
        bounties = self.mgr.get_available_bounties(current_depth=50)
        assert isinstance(bounties, list)

    def test_eliminate_executive_compat(self) -> None:
        result = self.mgr.eliminate_executive_compat("exec_02_morgan")
        assert result["success"] is True
        assert result["stolen_skill"] == "Risk Hedge (絶対損切り結界)"
