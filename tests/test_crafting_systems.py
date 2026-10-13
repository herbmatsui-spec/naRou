"""Partial-coverage tests for crafting systems.

Modules covered:
- crafting_engine.py  : CraftingSystem craft attempts, success/failure,
                        material consumption, salvage, recipe status
- crafting_system.py  : ResourceNode harvesting, try_craft recipes
- item_generator.py   : ItemGenerator with seeded/pinned RNG
- item_renderer.py    : char/text rendering with mocked display dependencies

The DataManager dependency is replaced by an in-memory fake so no disk data
is loaded and results are deterministic.
"""

from __future__ import annotations

import random
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import crafting_engine
import crafting_system
import item_generator as igen_module
from constants import (
    CAT_FOOD,
    CAT_ORE,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from crafting_engine import CraftingSystem
from crafting_system import (
    CRAFTING_RECIPES as SIMPLE_RECIPES,
)
from crafting_system import (
    Recipe as SimpleRecipe,
)
from crafting_system import (
    ResourceNode as HarvestNode,
)
from crafting_system import (
    try_craft as simple_try_craft,
)
from data.generated.item.enchantment import EnchantmentDefinition
from data.generated.item.item import ItemCategory, ItemDefinition
from data.generated.item.recipe import RecipeDefinition
from item_renderer import ItemRenderer
from item_system import Inventory, Item
from ui_fx_systems import LightSource

# ============================================================================
# Fakes and helpers
# ============================================================================


class FakeRepository:
    def __init__(self, data: dict):
        self._data = dict(data)

    def get(self, key):
        return self._data.get(key)

    def get_all(self):
        return list(self._data.values())

    def get_by_category(self, category: str):
        return [
            d
            for d in self._data.values()
            if (d.category.value if hasattr(d.category, "value") else str(d.category)) == category
        ]


class FakeEnchantmentRepository:
    def __init__(self, by_category: dict):
        self._by_category = by_category

    def get_for_category(self, category: str):
        return list(self._by_category.get(category, []))


class FakeDataManager:
    def __init__(self, items=None, recipes=None, enchantments=None):
        self.items = FakeRepository(items or {})
        self.recipes = FakeRepository(recipes or {})
        self.enchantments = FakeEnchantmentRepository(enchantments or {})


class PinnedRng:
    """Deterministic stand-in for the `random` module with pinned values."""

    def __init__(self, random_value: float = 0.5, randint_value: int | None = None):
        self.random_value = random_value
        self.randint_value = randint_value

    def random(self) -> float:
        return self.random_value

    def randint(self, a: int, b: int) -> int:
        return self.randint_value if self.randint_value is not None else a

    def sample(self, seq, k):
        return list(seq)[:k]


def make_item_def(key, name, category="ore", material="iron", salvage_materials=None,
                  hit_bonus=0, dmg_bonus=0, pv=0, dv=0, base_value=10, base_weight=1.0):
    definition = ItemDefinition(
        name=name,
        category=ItemCategory(category),
        char="?",
        color=[200, 200, 200],
        base_weight=base_weight,
        base_value=base_value,
        material=material,
        salvage_materials=salvage_materials or {},
        hit_bonus=hit_bonus,
        dmg_bonus=dmg_bonus,
        pv=pv,
        dv=dv,
    )
    return key, definition


def make_recipe(recipe_id, name, result_item_id, materials, result_count=1, difficulty=10,
                category="weapon"):
    definition = RecipeDefinition(
        id=recipe_id,
        name=name,
        result_item_id=result_item_id,
        result_count=result_count,
        category=category,
        required_materials=materials,
        difficulty=difficulty,
    )
    return recipe_id, definition


def make_ench(ench_id, name, ench_type, target_stat=None, power_range=(1, 5),
              min_quality="normal", element=None):
    return EnchantmentDefinition(
        id=ench_id,
        name=name,
        type=ench_type,
        target_stat=target_stat,
        power_range=list(power_range),
        min_quality=min_quality,
        element=element,
    )


def iron_ingots(count=1, quality=QUALITY_NORMAL):
    item = Item("鉄インゴット", "ore", "🧱", (180, 180, 180), base_weight=1.0, base_value=20,
                count=count, quality=quality)
    item.item_id = "item_iron_ingot"
    return item


def make_entity_with_inventory(*items, max_items=20, max_weight=100.0):
    inv = Inventory(max_items=max_items, max_weight=max_weight)
    for it in items:
        inv.add_item(it)
    return SimpleNamespace(inventory=inv, x=0, y=0)


def make_gen_manager():
    items = dict([
        make_item_def("item_test_sword", "テスト剣", category="weapon", hit_bonus=1, dmg_bonus=2,
                      pv=3, dv=4, material="iron"),
        make_item_def("item_test_potion", "テスト薬", category="potion"),
        make_item_def("item_iron_ingot", "鉄インゴット", category="ore"),
        make_item_def("longsword", "長剣", category="weapon"),
    ])
    return FakeDataManager(items=items)


def gen_with_sword():
    manager = make_gen_manager()
    return igen_module.ItemGenerator(manager), manager


# ============================================================================
# crafting_engine.py - inventory counts
# ============================================================================


class TestCraftingInventoryCounts:
    def test_counts_by_item_id_and_name_alias(self):
        entity = make_entity_with_inventory(iron_ingots(3))
        cs = CraftingSystem(FakeDataManager())
        counts = cs.get_inventory_material_counts(entity)
        assert counts["item_iron_ingot"] == 3
        assert counts["鉄インゴット"] == 3

    def test_empty_and_missing_inventory(self):
        cs = CraftingSystem(FakeDataManager())
        assert cs.get_inventory_material_counts(SimpleNamespace()) == {}
        assert cs.get_inventory_material_counts(SimpleNamespace(inventory=None)) == {}


# ============================================================================
# crafting_engine.py - craft attempts / success / failure
# ============================================================================


class TestCraftingAttempts:
    def base_setup(self) -> CraftingSystem:
        items = dict([
            make_item_def("item_iron_ingot", "鉄インゴット", category="ore"),
            make_item_def("item_test_sword", "テスト剣", category="weapon", hit_bonus=1,
                          dmg_bonus=2, pv=1, dv=1),
        ])
        recipes = dict([
            make_recipe("recipe_test_sword", "テスト剣の製作", "item_test_sword",
                        {"item_iron_ingot": 2}, result_count=1, difficulty=10),
        ])
        return CraftingSystem(FakeDataManager(items=items, recipes=recipes))

    def test_can_craft_unknown_recipe(self):
        cs = self.base_setup()
        entity = make_entity_with_inventory(iron_ingots(2))
        ok, reason, missing = cs.can_craft(entity, "recipe_ghost")
        assert ok is False
        assert missing == {}
        assert "レシピ" in reason

    def test_can_craft_detects_missing_materials(self):
        cs = self.base_setup()
        entity = make_entity_with_inventory(iron_ingots(1))
        ok, reason, missing = cs.can_craft(entity, "recipe_test_sword")
        assert ok is False
        assert missing == {"item_iron_ingot": 1}
        assert "素材が不足" in reason

    def test_can_craft_success(self):
        cs = self.base_setup()
        entity = make_entity_with_inventory(iron_ingots(2))
        ok, reason, missing = cs.can_craft(entity, "recipe_test_sword")
        assert ok is True
        assert missing == {}

    def test_craft_failure_consumes_nothing(self):
        cs = self.base_setup()
        entity = make_entity_with_inventory(iron_ingots(1))
        ok, item, msg = cs.craft_item(entity, "recipe_test_sword")
        assert ok is False
        assert item is None
        assert "素材が不足" in msg
        assert sum(i.count for i in entity.inventory.items) == 1

    def test_craft_success_consumes_materials_and_adds_result(self, monkeypatch):
        cs = self.base_setup()
        monkeypatch.setattr(crafting_engine, "random", PinnedRng(random_value=0.9))
        # 単独スタックは remove_item 既定 count=1 の影響を受けるため 1 個ずつ支給
        entity = make_entity_with_inventory(
            iron_ingots(1, quality=QUALITY_NORMAL), iron_ingots(1, quality=QUALITY_GOOD)
        )
        ok, crafted, msg = cs.craft_item(entity, "recipe_test_sword")
        assert ok is True
        assert crafted is not None
        assert crafted.name == "テスト剣"
        assert crafted.count == 1
        assert crafted.quality == QUALITY_NORMAL
        assert "製作しました" in msg
        assert not any(getattr(i, "item_id", "") == "item_iron_ingot" for i in entity.inventory.items)
        assert any(i.name == "テスト剣" for i in entity.inventory.items)

    def test_craft_crit_roll_grants_miracle_quality(self, monkeypatch):
        cs = self.base_setup()
        monkeypatch.setattr(crafting_engine, "random", PinnedRng(random_value=0.0))
        entity = make_entity_with_inventory(iron_ingots(2))
        ok, crafted, _ = cs.craft_item(entity, "recipe_test_sword")
        assert ok is True
        assert crafted.quality == QUALITY_MIRACLE

    def test_craft_mid_roll_grants_good_quality(self, monkeypatch):
        cs = self.base_setup()
        monkeypatch.setattr(crafting_engine, "random", PinnedRng(random_value=0.06))
        entity = make_entity_with_inventory(iron_ingots(2))
        ok, crafted, _ = cs.craft_item(entity, "recipe_test_sword")
        assert ok is True
        assert crafted.quality == QUALITY_GOOD

    def test_craft_missing_result_definition(self):
        items = dict([make_item_def("item_iron_ingot", "鉄インゴット", category="ore")])
        recipes = dict([make_recipe("r", "何か", "item_ghost_result", {"item_iron_ingot": 1})])
        cs = CraftingSystem(FakeDataManager(items=items, recipes=recipes))
        entity = make_entity_with_inventory(iron_ingots(1))
        ok, item, msg = cs.craft_item(entity, "r")
        assert ok is False
        assert item is None
        assert "完成品アイテム" in msg
        # 素材は結果定義チェックの前に消費される（現在の仕様）
        assert entity.inventory.items == []


class TestMaterialConsumption:
    def test_consume_across_partial_stacks(self):
        cs = CraftingSystem(FakeDataManager())
        s1 = iron_ingots(1, quality=QUALITY_NORMAL)
        s2 = iron_ingots(3, quality=QUALITY_GOOD)  # 品質違いでスタック分離
        entity = make_entity_with_inventory(s1, s2)
        cs._consume_material(entity, "item_iron_ingot", 2)
        remaining = [i for i in entity.inventory.items
                     if getattr(i, "item_id", "") == "item_iron_ingot"]
        assert len(remaining) == 1
        assert remaining[0].count == 2

    def test_consume_full_multi_count_stack_leaves_one(self):
        # 現行仕様: Inventory.remove_item の既定 count=1 のため、
        # 複数個スタックの全消費時も 1 個残る
        cs = CraftingSystem(FakeDataManager())
        entity = make_entity_with_inventory(iron_ingots(2))
        cs._consume_material(entity, "item_iron_ingot", 10)
        remaining = [i for i in entity.inventory.items
                     if getattr(i, "item_id", "") == "item_iron_ingot"]
        assert len(remaining) == 1
        assert remaining[0].count == 1


# ============================================================================
# crafting_engine.py - salvage
# ============================================================================


class TestSalvage:
    def test_salvage_uses_definition_salvage_materials(self):
        items = dict([
            make_item_def("item_gold_ingot", "金インゴット", category="ore"),
            make_item_def("item_test_amulet", "テストアミュレット", category="tool",
                          salvage_materials={"item_gold_ingot": 2}),
        ])
        cs = CraftingSystem(FakeDataManager(items=items))
        amulet = Item("テストアミュレット", "misc", "?", (255, 215, 0), count=1)
        amulet.item_id = "item_test_amulet"
        entity = make_entity_with_inventory(amulet)

        ok, mats, msg = cs.salvage_item(entity, amulet)
        assert ok is True
        assert mats == [{"mat_id": "item_gold_ingot", "name": "金インゴット", "count": 2}]
        assert "分解" in msg
        assert not any(i.name == "テストアミュレット" for i in entity.inventory.items)
        gold = [i for i in entity.inventory.items
                if getattr(i, "item_id", "") == "item_gold_ingot"]
        assert len(gold) == 1 and gold[0].count == 2

    def test_salvage_fallback_material_rules(self):
        cs = CraftingSystem(FakeDataManager())
        sword = Item("鋼の剣", "weapon", ")", (200, 200, 200), material="steel")
        entity = make_entity_with_inventory(sword)
        ok, mats, msg = cs.salvage_item(entity, sword)
        assert ok is True
        assert mats[0]["mat_id"] == "item_steel_ingot"
        assert mats[0]["count"] == 2
        assert "鋼の剣 を分解し" in msg

    def test_salvage_decrements_stack_before_removal(self):
        cs = CraftingSystem(FakeDataManager())
        herbs = Item("ハーブ", "food", "%", (150, 220, 120), count=3, material="cloth")
        entity = make_entity_with_inventory(herbs)
        ok, mats, _ = cs.salvage_item(entity, herbs)
        assert ok is True
        assert herbs.count == 2
        assert any(getattr(i, "item_id", "") == "item_cloth" for i in entity.inventory.items)
        assert any(i.name == "ハーブ" for i in entity.inventory.items)

    def test_salvage_equipped_item_prevented(self):
        cs = CraftingSystem(FakeDataManager())
        sword = Item("装備中の剣", "weapon", ")", (200, 200, 200))
        inv = MagicMock()
        inv.is_equipped.return_value = True
        inv.items = [sword]
        entity = SimpleNamespace(inventory=inv)
        ok, mats, msg = cs.salvage_item(entity, sword)
        assert ok is False
        assert "装備中" in msg
        inv.remove_item.assert_not_called()

    def test_salvage_locked_item_prevented(self):
        cs = CraftingSystem(FakeDataManager())
        sword = Item("愛用の剣", "weapon", ")", (200, 200, 200), locked=True)
        entity = make_entity_with_inventory(sword)
        ok, mats, msg = cs.salvage_item(entity, sword)
        assert ok is False
        assert "ロック保護" in msg
        assert len(entity.inventory.items) == 1

    def test_salvage_none_item(self):
        cs = CraftingSystem(FakeDataManager())
        ok, mats, msg = cs.salvage_item(make_entity_with_inventory(), None)
        assert ok is False
        assert mats == []
        assert "指定されていません" in msg


# ============================================================================
# crafting_engine.py - recipe status and resource nodes
# ============================================================================


class TestRecipeStatus:
    def test_get_recipes_status_structure(self):
        items = dict([
            make_item_def("item_iron_ingot", "鉄インゴット", category="ore"),
            make_item_def("item_test_sword", "テスト剣", category="weapon"),
        ])
        recipes = dict([
            make_recipe("r_ok", "作れる剣", "item_test_sword", {"item_iron_ingot": 1}),
            make_recipe("r_ng", "作れない剣", "item_test_sword", {"item_iron_ingot": 5}),
            make_recipe("r_ghost", "幻の剣", "item_ghost_result", {"item_iron_ingot": 0}),
        ])
        cs = CraftingSystem(FakeDataManager(items=items, recipes=recipes))
        entity = make_entity_with_inventory(iron_ingots(2))
        status = cs.get_recipes_status(entity)
        by_id = {s["id"]: s for s in status}
        assert by_id["r_ok"]["can_craft"] is True
        assert by_id["r_ng"]["can_craft"] is False
        assert by_id["r_ok"]["result_name"] == "テスト剣"
        assert by_id["r_ghost"]["result_name"] == "item_ghost_result"  # 未定義IDはそのまま
        mats = by_id["r_ng"]["materials"][0]
        assert mats == {"mat_id": "item_iron_ingot", "name": "鉄インゴット", "required": 5,
                        "current": 2, "satisfied": False}


class TestEngineResourceNode:
    def test_herb_harvest_depletes(self):
        node = crafting_engine.ResourceNode(x=1, y=2, node_type="herb", remaining_resources=2)
        assert node.harvest() == "item_herb"
        assert node.harvest() == "item_herb"
        assert node.remaining_resources == 0
        assert node.harvest() is None

    def test_ore_vein_yields_ingot(self):
        node = crafting_engine.ResourceNode(x=0, y=0, node_type="ore_vein")
        assert node.harvest() == "item_iron_ingot"


# ============================================================================
# crafting_system.py - harvesting and try_craft
# ============================================================================


def make_herbs(count=1, quality=QUALITY_NORMAL):
    return Item("ハーブ", CAT_FOOD, "%", (150, 220, 120), count=count, quality=quality)


class TestHarvestNode:
    def test_harvest_deterministic_first_drop(self, monkeypatch):
        monkeypatch.setattr(crafting_system, "random", PinnedRng(random_value=0.0))
        player = MagicMock()
        node = HarvestNode(x=3, y=4, node_type="herb")
        item, msg = node.harvest(player)
        assert item is not None
        assert item.name == "ハーブ"
        assert item.category == CAT_FOOD
        assert "採取した" in msg and "ハーブ" in msg
        player.gain_skill_exp.assert_called_once_with("farming", 20)
        assert node.depleted is True

    def test_harvest_depleted_returns_none(self):
        player = MagicMock()
        node = HarvestNode(x=0, y=0, node_type="herb", depleted=True)
        item, msg = node.harvest(player)
        assert item is None
        assert msg == "もう何もない。"
        player.gain_skill_exp.assert_not_called()

    def test_harvest_ore_uses_ore_category(self, monkeypatch):
        monkeypatch.setattr(crafting_system, "random", PinnedRng(random_value=0.0))
        player = MagicMock()
        node = HarvestNode(x=0, y=0, node_type="ore_vein")
        item, _ = node.harvest(player)
        assert item is not None
        assert item.category == CAT_ORE
        assert item.name == "鉄鉱石"


class TestSimpleTryCraft:
    RECIPE = SimpleRecipe(
        result_name="ハーブ弁当",
        result_category="food",
        required_materials={"ハーブ": 2, "旅糧": 1},
        required_skill="cooking",
        required_skill_level=2,
    )

    @staticmethod
    def make_player(cooking_level=5):
        return SimpleNamespace(
            skills={"cooking": SimpleNamespace(level=cooking_level)},
            gain_skill_exp=MagicMock(),
        )

    @staticmethod
    def make_inventory():
        inv = Inventory()
        inv.add_item(make_herbs(2))
        inv.add_item(Item("旅糧", CAT_FOOD, "%", (200, 180, 100)))
        return inv

    def test_insufficient_materials(self):
        player = self.make_player()
        inv = Inventory()
        inv.add_item(make_herbs(2))
        ok, msg, item = simple_try_craft(self.RECIPE, player, inv)
        assert ok is False
        assert item is None
        assert "素材が足りない" in msg and "旅糧" in msg

    def test_insufficient_skill_level(self):
        player = self.make_player(cooking_level=1)
        ok, msg, item = simple_try_craft(self.RECIPE, player, self.make_inventory())
        assert ok is False
        assert item is None
        assert "スキル【cooking】Lv2" in msg

    def test_success_consumes_materials_and_normal_quality(self, monkeypatch):
        monkeypatch.setattr(crafting_system, "random", PinnedRng(randint_value=0))
        player = self.make_player(cooking_level=2)  # surplus 0 → roll 0 → normal
        inv = self.make_inventory()
        ok, msg, item = simple_try_craft(self.RECIPE, player, inv)
        assert ok is True
        assert item is not None
        assert item.name == "ハーブ弁当"
        assert item.quality == QUALITY_NORMAL
        assert item.heal_amount == 35
        assert item.nutrition == 2000
        assert "ハーブ弁当" in msg
        assert not any(i.name == "ハーブ" for i in inv.items)
        assert not any(i.name == "旅糧" for i in inv.items)
        player.gain_skill_exp.assert_called_once_with("cooking", 30)

    def test_surplus_skill_grants_miracle_quality(self, monkeypatch):
        monkeypatch.setattr(crafting_system, "random", PinnedRng(randint_value=10))
        player = self.make_player(cooking_level=8)  # surplus 6 → roll 16 >= 15
        ok, _, item = simple_try_craft(self.RECIPE, player, self.make_inventory())
        assert ok is True
        assert item is not None
        assert item.quality == QUALITY_MIRACLE

    def test_partial_stack_consumption(self, monkeypatch):
        monkeypatch.setattr(crafting_system, "random", PinnedRng(randint_value=0))
        player = self.make_player(cooking_level=2)
        inv = Inventory()
        inv.add_item(make_herbs(1, quality=QUALITY_NORMAL))
        inv.add_item(make_herbs(2, quality=QUALITY_GOOD))
        inv.add_item(Item("旅糧", CAT_FOOD, "%", (200, 180, 100)))
        ok, _, item = simple_try_craft(self.RECIPE, player, inv)
        assert ok is True
        herbs = [i for i in inv.items if i.name == "ハーブ"]
        assert len(herbs) == 1
        assert herbs[0].count == 1  # normal x1 を全消費 → good x2 から 1 消費


class TestBuiltinSimpleRecipes:
    def test_builtin_recipes_defined(self):
        assert "basic_potion" in SIMPLE_RECIPES
        potion = SIMPLE_RECIPES["basic_potion"]
        assert potion.required_materials == {"高級ハーブ": 2}
        assert potion.required_skill == "cooking"
        assert "herb_food" in SIMPLE_RECIPES
        food = SIMPLE_RECIPES["herb_food"]
        assert food.required_materials == {"ハーブ": 3, "旅糧": 1}


# ============================================================================
# item_generator.py - quality and enchantment rolls
# ============================================================================

ALL_QUALITY_VALUES = {QUALITY_BAD, QUALITY_NORMAL, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD}


class TestItemGeneratorQuality:
    def test_roll_quality_seeded_is_deterministic(self, monkeypatch):
        gen, _ = gen_with_sword()
        monkeypatch.setattr(igen_module, "random", random.Random(1234))
        first = gen.roll_quality(dungeon_level=30, luck_bonus=1.0)
        monkeypatch.setattr(igen_module, "random", random.Random(1234))
        second = gen.roll_quality(dungeon_level=30, luck_bonus=1.0)
        assert first == second
        assert first in ALL_QUALITY_VALUES

    def test_roll_quality_valid_for_various_depths(self, monkeypatch):
        gen, _ = gen_with_sword()
        monkeypatch.setattr(igen_module, "random", random.Random(7))
        for depth in (1, 10, 50):
            assert gen.roll_quality(depth) in ALL_QUALITY_VALUES

    def test_enchant_count_by_quality(self, monkeypatch):
        gen, _ = gen_with_sword()
        assert gen.get_enchant_count(QUALITY_BAD) == 0
        monkeypatch.setattr(igen_module, "random", PinnedRng(random_value=0.05))
        assert gen.get_enchant_count(QUALITY_NORMAL) == 1
        monkeypatch.setattr(igen_module, "random", PinnedRng(random_value=0.95))
        assert gen.get_enchant_count(QUALITY_NORMAL) == 0
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=2))
        assert gen.get_enchant_count(QUALITY_GOOD) == 2
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=3))
        assert gen.get_enchant_count(QUALITY_MIRACLE) == 3
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=5))
        assert gen.get_enchant_count(QUALITY_GOD) == 5


