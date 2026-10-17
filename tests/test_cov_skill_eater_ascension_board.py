"""Coverage tests for skill_eater_ascension_board (AscensionBoard)."""

from __future__ import annotations

from types import SimpleNamespace

from skill_eater_ascension_board import AscensionBoard


def make_rank(**kwargs) -> SimpleNamespace:
    defaults = dict(
        max_depth_reached=0,
        floors_cleared=0,
        secret_rooms_found=0,
        total_exp=0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestAscensionBoard:
    def setup_method(self) -> None:
        AscensionBoard.reset_instance()
        self.board = AscensionBoard.get_instance()

    def test_singleton(self) -> None:
        b1 = AscensionBoard.get_instance()
        b2 = AscensionBoard.get_instance()
        assert b1 is b2

    def test_initial_state(self) -> None:
        assert len(self.board.nodes) == 4
        assert self.board.active_links_count == 0
        assert self.board.synergy_buffs["all_damage_multiplier"] == 1.0

    def test_equip_core_unknown_node(self) -> None:
        result = self.board.equip_core("nonexistent", "Fire Core", "Fire")
        assert result["success"] is False
        assert "does not exist" in result["message"]

    def test_equip_core_success(self) -> None:
        result = self.board.equip_core("alpha", "Flame Core", "Fire")
        assert result["success"] is True
        assert self.board.nodes["alpha"]["equipped_core"] == "Flame Core"
        assert self.board.nodes["alpha"]["element"] == "Fire"
        assert "active_links" in result

    def test_equip_core_synergy_no_match(self) -> None:
        # 異なる要素なのでシナジーは発生しない
        self.board.equip_core("alpha", "Flame Core", "Fire")
        self.board.equip_core("beta", "Ice Core", "Ice")
        assert self.board.active_links_count == 0
        assert self.board.synergy_buffs["all_damage_multiplier"] == 1.0

    def test_equip_core_synergy_match(self) -> None:
        # 同じ要素で隣接 → シナジー発生
        self.board.equip_core("alpha", "Flame Core", "Fire")
        self.board.equip_core("beta", "Blaze Core", "Fire")
        assert self.board.active_links_count == 1
        assert self.board.synergy_buffs["all_damage_multiplier"] == 1.2
        assert self.board.synergy_buffs["mp_cost_reduction"] == 0.1
        assert self.board.synergy_buffs["crit_rate_bonus"] == 0.05

    def test_unequip_core_unknown_node(self) -> None:
        result = self.board.unequip_core("nonexistent")
        assert result["success"] is False

    def test_unequip_core_success(self) -> None:
        self.board.equip_core("alpha", "Flame Core", "Fire")
        result = self.board.unequip_core("alpha")
        assert result["success"] is True
        assert self.board.nodes["alpha"]["equipped_core"] is None
        assert self.board.nodes["alpha"]["element"] == "Void"

    def test_get_board_state(self) -> None:
        state = self.board.get_board_state()
        assert "nodes" in state
        assert "active_links" in state
        assert "buffs" in state

    def test_check_conditions_deep_delver(self) -> None:
        rank = make_rank(max_depth_reached=60)
        unlocked = self.board._check_exploration_node_conditions(rank)
        assert "deep_delver" in unlocked  # threshold 50 を超過

    def test_check_conditions_full_clearer(self) -> None:
        rank = make_rank(floors_cleared=99)
        unlocked = self.board._check_exploration_node_conditions(rank)
        assert "full_clearer" in unlocked  # threshold 99

    def test_check_conditions_not_met(self) -> None:
        rank = make_rank(max_depth_reached=10, floors_cleared=5)
        unlocked = self.board._check_exploration_node_conditions(rank)
        assert unlocked == []

    def test_unlock_exploration_node_unknown(self) -> None:
        result = self.board.unlock_exploration_node("nonexistent", make_rank())
        assert result["success"] is False
        assert "Unknown exploration node" in result["message"]

    def test_unlock_exploration_node_success(self) -> None:
        rank = make_rank(max_depth_reached=60)
        # まず条件チェックで deep_delver を解放対象にする
        self.board._check_exploration_node_conditions(rank)
        result = self.board.unlock_exploration_node("deep_delver", rank)
        assert result["success"] is True
        assert result["level"] == 1
        assert self.board.exploration_nodes["deep_delver"]["unlocked"] is True

    def test_unlock_exploration_node_maxed(self) -> None:
        # deep_delver を max_level(4) まで上げる
        node = self.board.exploration_nodes["deep_delver"]
        node["level"] = 4
        node["unlocked"] = True
        result = self.board.unlock_exploration_node("deep_delver", make_rank())
        assert result["success"] is True
        assert "already maxed out" in result["message"]

    def test_check_and_unlock_exploration_nodes(self) -> None:
        rank = make_rank(max_depth_reached=60, floors_cleared=99)
        results = self.board.check_and_unlock_exploration_nodes(rank)
        # deep_delver と full_clearer が解放されるはず
        assert len(results) >= 1
        assert all(r["success"] is True for r in results)

    def test_get_exploration_node_status(self) -> None:
        status = self.board.get_exploration_node_status()
        assert "deep_delver" in status
        assert "full_clearer" in status
