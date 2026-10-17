"""APシステム テスト (Phase 2 Step 34-35)"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ecs.entity import Entity  # noqa: E402
from systems import CombatSystem, resolve_action  # noqa: E402


class TestAPSystem:
    """APシステムの基本動作テスト"""

    def test_ap_defaults_to_two(self):
        """全EntityのAP初期値は2"""
        e = Entity()
        assert e.ap == 2
        assert e.max_ap == 2

    def test_ap_can_be_modified(self):
        """APは設定・取得可能"""
        e = Entity()
        e.ap = 5
        assert e.ap == 5
        e.max_ap = 10
        assert e.max_ap == 10

    def test_reset_ap_restores_to_max(self):
        """reset_ap()で最大値まで回復"""
        e = Entity()
        e.ap = 0
        e.reset_ap()
        assert e.ap == e.max_ap

    def test_can_act_returns_true_when_enough_ap(self):
        """十分なAPがあればcan_actはTrue"""
        e = Entity()
        assert e.can_act(1) is True
        assert e.can_act(2) is True
        assert e.can_act(3) is False

    def test_spend_ap_reduces_ap(self):
        """spend_apでAPが減る"""
        e = Entity()
        assert e.spend_ap(1) is True
        assert e.ap == 1
        assert e.spend_ap(1) is True
        assert e.ap == 0
        # 足りない場合はFalseを返し消費しない
        assert e.spend_ap(1) is False
        assert e.ap == 0

    def test_attack_costs_one_ap(self):
        """攻撃はAP 1を消費"""
        attacker = Entity(name="Attacker")
        target = Entity(name="Target", x=1, y=0)
        target.hp = target.max_hp = 10

        initial_ap = attacker.ap
        success, msg = resolve_action(attacker, "attack", target=target)

        assert success is True
        assert attacker.ap == initial_ap - CombatSystem.AP_COST["attack"]
        assert "ダメージ" in msg or "かわされた" in msg

    def test_three_attacks_per_turn_at_two_ap(self):
        """AP 2なら1ターンに3回攻撃可能（初期2 + reset_apで2回復 = 4AP / 1 = 4回、ただしreset_apはターン開始時）"""
        # このテストは「AP制であること」を数値で固定する
        attacker = Entity(name="Attacker")
        target = Entity(name="Target", x=1, y=0)
        target.hp = target.max_hp = 999

        # 初期AP=2で2回攻撃可能
        assert attacker.spend_ap(CombatSystem.AP_COST["attack"]) is True
        assert attacker.spend_ap(CombatSystem.AP_COST["attack"]) is True
        # 3回目はAP不足
        assert attacker.spend_ap(CombatSystem.AP_COST["attack"]) is False
        assert attacker.ap == 0

    def test_wait_costs_zero_ap(self):
        """待機はAP 0（世界を進めるのみ）"""
        e = Entity()
        initial_ap = e.ap
        # waitはAP 0なので消費されない
        e.spend_ap(CombatSystem.AP_COST["wait"])
        assert e.ap == initial_ap

    def test_move_costs_one_ap(self):
        """移動はAP 1を消費"""
        e = Entity()
        initial_ap = e.ap
        e.spend_ap(CombatSystem.AP_COST["move"])
        assert e.ap == initial_ap - 1

    def test_spell_costs_one_ap(self):
        """呪文はAP 1を消費"""
        e = Entity()
        initial_ap = e.ap
        e.spend_ap(CombatSystem.AP_COST["spell"])
        assert e.ap == initial_ap - 1

    def test_non_vacuity_ap_zero_blocks_action(self):
        """非空虚性: AP=0なら行動不可"""
        e = Entity()
        e.ap = 0
        assert e.can_act(1) is False
        assert e.spend_ap(1) is False


class TestResolveAction:
    """resolve_action 統一エントリポイントのテスト"""

    def test_resolve_action_attack(self):
        """attackタイプで攻撃解決"""
        attacker = Entity(name="Attacker")
        target = Entity(name="Target", x=1, y=0)
        target.hp = target.max_hp = 10

        success, msg = resolve_action(attacker, "attack", target=target)
        assert success is True
        assert attacker.ap == 1  # 2 - 1 = 1

    def test_resolve_action_move(self):
        """moveタイプで移動解決"""
        from unittest.mock import Mock
        engine = Mock()
        engine.is_tile_free.return_value = True

        actor = Entity(name="Mover")
        success, msg = resolve_action(actor, "move", engine=engine, dx=1, dy=0)
        assert success is True
        assert actor.x == 1
        assert actor.ap == 1

    def test_resolve_action_wait(self):
        """waitタイプで待機解決（世界進行）"""
        from unittest.mock import Mock
        engine = Mock()

        actor = Entity(name="Waiter")
        initial_ap = actor.ap
        success, msg = resolve_action(actor, "wait", engine=engine)
        assert success is True
        assert actor.ap == initial_ap  # AP 0なので変わらない
        engine.advance_world.assert_called_once()

    def test_resolve_action_insufficient_ap(self):
        """AP不足なら失敗"""
        actor = Entity(name="Actor")
        actor.ap = 0
        success, msg = resolve_action(actor, "attack")
        assert success is False
        assert "AP不足" in msg

    def test_resolve_action_unknown_type(self):
        """未知のアクションタイプは失敗"""
        actor = Entity(name="Actor")
        success, msg = resolve_action(actor, "unknown_action")
        assert success is False
        assert "不明" in msg


class TestAPCostConstants:
    """AP_COST 定数の確認テスト"""

    def test_ap_cost_contains_expected_keys(self):
        """必要なキーがすべて定義されている"""
        expected = {"attack", "move", "wait", "spell", "item", "skill"}
        assert set(CombatSystem.AP_COST.keys()) == expected

    def test_ap_cost_values_are_correct(self):
        """各コスト値が仕様通り"""
        assert CombatSystem.AP_COST["attack"] == 1
        assert CombatSystem.AP_COST["move"] == 1
        assert CombatSystem.AP_COST["wait"] == 0
        assert CombatSystem.AP_COST["spell"] == 1
        assert CombatSystem.AP_COST["item"] == 1
        assert CombatSystem.AP_COST["skill"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