class TestItemGeneratorEnchantments:
    @staticmethod
    def make_gen(enchantments):
        items = dict([make_item_def("x", "x")])
        return igen_module.ItemGenerator(FakeDataManager(items=items, enchantments=enchantments))

    def test_selection_respects_count_and_power_range(self, monkeypatch):
        ench = make_ench("ench_pv", "剛力の刻印", "combat_bonus", target_stat="pv",
                         power_range=(2, 5))
        gen = self.make_gen({"weapon": [ench]})
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=4))
        instances = gen.generate_enchantments_for_item("weapon", QUALITY_GOOD, count=2)
        # 候補1件なので重複なしで1件のみ
        assert len(instances) == 1
        inst = instances[0]
        assert inst.id == "ench_pv"
        assert inst.power == 4  # pinned randint(2,5)=4、good はブーストなし
        assert inst.target_stat == "pv"

    def test_quality_filter_excludes_high_min_quality(self, monkeypatch):
        low = make_ench("ench_low", "低級", "combat_bonus", target_stat="pv",
                        power_range=(1, 2), min_quality="normal")
        high = make_ench("ench_high", "神級", "stat_bonus", target_stat="strength",
                         power_range=(1, 2), min_quality="god")
        gen = self.make_gen({"weapon": [low, high]})
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=1))
        instances = gen.generate_enchantments_for_item("weapon", QUALITY_NORMAL, count=2)
        assert [i.id for i in instances] == ["ench_low"]

    def test_fallback_when_no_candidate_passes_filter(self, monkeypatch):
        high = make_ench("ench_high", "神級", "stat_bonus", target_stat="strength",
                         power_range=(1, 2), min_quality="god")
        gen = self.make_gen({"weapon": [high]})
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=1))
        instances = gen.generate_enchantments_for_item("weapon", QUALITY_NORMAL, count=1)
        assert [i.id for i in instances] == ["ench_high"]

    def test_empty_results(self):
        gen = self.make_gen({})
        assert gen.generate_enchantments_for_item("weapon", QUALITY_GOOD, count=2) == []
        gen2 = self.make_gen({"weapon": [make_ench("e", "e", "combat_bonus")]})
        assert gen2.generate_enchantments_for_item("weapon", QUALITY_GOOD, count=0) == []


