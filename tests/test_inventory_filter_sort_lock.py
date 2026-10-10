"""
Unit and integration tests for Inventory Filter, Sort, and Lock Protection (Phase 2, Steps 45-46).
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

from naRou.constants import (
    CAT_ARMOR,
    CAT_ORE,
    CAT_POTION,
    CAT_WEAPON,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from naRou.systems.item_system import Inventory, Item


class TestInventoryFilterSortLock:
    """フェーズ2のテストスイート"""

    def test_filter_by_category(self):
        """カテゴリ別フィルタリングの検証 (Step 30)"""
        inv = Inventory()
        item_w = Item(name="剣", category=CAT_WEAPON, char="🗡️", color=(200, 200, 200))
        item_a = Item(name="鎧", category=CAT_ARMOR, char="🥋", color=(100, 100, 100))
        item_p = Item(name="ポーション", category=CAT_POTION, char="🧪", color=(255, 0, 0))

        inv.add_item(item_w)
        inv.add_item(item_a)
        inv.add_item(item_p)

        weapons = inv.filter_items("weapon")
        assert len(weapons) == 1
        assert weapons[0].name == "剣"

        equipment = inv.filter_items("equipment")
        assert len(equipment) == 2

        consumables = inv.filter_items("consumable")
        assert len(consumables) == 1
        assert consumables[0].name == "ポーション"

    def test_sorting_options(self):
        """各種キーによるソート検証 (Step 31-34)"""
        inv = Inventory()
        item1 = Item(name="C item", category=CAT_WEAPON, char="🗡️", color=(200, 200, 200), base_value=100, base_weight=5.0, quality=QUALITY_NORMAL)
        item2 = Item(name="A item", category=CAT_WEAPON, char="🗡️", color=(200, 200, 200), base_value=500, base_weight=1.0, quality=QUALITY_GOD)
        item3 = Item(name="B item", category=CAT_WEAPON, char="🗡️", color=(200, 200, 200), base_value=50, base_weight=10.0, quality=QUALITY_BAD)

        inv.add_item(item1)
        inv.add_item(item2)
        inv.add_item(item3)

        # Name sort
        sorted_by_name = inv.sort_items(key="name")
        assert [i.name for i in sorted_by_name] == ["A item", "B item", "C item"]

        # Value sort (descending)
        sorted_by_value = inv.sort_items(key="value", reverse=True)
        assert [i.name for i in sorted_by_value] == ["A item", "C item", "B item"]

        # Weight sort (ascending)
        sorted_by_weight = inv.sort_items(key="weight", reverse=False)
        assert [i.name for i in sorted_by_weight] == ["A item", "C item", "B item"]

        # Quality sort (descending)
        sorted_by_quality = inv.sort_items(key="quality", reverse=True)
        assert [i.name for i in sorted_by_quality] == ["A item", "C item", "B item"]

    def test_lock_protection_and_pinning(self):
        """お気に入りロック機能と売却・破棄保護、ソート時最上部固定の検証 (Step 37-40)"""
        inv = Inventory()
        item1 = Item(name="Item 1", category=CAT_WEAPON, char="🗡️", color=(200, 200, 200), base_value=100)
        item2 = Item(name="Item 2", category=CAT_WEAPON, char="🗡️", color=(200, 200, 200), base_value=500)

        inv.add_item(item1)
        inv.add_item(item2)

        # 初期状態は売却可能
        can_sell, _ = inv.can_sell(item1)
        assert can_sell

        # ロック切り替え
        locked = inv.toggle_lock(item1)
        assert locked is True
        assert item1.locked is True

        # ロック状態では売却不可
        can_sell, msg = inv.can_sell(item1)
        assert not can_sell
        assert "保護" in msg

        # ロック状態では破棄不可
        can_destroy, msg = inv.can_destroy(item1)
        assert not can_destroy
        assert "保護" in msg

        # ソート時、item1（valueが低いがlocked）が最上部に固定されること (Step 39)
        sorted_items = inv.sort_items(key="value", reverse=True)
        assert sorted_items[0].name == "Item 1"


if __name__ == "__main__":
    test = TestInventoryFilterSortLock()
    test.test_filter_by_category()
    test.test_sorting_options()
    test.test_lock_protection_and_pinning()
    print("All Phase 2 unit & integration tests PASSED!")
