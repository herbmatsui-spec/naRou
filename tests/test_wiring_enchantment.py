"""改善案6 機能4: エンチャントのアイテム生成への組み込み配線テスト。

配線対象:
- item_system.create_sample_item が装備品カテゴリでエンチャントを抽選する
  (ItemGenerator と同じ品質カーブ・控えめな初期値)。
- Inventory.get_stat_bonuses / get_weapon_element_damages が
  旧形式 (文字列) の enchants でクラッシュしない。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import item_generator
from data.generated.item.enchantment import ItemEnchantmentInstance
from item_system import Inventory, Item, create_sample_item


class _ForcedRollRandom:
    """item_generator 内の random を決定化するスタブ。

    random() は常に 0.0 (NORMAL 品質なら必ず 1 個付与)、
    sample() は先頭 k 件、randint() は常に下限を返す。
    """

    def random(self) -> float:
        return 0.0

    def randint(self, a: int, b: int) -> int:
        return a

    def sample(self, population, k: int):
        return list(population)[:k]


@pytest.fixture
def forced_roll(monkeypatch):
    """item_generator の乱数を決定化し、テスト後に復元する。"""
    original = item_generator.random
    monkeypatch.setattr(item_generator, "random", _ForcedRollRandom())
    yield


def test_create_sample_item_equipment_rolls_enchantments(forced_roll):
    """装備品カテゴリのサンプルアイテム生成でエンチャントが付与される。"""
    item = create_sample_item("longsword")
    assert isinstance(item, Item)
    assert item.category == "weapon"
    assert len(item.enchantments) == 1
    ench = item.enchantments[0]
    assert isinstance(ench, ItemEnchantmentInstance)
    assert ench.id


def test_create_sample_item_fallback_preset_rolls_enchantments(forced_roll):
    """YAML 未登録名 (フォールバックプリセット) でも装備品ならエンチャントが付く。"""
    item = create_sample_item("shield")
    assert item.category == "shield"
    assert len(item.enchantments) == 1
    assert isinstance(item.enchantments[0], ItemEnchantmentInstance)


def test_create_sample_item_non_equipment_never_enchanted(forced_roll):
    """非装備カテゴリ (potion/food) にはエンチャントが付かない。"""
    potion = create_sample_item("potion_heal")
    assert potion.enchantments == []
    food = create_sample_item("bread")
    assert food.enchantments == []


def test_get_stat_bonuses_tolerates_legacy_string_enchants():
    """旧セーブの文字列 enchants を持つ Item でも集計がクラッシュしない。"""
    inv = Inventory()
    item = Item("旧い剣", "weapon", "🗡️", (200, 200, 200))
    item.enchants = ("ench_str",)  # 旧形式: 文字列
    inv.slots[0].item = item
    assert inv.get_stat_bonuses() == {}


def test_get_stat_bonuses_aggregates_instances():
    """インスタンス形式の enchants は従来どおり集計される。"""
    inv = Inventory()
    item = Item("剛力の剣", "weapon", "🗡️", (200, 200, 200))
    item.enchantments = [
        ItemEnchantmentInstance(
            id="ench_str", name="剛力", type="stat_bonus", target_stat="strength", power=5
        )
    ]
    inv.slots[0].item = item
    assert inv.get_stat_bonuses() == {"strength": 5}


def test_get_weapon_element_damages_tolerates_legacy_string_enchants():
    """旧セーブの文字列 enchants を持つ武器でも属性ダメージ取得がクラッシュしない。"""
    inv = Inventory()
    weapon = Item("旧い剣", "weapon", "🗡️", (200, 200, 200))
    weapon.enchants = ("ench_fire_dmg",)  # 旧形式: 文字列
    inv.slots[0].item = weapon
    assert inv.get_weapon_element_damages() == []