# ============================================================================
# item_generator.py - item creation
# ============================================================================


class TestItemGeneratorCreateItem:
    def test_quality_bonuses_good(self):
        gen, _ = gen_with_sword()
        item = gen.create_item("item_test_sword", quality=QUALITY_GOOD)
        assert (item.hit_bonus, item.dmg_bonus, item.pv, item.dv) == (2, 3, 4, 4)
        assert item.item_id == "item_test_sword"
        assert item.name == "テスト剣"
        assert item.identified is True
        assert item.count == 1
        assert item.material == "iron"

    def test_quality_bonuses_god(self):
        gen, _ = gen_with_sword()
        item = gen.create_item("item_test_sword", quality=QUALITY_GOD)
        assert (item.hit_bonus, item.dmg_bonus, item.pv, item.dv) == (5, 6, 8, 6)

    def test_quality_bonuses_bad_without_curse(self, monkeypatch):
        gen, _ = gen_with_sword()
        monkeypatch.setattr(igen_module, "random", PinnedRng(random_value=0.9))
        item = gen.create_item("item_test_sword", quality=QUALITY_BAD)
        assert (item.hit_bonus, item.dmg_bonus, item.pv, item.dv) == (0, 1, 2, 4)
        assert item.cursed is False

    def test_bad_quality_can_be_cursed(self, monkeypatch):
        gen, _ = gen_with_sword()
        monkeypatch.setattr(igen_module, "random", PinnedRng(random_value=0.1))
        item = gen.create_item("item_test_sword", quality=QUALITY_BAD)
        assert item.cursed is True

    def test_enchant_combat_bonus_applied_to_stats(self, monkeypatch):
        manager = make_gen_manager()
        manager.enchantments = FakeEnchantmentRepository({
            "weapon": [
                make_ench("ench_pv", "剛力の刻印", "combat_bonus", target_stat="pv",
                          power_range=(3, 3), min_quality="normal")
            ]
        })
        gen = igen_module.ItemGenerator(manager)
        monkeypatch.setattr(igen_module, "random", PinnedRng(randint_value=3))
        item = gen.create_item("item_test_sword", quality=QUALITY_MIRACLE)
        # 品質補正 pv+2、エンチャント power 3 → miracle ブーストで 4
        assert item.pv == 3 + 2 + 4
        assert len(item.enchants) == 1
        assert item.enchants[0].power == 4

    def test_non_equip_category_skips_enchantments(self):
        manager = make_gen_manager()
        manager.enchantments = MagicMock()
        gen = igen_module.ItemGenerator(manager)
        item = gen.create_item("item_test_potion", quality=QUALITY_NORMAL)
        manager.enchantments.get_for_category.assert_not_called()
        assert item.category == "potion"
        assert item.enchants == ()

    def test_unknown_template_raises(self):
        gen, _ = gen_with_sword()
        with pytest.raises(KeyError):
            gen.create_item("item_ghost", quality=QUALITY_NORMAL)

    def test_material_override(self):
        gen, _ = gen_with_sword()
        item = gen.create_item("item_test_sword", quality=QUALITY_NORMAL, material="mythril")
        assert item.material == "mythril"


