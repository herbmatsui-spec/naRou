"""Unit tests for Crafting and Salvage System (Phase 4, Steps 1-24)"""

import pytest
from naRou.data_manager import DataManager
from naRou.ecs.entity import Entity

from crafting_engine import CraftingSystem
from item_system import Inventory, Item


def test_crafting_system_initialization():
    dm = DataManager()
    cs = CraftingSystem(dm)
    assert len(dm.recipes.get_all()) >= 6


def test_salvage_item():
    dm = DataManager()
    cs = CraftingSystem(dm)

    entity = Entity(name="Player")
    entity.inventory = Inventory(max_items=20, max_weight=100.0)

    # 刀 (steel ingot x 2) をインベントリに追加
    katana_def = dm.items.get("katana")
    assert katana_def is not None
    katana = cs.item_generator.generate_item_from_definition(katana_def)
    entity.inventory.add_item(katana)

    assert len(entity.inventory.items) == 1

    # 分解実行
    success, mats, msg = cs.salvage_item(entity, katana)
    assert success is True
    assert len(mats) >= 1
    assert "刀 を分解し" in msg
    assert any(m["mat_id"] == "item_steel_ingot" and m["count"] == 2 for m in mats)

    # 元のアイテムが消え、素材が入っていること
    assert not any(i.name == "刀" for i in entity.inventory.items)
    steel_items = [i for i in entity.inventory.items if getattr(i, "item_id", "") == "item_steel_ingot"]
    assert len(steel_items) == 1
    assert steel_items[0].count == 2


def test_can_craft_and_craft_item():
    dm = DataManager()
    cs = CraftingSystem(dm)

    entity = Entity(name="Player")
    entity.inventory = Inventory(max_items=20, max_weight=100.0)

    # 素材なしの状態ではクラフト不可
    can, reason, missing = cs.can_craft(entity, "recipe_shortsword")
    assert can is False
    assert "item_iron_ingot" in missing

    # 鉄インゴットを1つ付与
    iron_def = dm.items.get("item_iron_ingot")
    iron_item = cs.item_generator.generate_item_from_definition(iron_def)
    iron_item.count = 1
    entity.inventory.add_item(iron_item)

    # クラフト可能になる
    can, reason, _ = cs.can_craft(entity, "recipe_shortsword")
    assert can is True

    # クラフト実行
    success, crafted_item, msg = cs.craft_item(entity, "recipe_shortsword")
    assert success is True
    assert crafted_item is not None
    assert crafted_item.name == "短剣"
    assert "短剣 を製作しました" in msg

    # 鉄インゴットが消費されていること
    assert not any(getattr(i, "item_id", "") == "item_iron_ingot" for i in entity.inventory.items)
    # 短剣が手に入っていること
    assert any(i.name == "短剣" for i in entity.inventory.items)


def test_salvage_locked_item_prevention():
    dm = DataManager()
    cs = CraftingSystem(dm)

    entity = Entity(name="Player")
    entity.inventory = Inventory(max_items=20, max_weight=100.0)

    longsword_def = dm.items.get("longsword")
    sword = cs.item_generator.generate_item_from_definition(longsword_def)
    sword.locked = True
    entity.inventory.add_item(sword)

    success, mats, msg = cs.salvage_item(entity, sword)
    assert success is False
    assert "ロック保護" in msg
    # アイテムは消えていないこと
    assert len(entity.inventory.items) == 1
