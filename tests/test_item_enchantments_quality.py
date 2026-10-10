import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

from naRou.constants import (
    ALL_QUALITIES,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from naRou.data_manager import DataManager
from data.generated.item.enchantment import ItemEnchantmentInstance
from item_generator import ItemGenerator, generate_random_item
from naRou.systems.item_system import Inventory, Item


class TestItemQualityAndEnchantments:
    """ステップ22 & 23のテストスイート"""

    def setup_method(self):
        self.data_manager = DataManager()
        self.generator = ItemGenerator(self.data_manager)

    def test_roll_quality(self):
        """品質抽選が有効な値を返すこと"""
        for _ in range(50):
            q = self.generator.roll_quality(dungeon_level=5)
            assert q in ALL_QUALITIES

    def test_enchant_count_by_quality(self):
        """品質に応じたエンチャント数が正しく抽選されること"""
        assert self.generator.get_enchant_count(QUALITY_BAD) == 0
        assert self.generator.get_enchant_count(QUALITY_NORMAL) in (0, 1)
        assert 1 <= self.generator.get_enchant_count(QUALITY_GOOD) <= 2
        assert 2 <= self.generator.get_enchant_count(QUALITY_MIRACLE) <= 4
        assert 4 <= self.generator.get_enchant_count(QUALITY_GOD) <= 6

    def test_create_item_with_quality(self):
        """品質指定でのアイテム生成とステータス補正"""
        item_normal = self.generator.create_item("longsword", quality=QUALITY_NORMAL)
        assert item_normal.quality == QUALITY_NORMAL
        assert item_normal.hit_bonus == 2  # base hit bonus of longsword is 2

        item_miracle = self.generator.create_item("longsword", quality=QUALITY_MIRACLE)
        assert item_miracle.quality == QUALITY_MIRACLE
        assert item_miracle.value > item_normal.value
        assert len(item_miracle.enchantments) >= 2

    def test_serialization_roundtrip(self):
        """シリアライズとデシリアライズで品質とエンチャントが維持されること"""
        item = self.generator.create_item("longsword", quality=QUALITY_MIRACLE)
        data = item.to_dict()
        assert data["quality"] == QUALITY_MIRACLE
        assert isinstance(data["enchants"], list)

        restored = Item.from_dict(data)
        assert restored.quality == QUALITY_MIRACLE
        assert len(restored.enchantments) == len(item.enchantments)
        assert restored.value == item.value

    def test_inventory_equipment_stat_bonuses(self):
        """インベントリに装備したアイテムのエンチャント補正計算 (Step 23)"""
        inv = Inventory()
        # 武器作成
        weapon = self.generator.create_item("longsword", quality=QUALITY_NORMAL)
        # エンチャントを手動追加
        ench_str = ItemEnchantmentInstance(
            id="ench_str",
            name="剛力",
            type="stat_bonus",
            target_stat="strength",
            power=5,
        )
        ench_fire = ItemEnchantmentInstance(
            id="ench_fire_dmg",
            name="紅蓮",
            type="element_damage",
            element="fire",
            power=8,
        )
        weapon.enchantments = [ench_str, ench_fire]

        inv.add_item(weapon)
        ok, msg = inv.equip(weapon, "main_hand")
        assert ok

        # ステータス計算検証
        bonuses = inv.get_stat_bonuses()
        assert bonuses.get("strength") == 5

        elem_dmgs = inv.get_weapon_element_damages()
        assert len(elem_dmgs) == 1
        assert elem_dmgs[0] == ("fire", 8)

    def test_random_item_generator_shortcut(self):
        """generate_random_itemヘルパー関数の検証"""
        item = generate_random_item(dungeon_level=10)
        assert isinstance(item, Item)
        assert item.quality in ALL_QUALITIES


if __name__ == "__main__":
    test = TestItemQualityAndEnchantments()
    test.setup_method()
    test.test_roll_quality()
    test.test_enchant_count_by_quality()
    test.test_create_item_with_quality()
    test.test_serialization_roundtrip()
    test.test_inventory_equipment_stat_bonuses()
    test.test_random_item_generator_shortcut()
    print("All Phase 1 unit & integration tests PASSED!")