class TestItemGeneratorFromDefinition:
    def test_resolves_key_from_manager(self):
        gen, manager = gen_with_sword()
        item_def = manager.items.get("item_test_sword")
        item = gen.generate_item_from_definition(item_def, quality=QUALITY_NORMAL)
        assert item.item_id == "item_test_sword"

    def test_resolves_by_name_when_id_missing(self):
        gen, _ = gen_with_sword()
        clone = ItemDefinition(name="テスト剣", category=ItemCategory.weapon, color=[1, 2, 3])
        item = gen.generate_item_from_definition(clone, quality=QUALITY_NORMAL)
        assert item.item_id == "item_test_sword"

    def test_falls_back_to_longsword_key(self):
        gen, _ = gen_with_sword()
        stranger = ItemDefinition(name="異物", category=ItemCategory.tool)
        item = gen.generate_item_from_definition(stranger, quality=QUALITY_NORMAL)
        assert item.item_id == "longsword"


class TestItemGeneratorRandom:
    def test_category_filter(self, monkeypatch):
        gen, _ = gen_with_sword()
        monkeypatch.setattr(igen_module, "random", random.Random(0))
        item = gen.generate_random_item(dungeon_level=1, category="potion")
        assert item.name == "テスト薬"
        assert item.category == "potion"

    def test_random_from_all_items(self, monkeypatch):
        gen, _ = gen_with_sword()
        monkeypatch.setattr(igen_module, "random", random.Random(0))
        item = gen.generate_random_item()
        assert item.name in {"テスト剣", "テスト薬", "鉄インゴット", "長剣"}

    def test_singleton_generator(self):
        assert igen_module.get_item_generator() is igen_module.get_item_generator()


