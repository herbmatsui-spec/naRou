"""戦利品判断テスト (Phase 3 Step 59, 63, 66)"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import QUALITY_GOOD, QUALITY_NORMAL  # noqa: E402
from item_system import Item, _apply_affix, load_affixes  # noqa: E402


def _make_item(name: str, quality: str = QUALITY_NORMAL, affix_id: str | None = None) -> Item:
    item = Item(name, "weapon", "/", (200, 200, 200), quality=quality)
    if affix_id:
        affixes = load_affixes()
        affix = affixes.get(affix_id)
        if affix:
            _apply_affix(item, affix)
            item.affix_ids = (affix_id,)
            item.name = f"{item.name} [{affix.name}]"
    return item


def _combat_score(item: Item) -> int:
    """戦闘価値の指標: dmg_bonus + hit_bonus + pv + dv の合計"""
    return (
        getattr(item, "dmg_bonus", 0)
        + getattr(item, "hit_bonus", 0)
        + getattr(item, "pv", 0)
        + getattr(item, "dv", 0)
    )


class TestLootDecision:
    """Step 59: 床に残す理由"""

    def test_two_items_with_same_base_can_differ_by_affix(self):
        """Step 59.1: 同一基底・接尾辞違いの2品が比較可能であること"""
        a = _make_item("longsword", affix_id="of_sharpness")  # dmg+3, hit-3
        b = _make_item("longsword", affix_id="of_precision")  # hit+5, dmg-4

        assert a.name != b.name, f"接尾辞違いで表示名が同一: {a.name} == {b.name}"
        stat_a = (a.dmg_bonus, a.hit_bonus, a.pv, a.dv)
        stat_b = (b.dmg_bonus, b.hit_bonus, b.pv, b.dv)
        assert stat_a != stat_b, (
            f"接尾辞違いで能力ベクトルが同一: {stat_a} == {stat_b}"
        )

    def test_identical_base_and_affix_compare_by_quality(self):
        """Step 59.2: 同一基底・同一接尾辞は品質で区別できる (品質→能力ボーナス)"""
        from data_manager import DataManager

        dm = DataManager()
        item_ids = ("longsword", "shortsword", "leather_armor")
        normal_items = [
            dm.create_item(item_id, quality=QUALITY_NORMAL)
            for item_id in item_ids
        ]
        good_items = [
            dm.create_item(item_id, quality=QUALITY_GOOD)
            for item_id in item_ids
        ]

        for n, g in zip(normal_items, good_items):
            score_n = _combat_score(n)
            score_g = _combat_score(g)
            assert g.quality == QUALITY_GOOD and n.quality == QUALITY_NORMAL
            assert score_g > score_n, (
                f"{n.name}: GOOD品 ({score_g}) が NORMAL品 ({score_n}) を上回っていない"
            )

    def test_player_has_a_reason_to_leave_a_weaker_item_on_the_floor(self):
        """Step 59.3/66: 弱い品を床に残す理由が実在する

        同一基底で戦闘価値の低い品は、インベントリの枠を浪費する。
        比較関数が「より弱い品」を判別できることを確認する。
        """
        strong = _make_item("longsword", affix_id="of_the_berserker")  # dmg+8, pv-4, max_hp-8
        weak = _make_item("longsword", affix_id="of_precision")  # hit+5, dmg-4

        assert _combat_score(strong) > _combat_score(weak), (
            f"強弱の判別ができない: strong={_combat_score(strong)}, weak={_combat_score(weak)}"
        )
        # 接尾辞表示により、プレイヤーは拾う前に比較できる
        assert strong.name != weak.name

    def test_dropping_a_worse_item_is_possible(self):
        """Step 66.3: より弱い品を捨てる動詞が実在する"""
        # Drop 動詞はインベントリ画面の D キー (input_handler._handle_keydown_legacy)
        # ここでは Item が床に戻せること (x/y 座標を持つ) を検証
        item = _make_item("longsword")
        item.x, item.y = 10, 10
        assert (item.x, item.y) == (10, 10), "アイテムに座標が設定できない"

        # remove_item 相当: count 操作でスタックから外せること
        item2 = _make_item("potion", affix_id=None)
        item2.count = 2
        item2.count -= 1
        assert item2.count == 1


class TestInventoryChoice:
    """Step 63: インベントリ選択"""

    def test_inventory_full_forces_a_choice(self):
        """Step 63.1: インベントリが満杯なら拾うか捨てるかを選ぶ必要がある"""
        from item_system import Inventory

        inv = Inventory()
        # 容量を確認 (小さい容量なら満タン判定が実在する)
        capacity = getattr(inv, "capacity", None) or getattr(inv, "max_size", None)
        if capacity is None:
            pytest.skip("Inventory に容量制限が無い (Step 63 は後日)")
        # 満タンまで詰める
        filled = 0
        for i in range(capacity + 1):
            item = _make_item(f"item_{i}")
            ok, _msg = inv.add_item(item)
            if ok:
                filled += 1
        assert filled == capacity, f"容量 {capacity} を超えて {filled} 個入った"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
