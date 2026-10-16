"""Coverage tests for skill_eater_master_bosses (MasterBossManager)."""

from __future__ import annotations

from skill_eater_master_bosses import MasterBossManager


class TestMasterBossManager:
    def setup_method(self) -> None:
        self.mgr = MasterBossManager()

    def test_initial_bosses(self) -> None:
        assert "investment_boss" in self.mgr.bosses
        assert "debt_boss" in self.mgr.bosses
        assert self.mgr.collected_concept_keys == []

    def test_attack_unknown_boss(self) -> None:
        result = self.mgr.attack_master_boss("nonexistent", 1000, "Fire")
        assert result["error"] == "Boss not found"

    def test_attack_already_defeated_boss(self) -> None:
        self.mgr.bosses["investment_boss"]["is_defeated"] = True
        result = self.mgr.attack_master_boss("investment_boss", 1000, "Fire")
        assert result["error"] == "Boss already defeated"

    def test_attack_with_barrier_active(self) -> None:
        # バリアありで弱点スキルを使わない → ダメージ20%
        result = self.mgr.attack_master_boss("investment_boss", 1000, "Fire")
        assert result["weakness_hit"] is False
        assert result["barrier_active"] is True
        assert result["remaining_hp"] == 8000 - 200  # 1000 * 0.2

    def test_attack_weakness_breaks_barrier(self) -> None:
        # 弱点スキル "Fire + Ice" を使用 → バリア解除、3倍ダメージ
        result = self.mgr.attack_master_boss(
            "investment_boss", 1000, "Heat Shock Fusion: Fire + Ice"
        )
        assert result["weakness_hit"] is True
        assert result["barrier_active"] is False
        assert result["remaining_hp"] == 8000 - 3000  # 1000 * 3

    def test_attack_defeats_boss(self) -> None:
        # バリアを解除してから大ダメージで撃破
        self.mgr.attack_master_boss(
            "investment_boss", 1000, "Heat Shock Fusion: Fire + Ice"
        )
        result = self.mgr.attack_master_boss("investment_boss", 6000, "Anything")
        assert result["boss_defeated"] is True
        assert result["weakness_hit"] is False  # 2回目は弱点スキルではない
        assert result["dropped_concept_key"] == "Concept Key of 投資信託部門"
        assert result["stolen_master_skill"] == "Compound Multiplication (無限複利増殖)"
        assert len(self.mgr.collected_concept_keys) == 1

    def test_attack_defeats_boss_with_weakness(self) -> None:
        # 弱点スキルで直接撃破
        result = self.mgr.attack_master_boss(
            "investment_boss", 3000, "Heat Shock Fusion: Fire + Ice"
        )
        assert result["boss_defeated"] is True
        assert result["weakness_hit"] is True
        assert result["dropped_concept_key"] == "Concept Key of 投資信託部門"

    def test_collect_multiple_keys(self) -> None:
        self.mgr.attack_master_boss(
            "investment_boss", 3000, "Heat Shock Fusion: Fire + Ice"
        )
        self.mgr.attack_master_boss("debt_boss", 4000, "Defense + Sword Slash")
        assert len(self.mgr.collected_concept_keys) == 2
        assert "Concept Key of 負債回収部門" in self.mgr.collected_concept_keys