# ============================================================================
# item_renderer.py - rendering with mocked display dependencies
# ============================================================================


class FakeGameMap:
    def __init__(self, width=60, height=60):
        self.width = width
        self.height = height
        self.visible = [[True] * height for _ in range(width)]


def make_context(items, hunger=5000, frame_count=0, game_map=None):
    return SimpleNamespace(
        survival=SimpleNamespace(hunger=hunger),
        frame_count=frame_count,
        items_on_ground=items,
        game_map=game_map or FakeGameMap(),
    )


def printed_kwargs(console):
    return [call.kwargs for call in console.print.call_args_list]


class TestItemRenderer:
    @staticmethod
    def make_item(**overrides):
        params = dict(name="試験剣", category="weapon", char=")", color=(200, 200, 200),
                      x=10, y=10)
        params.update(overrides)
        return Item(**params)

    def test_renders_visible_item_char_with_silhouette(self):
        console = MagicMock()
        item = self.make_item()
        ItemRenderer.render(console, make_context([item]), cam_x=0, cam_y=0, light_sources=[])
        char_calls = [c for c in printed_kwargs(console) if c.get("string") == ")"]
        assert len(char_calls) == 1
        assert char_calls[0]["x"] == 10 and char_calls[0]["y"] == 10
        # 光源なし → intensity 0.15 < 0.25 でシルエット化
        assert char_calls[0]["fg"] == (60, 65, 80)

    def test_camera_offset_applied(self):
        console = MagicMock()
        item = self.make_item(x=15, y=12)
        ItemRenderer.render(console, make_context([item]), cam_x=5, cam_y=2, light_sources=[])
        char_calls = [c for c in printed_kwargs(console) if c.get("string") == ")"]
        assert (char_calls[0]["x"], char_calls[0]["y"]) == (10, 10)

    def test_particle_printed_on_even_tick(self):
        console = MagicMock()
        item = self.make_item()
        ItemRenderer.render(console, make_context([item], frame_count=0), 0, 0, [])
        assert any(c.get("string") == "*" and c.get("fg") == (200, 200, 200)
                   for c in printed_kwargs(console))

    def test_no_particle_on_odd_tick(self):
        console = MagicMock()
        item = self.make_item()
        ItemRenderer.render(console, make_context([item], frame_count=1), 0, 0, [])
        assert not any(c.get("string") == "*" for c in printed_kwargs(console))

    def test_starving_food_gets_gold_aura(self):
        console = MagicMock()
        item = self.make_item(name="パン", category=CAT_FOOD, char="%", color=(200, 180, 100))
        ItemRenderer.render(console, make_context([item], hunger=1000), 0, 0, [])
        char_calls = [c for c in printed_kwargs(console) if c.get("string") == "%"]
        assert char_calls
        assert char_calls[0]["fg"] == (255, 225, 60)

    def test_rare_item_gets_god_rays(self):
        console = MagicMock()
        item = self.make_item(color=(255, 215, 0), x=5, y=5)
        ItemRenderer.render(console, make_context([item], frame_count=0), 0, 0, [])
        bg_calls = [c for c in printed_kwargs(console) if "bg" in c]
        assert len(bg_calls) == 8  # 十字4方向 × 距離2
        assert all(c["bg"] == (127, 107, 0) for c in bg_calls)

    def test_offscreen_and_invisible_items_skipped(self):
        console = MagicMock()
        far = self.make_item(name="遠い", x=90, y=10)  # vx=90 >= VIEW_WIDTH(80)
        hidden = self.make_item(name="見えない", x=12, y=12)
        game_map = FakeGameMap(width=100, height=100)
        game_map.visible[12][12] = False
        ItemRenderer.render(console, make_context([far, hidden], game_map=game_map), 0, 0, [])
        assert console.print.call_args_list == []

    def test_nearby_light_source_lights_item(self):
        console = MagicMock()
        item = self.make_item(x=10, y=10)
        light = LightSource(x=10, y=10, radius=6, intensity=1.0, color=(255, 240, 200))
        ItemRenderer.render(console, make_context([item]), 0, 0, [light])
        char_calls = [c for c in printed_kwargs(console) if c.get("string") == ")"]
        assert char_calls
        assert char_calls[0]["fg"] != (60, 65, 80)
        assert len(char_calls[0]["fg"]) == 3
