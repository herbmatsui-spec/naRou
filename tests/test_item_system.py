"""Unit tests for item_system.py - Core item implementation."""

from __future__ import annotations

import random

import pytest

import item_system
from item_system import (
    CAT_ARMOR,
    CAT_FOOD,
    CAT_GOLD,
    CAT_HELM,
    CAT_ORE,
    CAT_POTION,
    CAT_RING,
    CAT_ROD,
    CAT_SCROLL,
    CAT_SHIELD,
    CAT_SPELLBOOK,
    CAT_TOOL,
    CAT_WEAPON,
    MATERIALS,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
    Affix,
    EquipmentSlot,
    Inventory,
    Item,
    _affix_roll_count,
    _apply_affix,
    calculate_reincarnation_drop_rate,
    can_identify,
    clear_affix_cache,
    create_sample_item,
    identify,
    load_affixes,
    roll_affixes,
    sell,
    use_item,
)


class TestItemInitialization:
    """Tests for Item initialization."""

    def test_basic_item_creation(self):
        """Item initializes with required attributes."""
        item = Item(
            name="Test Sword",
            category=CAT_WEAPON,
            char=")",
            color=(200, 100, 100),
            x=0, y=0,
        )

        assert item.name == "Test Sword"
        assert item.category == CAT_WEAPON
        assert item.char == ")"
        assert item.color == (200, 100, 100)
        assert item.x == 0
        assert item.y == 0

    def test_item_has_item_id(self):
        """Item has unique item_id (UUID)."""
        item1 = Item("Sword1", CAT_WEAPON, ")", (200, 100, 100), 0, 0)
        item2 = Item("Sword2", CAT_WEAPON, ")", (200, 100, 100), 0, 0)

        assert hasattr(item1, "item_id")
        assert hasattr(item2, "item_id")
        assert item1.item_id != item2.item_id

    def test_item_default_attributes(self):
        """Item has expected default attributes."""
        item = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0)

        assert item.base_weight == 1.0
        assert item.base_value == 10
        assert item.count == 1
        assert item.material == "iron"
        assert item.quality == "normal"
        assert item.identified is True
        assert item.cursed is False
        assert item.enchants == ()
        assert item.locked is False
        assert item.rot_progress == 0
        assert item.is_cooling is False

    def test_item_food_attributes(self):
        """Food items have nutrition attribute."""
        item = Item("Bread", CAT_FOOD, "%", (200, 180, 100), 0, 0, nutrition=100)

        assert item.nutrition == 100

    def test_item_weapon_attributes(self):
        """Weapon items have hit/damage bonuses."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0, hit_bonus=5, dmg_bonus=10)

        assert item.hit_bonus == 5
        assert item.dmg_bonus == 10


class TestItemCategories:
    """Tests for item category constants."""

    def test_category_constants_exist(self):
        """All category constants are defined."""
        assert CAT_WEAPON == "weapon"
        assert CAT_SHIELD == "shield"
        assert CAT_HELM == "helm"
        assert CAT_ARMOR == "armor"
        assert CAT_RING == "ring"
        assert CAT_POTION == "potion"
        assert CAT_SCROLL == "scroll"
        assert CAT_FOOD == "food"
        assert CAT_SPELLBOOK == "spellbook"
        assert CAT_TOOL == "tool"
        assert CAT_ROD == "rod"
        assert CAT_ORE == "ore"
        assert CAT_GOLD == "gold"


class TestMaterials:
    """Tests for material definitions."""

    def test_materials_defined(self):
        """MATERIALS dictionary has expected materials."""
        expected = ["wood", "iron", "steel", "mithril", "rubynus", "emerald"]
        for mat in expected:
            assert mat in MATERIALS

    def test_material_properties(self):
        """Materials have expected properties."""
        for mat_name, mat_data in MATERIALS.items():
            assert "name" in mat_data
            assert "weight_mult" in mat_data
            assert "value_mult" in mat_data
            assert "hit" in mat_data
            assert "dmg" in mat_data
            assert "pv" in mat_data
            assert "dv" in mat_data


class TestItemQuality:
    """Tests for item quality system."""

    def test_quality_constants_exist(self):
        """Quality constants are defined."""
        assert QUALITY_BAD == "bad"
        assert QUALITY_NORMAL == "normal"
        assert QUALITY_GOOD == "good"
        assert QUALITY_GOD == "god"
        assert QUALITY_MIRACLE == "miracle"

    def test_item_quality_assignment(self):
        """Item quality can be set."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)
        item.quality = QUALITY_GOOD

        assert item.quality == QUALITY_GOOD

    def test_item_enchantment(self):
        """Item enchantments can be modified."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)
        item.enchants = ("fire", "sharp")

        assert list(item.enchantments) == ["fire", "sharp"]
        assert item.enchants == ("fire", "sharp")


class TestItemCursed:
    """Tests for cursed item behavior."""

    def test_cursed_flag(self):
        """Items can be cursed."""
        item = Item("Cursed Sword", CAT_WEAPON, ")", (100, 50, 50), 0, 0)
        item.cursed = True

        assert item.cursed is True

    def test_uncursed_by_default(self):
        """Items are not cursed by default."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)

        assert item.cursed is False


class TestItemIdentified:
    """Tests for item identification."""

    def test_identified_by_default(self):
        """Items are identified by default."""
        item = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0)

        assert item.identified is True

    def test_unidentified_item(self):
        """Items can be unidentified."""
        item = Item("Mystery Potion", CAT_POTION, "!", (200, 200, 200), 0, 0)
        item.identified = False

        assert item.identified is False


class TestItemRotProgress:
    """Tests for food rot progress (replaces durability)."""

    def test_rot_progress_defaults(self):
        """Rot progress defaults to 0."""
        item = Item("Bread", CAT_FOOD, "%", (200, 180, 100), 0, 0)

        assert item.rot_progress == 0

    def test_rot_progress_modification(self):
        """Rot progress can be modified."""
        item = Item("Bread", CAT_FOOD, "%", (200, 180, 100), 0, 0)
        item.rot_progress = 2500

        assert item.rot_progress == 2500


class TestItemMaterial:
    """Tests for item material system."""

    def test_material_assignment(self):
        """Items can have materials assigned."""
        item = Item("Iron Sword", CAT_WEAPON, ")", (150, 150, 150), 0, 0)
        item.material = "iron"

        assert item.material == "iron"

    def test_material_effects(self):
        """Materials affect item properties."""
        iron = MATERIALS["iron"]
        assert iron["weight_mult"] == 1.0
        assert iron["value_mult"] == 1.0
        assert iron["dmg"] == 1
        assert iron["pv"] == 1


class TestItemStacking:
    """Tests for item stacking behavior."""

    def test_stackable_items(self):
        """Some items can stack."""
        item1 = Item("Arrow", CAT_WEAPON, "/", (200, 200, 200), 0, 0, count=10)
        item2 = Item("Arrow", CAT_WEAPON, "/", (200, 200, 200), 0, 0, count=5)

        assert item1.count == 10
        assert item2.count == 5

    def test_non_stackable_default(self):
        """Items default to count = 1."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)

        assert item.count == 1

    def test_can_stack_with(self):
        """can_stack_with checks strict conditions."""
        item1 = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, count=5)
        item2 = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, count=3)

        assert item1.can_stack_with(item2) is True

    def test_cannot_stack_different_material(self):
        """Items with different materials cannot stack."""
        item1 = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, material="iron")
        item2 = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, material="steel")

        assert item1.can_stack_with(item2) is False

    def test_cannot_stack_different_quality(self):
        """Items with different quality cannot stack."""
        item1 = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, quality="normal")
        item2 = Item("Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, quality="good")

        assert item1.can_stack_with(item2) is False


class TestItemSerialization:
    """Tests for item serialization."""

    def test_item_to_dict(self):
        """Item serializes to dict."""
        item = Item("Test Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)
        item.quality = "good"
        item.enchants = ("fire", "sharp")

        data = item.to_dict()

        assert data["name"] == "Test Sword"
        assert data["category"] == CAT_WEAPON
        assert data["quality"] == "good"
        assert data["enchants"] == ["fire", "sharp"]  # to_dict converts tuple to list
        assert "item_id" in data
        assert data["category"] == CAT_WEAPON


class TestItemComparison:
    """Tests for item comparison/equality."""

    def test_same_item_id_different_objects(self):
        """Items with same item_id are equal."""
        item1 = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)
        item2 = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0)
        # Force same item_id for testing
        item2.item_id = item1.item_id

        # Items should be comparable by item_id
        assert item1.item_id == item2.item_id

    def test_item_weight_property(self):
        """Item weight property calculates correctly."""
        item = Item("Iron Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0,
                    base_weight=3.0, material="iron")
        # iron weight_mult = 1.0
        assert item.weight == 3.0

    def test_item_value_property(self):
        """Item value property calculates correctly."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0,
                    base_value=100, material="iron", quality="normal")
        # iron value_mult = 1.0, normal quality = 1.0
        assert item.value == 100

    def test_item_display_name(self):
        """Item display_name formats correctly."""
        item = Item("Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0,
                    material="iron", base_weight=3.0)
        display = item.display_name

        assert "Sword" in display
        assert "3.0s" in display  # weight suffix


# ==================== EquipmentSlot / Inventory (item_system.py 296-520) ====================


class MockEnchant:
    """Enchant mock with type/target_stat/power/element attributes."""

    def __init__(self, ench_type, target_stat="", power=0, element=""):
        self.type = ench_type
        self.target_stat = target_stat
        self.power = power
        self.element = element


def make_item(name, category=CAT_WEAPON, char=")", color=(200, 100, 100), **kwargs):
    """Build an Item with sensible defaults."""
    return Item(name, category, char, color, 0, 0, **kwargs)


class TestEquipmentSlot:
    """Tests for EquipmentSlot (item_system.py 297-306)."""

    def test_can_equip_returns_true_when_not_disabled(self):
        slot = EquipmentSlot("main_hand", "利き手")
        assert slot.can_equip(make_item("Sword")) is True

    def test_can_equip_returns_false_when_disabled(self):
        slot = EquipmentSlot("main_hand", "利き手", disabled=True)
        assert slot.can_equip(make_item("Sword")) is False

    def test_slot_defaults(self):
        slot = EquipmentSlot("head", "頭")
        assert slot.slot_name == "head"
        assert slot.display_name == "頭"
        assert slot.item is None
        assert slot.disabled is False


class TestInventoryBasics:
    """Tests for Inventory construction and basic properties."""

    def test_init_defaults(self):
        inv = Inventory()
        assert inv.max_items == 24
        assert inv.max_weight == 50.0
        assert inv.items == []

    def test_init_custom_limits(self):
        inv = Inventory(max_items=10, max_weight=25.0)
        assert inv.max_items == 10
        assert inv.max_weight == 25.0

    def test_six_equipment_slots(self):
        inv = Inventory()
        assert [s.slot_name for s in inv.slots] == [
            "main_hand", "off_hand", "head", "body", "ring1", "ring2",
        ]
        for slot in inv.slots:
            assert slot.item is None
            assert slot.disabled is False

    def test_get_slot_by_name(self):
        inv = Inventory()
        slot = inv.get_slot("ring2")
        assert slot is not None
        assert slot.slot_name == "ring2"
        assert slot.display_name == "指(左)"

    def test_get_slot_invalid_returns_none(self):
        assert Inventory().get_slot("no_such_slot") is None

    def test_equipment_property_empty(self):
        equipment = Inventory().equipment
        assert set(equipment) == {"main_hand", "off_hand", "head", "body", "ring1", "ring2"}
        assert all(v is None for v in equipment.values())

    def test_equipment_property_with_item(self):
        inv = Inventory()
        sword = make_item("Sword")
        inv.equip(sword, "main_hand")
        assert inv.equipment["main_hand"] is sword
        assert inv.equipment["head"] is None

    def test_total_weight_sums_items(self):
        inv = Inventory()
        inv.add_item(make_item("Anvil", base_weight=2.0))
        inv.add_item(make_item("Log", base_weight=3.5))
        assert inv.total_weight == 5.5

    def test_total_weight_counts_stack_count(self):
        inv = Inventory()
        inv.add_item(make_item("Potion", CAT_POTION, "!", base_weight=0.5, count=3))
        assert inv.total_weight == 1.5

    def test_is_overburdened(self):
        inv = Inventory(max_weight=5.0)
        inv.add_item(make_item("Rock", base_weight=3.0))
        assert inv.is_overburdened() is False
        inv.add_item(make_item("Anvil", base_weight=3.0))
        assert inv.is_overburdened() is True


class TestInventoryAddRemove:
    """Tests for Inventory.add_item / remove_item."""

    def test_add_item_success(self):
        inv = Inventory()
        sword = make_item("Sword")
        ok, msg = inv.add_item(sword)
        assert ok is True
        assert "手に入れた" in msg
        assert inv.items == [sword]

    def test_add_item_stacks(self):
        inv = Inventory()
        p1 = make_item("Potion", CAT_POTION, "!", count=2)
        p2 = make_item("Potion", CAT_POTION, "!", count=3)
        inv.add_item(p1)
        ok, msg = inv.add_item(p2)
        assert ok is True
        assert "スタックした" in msg
        assert "(x5)" in msg
        assert len(inv.items) == 1
        assert p1.count == 5

    def test_add_item_full(self):
        inv = Inventory(max_items=1)
        inv.add_item(make_item("Sword"))
        ok, msg = inv.add_item(make_item("Shield", CAT_SHIELD))
        assert ok is False
        assert "荷物がいっぱい" in msg
        assert len(inv.items) == 1

    def test_remove_item_not_in_inventory_returns_none(self):
        assert Inventory().remove_item(make_item("Ghost")) is None

    def test_remove_item_removes_when_count_equals(self):
        inv = Inventory()
        item = make_item("Potion", CAT_POTION, "!", count=3)
        inv.add_item(item)
        removed = inv.remove_item(item, 3)
        assert removed is item
        assert item not in inv.items

    def test_remove_item_removes_when_count_greater(self):
        inv = Inventory()
        item = make_item("Potion", CAT_POTION, "!", count=2)
        inv.add_item(item)
        removed = inv.remove_item(item, 5)
        assert removed is item
        assert item not in inv.items

    def test_remove_item_reduces_count_returns_copy(self):
        inv = Inventory()
        item = make_item("Potion", CAT_POTION, "!", count=5)
        inv.add_item(item)
        dropped = inv.remove_item(item, 2)
        assert dropped is not item
        assert dropped.count == 2
        assert dropped.item_id != item.item_id
        assert item in inv.items
        assert item.count == 3

    def test_remove_item_auto_unequips(self):
        inv = Inventory()
        sword = make_item("Sword")
        inv.add_item(sword)
        inv.equip(sword, "main_hand")
        removed = inv.remove_item(sword)
        assert removed is sword
        assert sword not in inv.items
        assert inv.get_slot("main_hand").item is None

    def test_remove_item_cursed_equipped_fails(self):
        inv = Inventory()
        sword = make_item("Cursed Sword", cursed=True)
        inv.add_item(sword)
        inv.equip(sword, "main_hand")
        assert inv.remove_item(sword) is None
        assert sword in inv.items
        assert inv.get_slot("main_hand").item is sword


class TestInventoryEquip:
    """Tests for Inventory.equip / unequip."""

    def test_equip_to_valid_slot(self):
        inv = Inventory()
        sword = make_item("Sword")
        inv.add_item(sword)
        ok, msg = inv.equip(sword, "main_hand")
        assert ok is True
        assert "装備した" in msg
        assert inv.get_slot("main_hand").item is sword

    def test_equip_to_invalid_slot(self):
        ok, msg = Inventory().equip(make_item("Sword"), "foot")
        assert ok is False
        assert "無効なスロット" in msg

    def test_equip_to_disabled_slot(self):
        inv = Inventory()
        inv.get_slot("head").disabled = True
        ok, msg = inv.equip(make_item("Helm", CAT_HELM), "head")
        assert ok is False
        assert "使えない" in msg

    def test_equip_replaces_existing_item(self):
        inv = Inventory()
        old = make_item("Old Sword")
        new = make_item("New Sword")
        inv.add_item(old)
        inv.add_item(new)
        inv.equip(old, "main_hand")
        ok, msg = inv.equip(new, "main_hand")
        assert ok is True
        assert inv.get_slot("main_hand").item is new
        assert all(slot.item is not old for slot in inv.slots)

    def test_equip_blocked_by_cursed_existing_item(self):
        inv = Inventory()
        cursed = make_item("Cursed Sword", cursed=True)
        new = make_item("New Sword")
        inv.add_item(cursed)
        inv.add_item(new)
        inv.equip(cursed, "main_hand")
        ok, msg = inv.equip(new, "main_hand")
        assert ok is False
        assert "呪われており外せない" in msg
        assert inv.get_slot("main_hand").item is cursed

    def test_unequip_non_cursed(self):
        inv = Inventory()
        sword = make_item("Sword")
        inv.add_item(sword)
        inv.equip(sword, "main_hand")
        ok, msg = inv.unequip(sword)
        assert ok is True
        assert "外した" in msg
        assert inv.get_slot("main_hand").item is None

    def test_unequip_cursed_fails(self):
        inv = Inventory()
        sword = make_item("Cursed Sword", cursed=True)
        inv.add_item(sword)
        inv.equip(sword, "main_hand")
        ok, msg = inv.unequip(sword)
        assert ok is False
        assert "呪われており外せない" in msg
        assert inv.get_slot("main_hand").item is sword

    def test_unequip_not_equipped_fails(self):
        ok, msg = Inventory().unequip(make_item("Sword"))
        assert ok is False
        assert "装備されていない" in msg


class TestInventoryFilterSortLock:
    """Tests for filter_items / sort_items / can_sell / can_destroy / toggle_lock."""

    def make_inventory(self):
        inv = Inventory()
        self.sword = make_item("Sword", CAT_WEAPON)
        self.shield = make_item("Shield", CAT_SHIELD)
        self.armor = make_item("Armor", CAT_ARMOR)
        self.helm = make_item("Helm", CAT_HELM)
        self.ring = make_item("Ring", CAT_RING)
        self.potion = make_item("Potion", CAT_POTION, "!")
        self.scroll = make_item("Scroll", CAT_SCROLL, "?")
        self.bread = make_item("Bread", CAT_FOOD, "%")
        self.book = make_item("Spellbook", CAT_SPELLBOOK, "B")
        self.tool = make_item("Tool", CAT_TOOL, "(")
        for it in (self.sword, self.shield, self.armor, self.helm, self.ring,
                   self.potion, self.scroll, self.bread, self.book, self.tool):
            inv.add_item(it)
        return inv

    def test_filter_weapon(self):
        inv = self.make_inventory()
        assert inv.filter_items("weapon") == [self.sword]

    def test_filter_equipment(self):
        inv = self.make_inventory()
        result = inv.filter_items("equipment")
        assert len(result) == 5
        for it in (self.sword, self.shield, self.armor, self.helm, self.ring):
            assert it in result
        assert self.potion not in result
        assert self.tool not in result

    def test_filter_consumable(self):
        inv = self.make_inventory()
        result = inv.filter_items("consumable")
        assert len(result) == 4
        for it in (self.potion, self.scroll, self.bread, self.book):
            assert it in result
        assert self.sword not in result

    def test_filter_single_category(self):
        inv = Inventory()
        ore = make_item("Ore", CAT_ORE, "*")
        inv.add_item(ore)
        inv.add_item(make_item("Sword", CAT_WEAPON))
        assert inv.filter_items("ore") == [ore]

    def test_sort_by_name(self):
        inv = Inventory()
        for name in ("C Sword", "A Sword", "B Sword"):
            inv.add_item(make_item(name))
        assert [i.name for i in inv.sort_items("name")] == ["A Sword", "B Sword", "C Sword"]
        assert [i.name for i in inv.sort_items("name", reverse=True)] == ["C Sword", "B Sword", "A Sword"]

    def test_sort_by_value(self):
        inv = Inventory()
        cheap = make_item("Cheap", base_value=10)
        dear = make_item("Dear", base_value=100)
        inv.add_item(dear)
        inv.add_item(cheap)
        assert [i.name for i in inv.sort_items("value")] == ["Cheap", "Dear"]

    def test_sort_by_weight(self):
        inv = Inventory()
        light = make_item("Light", base_weight=0.5)
        heavy = make_item("Heavy", base_weight=9.0)
        inv.add_item(heavy)
        inv.add_item(light)
        assert [i.name for i in inv.sort_items("weight")] == ["Light", "Heavy"]

    def test_sort_by_quality(self):
        inv = Inventory()
        bad = make_item("Bad", quality=QUALITY_BAD)
        normal = make_item("Normal", quality=QUALITY_NORMAL)
        good = make_item("Good", quality=QUALITY_GOOD)
        miracle = make_item("Miracle", quality=QUALITY_MIRACLE)
        god = make_item("God", quality=QUALITY_GOD)
        for it in (normal, god, bad, miracle, good):
            inv.add_item(it)
        assert [i.name for i in inv.sort_items("quality")] == [
            "Bad", "Normal", "Good", "Miracle", "God",
        ]

    def test_locked_items_come_first(self):
        inv = Inventory()
        a = make_item("A Sword")
        z = make_item("Z Sword")
        inv.add_item(a)
        inv.add_item(z)
        inv.toggle_lock(z)
        result = inv.sort_items("name")
        assert result[0] is z
        assert [i.name for i in result] == ["Z Sword", "A Sword"]

    def test_can_sell_locked(self):
        inv = Inventory()
        item = make_item("Sword")
        inv.add_item(item)
        inv.toggle_lock(item)
        ok, msg = inv.can_sell(item)
        assert ok is False
        assert "ロック" in msg

    def test_can_sell_cursed(self):
        inv = Inventory()
        item = make_item("Cursed Sword", cursed=True)
        inv.add_item(item)
        ok, msg = inv.can_sell(item)
        assert ok is False
        assert "呪われている" in msg

    def test_can_sell_equipped(self):
        inv = Inventory()
        item = make_item("Sword")
        inv.add_item(item)
        inv.equip(item, "main_hand")
        ok, msg = inv.can_sell(item)
        assert ok is False
        assert "装備中" in msg

    def test_can_sell_normal(self):
        inv = Inventory()
        item = make_item("Sword")
        inv.add_item(item)
        assert inv.can_sell(item) == (True, "")

    def test_can_destroy_locked(self):
        inv = Inventory()
        item = make_item("Sword")
        inv.add_item(item)
        inv.toggle_lock(item)
        ok, msg = inv.can_destroy(item)
        assert ok is False
        assert "ロック" in msg

    def test_can_destroy_equipped(self):
        inv = Inventory()
        item = make_item("Sword")
        inv.add_item(item)
        inv.equip(item, "main_hand")
        ok, msg = inv.can_destroy(item)
        assert ok is False
        assert "装備中" in msg

    def test_can_destroy_cursed_allowed(self):
        inv = Inventory()
        item = make_item("Cursed Sword", cursed=True)
        inv.add_item(item)
        assert inv.can_destroy(item) == (True, "")

    def test_toggle_lock_flips_state(self):
        inv = Inventory()
        item = make_item("Sword")
        inv.add_item(item)
        assert inv.toggle_lock(item) is True
        assert item.locked is True
        assert inv.toggle_lock(item) is False
        assert item.locked is False

    def test_toggle_lock_item_not_in_inventory(self):
        assert Inventory().toggle_lock(make_item("Ghost")) is False


class TestInventoryStatBonuses:
    """Tests for get_stat_bonuses / get_weapon_element_damages."""

    def test_no_equipment_returns_empty(self):
        assert Inventory().get_stat_bonuses() == {}

    def test_aggregates_stat_and_combat_bonuses(self):
        inv = Inventory()
        sword = make_item("Sword")
        sword.enchants = (
            MockEnchant("stat_bonus", "strength", 5),
            MockEnchant("combat_bonus", "dexterity", 3),
            MockEnchant("other_type", "ignored_stat", 99),
        )
        armor = make_item("Armor", CAT_ARMOR)
        armor.enchants = (MockEnchant("stat_bonus", "strength", 2),)
        inv.add_item(sword)
        inv.add_item(armor)
        inv.equip(sword, "main_hand")
        inv.equip(armor, "body")
        assert inv.get_stat_bonuses() == {"strength": 7, "dexterity": 3}

    def test_unequipped_items_not_counted(self):
        inv = Inventory()
        sword = make_item("Sword")
        sword.enchants = (MockEnchant("stat_bonus", "strength", 5),)
        inv.add_item(sword)
        assert inv.get_stat_bonuses() == {}

    def test_empty_enchants_fall_back_to_enchantments(self):
        inv = Inventory()
        sword = make_item("Sword")
        inv.add_item(sword)
        inv.equip(sword, "main_hand")
        assert inv.get_stat_bonuses() == {}

    def test_weapon_element_damages(self):
        inv = Inventory()
        sword = make_item("Sword")
        sword.enchants = (
            MockEnchant("element_damage", power=10, element="fire"),
            MockEnchant("element_damage", power=5, element="ice"),
            MockEnchant("stat_bonus", "strength", 3),
            MockEnchant("element_damage", power=7, element=""),  # no element: skipped
        )
        inv.add_item(sword)
        inv.equip(sword, "main_hand")
        assert inv.get_weapon_element_damages() == [("fire", 10), ("ice", 5)]

    def test_weapon_element_damages_no_weapon(self):
        assert Inventory().get_weapon_element_damages() == []

    def test_weapon_element_damages_ignores_off_hand(self):
        inv = Inventory()
        shield = make_item("Shield", CAT_SHIELD)
        shield.enchants = (MockEnchant("element_damage", power=10, element="fire"),)
        inv.add_item(shield)
        inv.equip(shield, "off_hand")
        assert inv.get_weapon_element_damages() == []


class TestInventoryTickFoodRot:
    """Tests for Inventory.tick_food_rot."""

    def test_food_rots_and_returns_message(self):
        inv = Inventory()
        bread = make_item("Bread", CAT_FOOD, "%", nutrition=100)
        bread.rot_progress = 4999
        inv.add_item(bread)
        logs = inv.tick_food_rot(1)
        assert logs == ["腐ったBread が腐り始めた！"]
        assert bread.name == "腐ったBread"
        assert bread.rot_progress == 5000
        assert bread.nutrition == 0

    def test_food_below_threshold_no_message(self):
        inv = Inventory()
        bread = make_item("Bread", CAT_FOOD, "%", nutrition=100)
        inv.add_item(bread)
        assert inv.tick_food_rot(1) == []
        assert bread.rot_progress == 1
        assert bread.name == "Bread"

    def test_ticks_parameter_applied(self):
        inv = Inventory()
        bread = make_item("Bread", CAT_FOOD, "%")
        inv.add_item(bread)
        inv.tick_food_rot(100)
        assert bread.rot_progress == 100

    def test_non_food_skipped(self):
        inv = Inventory()
        sword = make_item("Sword")
        inv.add_item(sword)
        assert inv.tick_food_rot(1) == []
        assert sword.rot_progress == 0

    def test_cooling_food_skipped(self):
        inv = Inventory()
        bread = make_item("Bread", CAT_FOOD, "%", nutrition=100)
        bread.rot_progress = 4999
        bread.is_cooling = True
        inv.add_item(bread)
        assert inv.tick_food_rot(1) == []
        assert bread.rot_progress == 4999
        assert bread.name == "Bread"


# ==================== Serialization / module-level functions ====================


class TestItemFromDict:
    """Tests for Item.to_dict / Item.from_dict round-trip."""

    def test_round_trip(self):
        item = make_item(
            "Cursed Blade",
            base_weight=2.5,
            base_value=80,
            count=4,
            cursed=True,
            identified=False,
            locked=True,
            quality=QUALITY_GOOD,
            material="steel",
        )
        item.rot_progress = 123
        item.is_cooling = True
        item.enchantments = ["fire", "sharp"]  # exercises the setter alias

        restored = Item.from_dict(item.to_dict())

        assert restored.item_id == item.item_id
        assert restored.name == "Cursed Blade"
        assert restored.category == CAT_WEAPON
        assert restored.count == 4
        assert restored.base_weight == 2.5
        assert restored.base_value == 80
        assert restored.material == "steel"
        assert restored.quality == QUALITY_GOOD
        assert restored.cursed is True
        assert restored.identified is False
        assert restored.locked is True
        assert restored.rot_progress == 123
        assert restored.is_cooling is True
        assert restored.enchants == ("fire", "sharp")
        assert restored.sell_price == item.sell_price

    def test_from_dict_defaults(self):
        item = Item.from_dict({})
        assert item.name == "Unknown Item"
        assert item.category == CAT_TOOL
        assert item.identified is True
        assert item.cursed is False
        assert item.locked is False
        assert item.rot_progress == 0
        assert item.is_cooling is False

    def test_sort_items_unknown_key_falls_back_to_name(self):
        inv = Inventory()
        for name in ("C", "A", "B"):
            inv.add_item(make_item(name))
        assert [i.name for i in inv.sort_items("mystery_key")] == ["A", "B", "C"]


class TestCreateSampleItem:
    """Tests for create_sample_item YAML path and fallback presets."""

    def test_yaml_data_path(self):
        item = create_sample_item("longsword", x=3, y=4)
        assert item.name == "長剣"
        assert item.category == CAT_WEAPON
        assert item.x == 3
        assert item.y == 4

    def test_yaml_unknown_name_falls_back_to_longsword(self):
        item = create_sample_item("no_such_item_entry")
        assert item.name == "長剣"

    def test_fallback_presets_without_yaml(self, monkeypatch):
        from config_manager import DataCache

        monkeypatch.setattr(DataCache, "get_data", staticmethod(lambda path: None))

        bread = create_sample_item("bread")
        assert bread.name == "パン"
        assert bread.category == CAT_FOOD
        assert bread.nutrition == 1500

        ration = create_sample_item("ration")
        assert ration.nutrition == 3200

        book = create_sample_item("book_fire")
        assert book.category == CAT_SPELLBOOK
        assert book.spell_id == "magic_dart"
        assert book.sp_stock == 50

        potion = create_sample_item("potion_heal")
        assert potion.category == CAT_POTION
        assert potion.heal_amount == 35

        armor = create_sample_item("leather_armor")
        assert armor.category == CAT_ARMOR
        assert armor.pv == 4
        assert armor.material == "wood"

        shield = create_sample_item("shield")
        assert shield.category == CAT_SHIELD
        assert shield.pv == 2
        assert shield.dv == 4
        assert shield.material == "steel"

        shortsword = create_sample_item("shortsword")
        assert shortsword.name == "短剣"

        unknown = create_sample_item("mystery_name")
        assert unknown.name == "長剣"
        assert unknown.base_weight == 3.5


class _GoldHolder:
    def __init__(self, gold=100):
        self.gold = gold


class _AddGoldHolder:
    """Holder without a gold attribute; only exposes add_gold()."""

    def __init__(self):
        self.total = 0

    def add_gold(self, amount):
        self.total += amount


class TestSellFunction:
    """Tests for the module-level sell() function."""

    def test_sell_with_gold_attribute(self):
        holder = _GoldHolder(gold=100)
        item = make_item("Gem", base_value=100, count=2)  # sell_price = 30
        gained = sell(item, holder)
        assert gained == 60
        assert holder.gold == 160

    def test_sell_with_add_gold_method(self):
        holder = _AddGoldHolder()
        item = make_item("Gem", base_value=100, count=1)
        gained = sell(item, holder)
        assert gained == 30
        assert holder.total == 30

    def test_sell_fallback_price_when_none(self):
        holder = _GoldHolder()
        item = make_item("Gem", base_value=100)
        item.sell_price = None
        assert sell(item, holder) == 30

    def test_sell_invalid_holder_raises(self):
        with pytest.raises(ValueError):
            sell(make_item("Gem"), object())


class TestCalculateReincarnationDropRate:
    """Tests for reincarnation drop rate scaling."""

    def test_no_reincarnations_unchanged(self):
        assert calculate_reincarnation_drop_rate(0.1, 0) == pytest.approx(0.1)

    def test_scaling_applied(self):
        assert calculate_reincarnation_drop_rate(0.1, 5) == pytest.approx(0.15)

    def test_scaling_capped_at_3x(self):
        assert calculate_reincarnation_drop_rate(0.1, 100) == pytest.approx(0.3)


class TestAffixSystem:
    """Tests for the affix (接尾辞) system."""

    @pytest.fixture(autouse=True)
    def _fresh_affix_cache(self):
        clear_affix_cache()
        yield
        clear_affix_cache()

    def test_affix_is_curse_property(self):
        curse = Affix(id="c", name="呪い", slot="any", weight=0, tier=0, mods={}, cursed=True)
        normal = Affix(id="n", name="通常", slot="any", weight=5, tier=1, mods={})
        assert curse.is_curse is True
        assert normal.is_curse is False

    def test_load_affixes_from_yaml(self):
        affixes = load_affixes()
        assert len(affixes) > 0
        assert all(isinstance(a, Affix) for a in affixes.values())
        first = next(iter(affixes.values()))
        assert first.name
        assert first.slot in ("weapon", "armor", "any")

    def test_load_affixes_cached(self):
        assert load_affixes() is load_affixes()

    def test_load_affixes_missing_file_returns_empty(self):
        assert load_affixes("no_such_affix_file_xyz.yaml") == {}

    def test_load_affixes_skips_non_dict_entries(self, tmp_path):
        bad_yaml = tmp_path / "affixes.yaml"
        bad_yaml.write_text(
            "valid_one:\n  name: 有効\n  weight: 5\n  tier: 1\n  mods: {}\n"
            "not_a_dict: just_a_string\n",
            encoding="utf-8",
        )
        affixes = load_affixes(str(bad_yaml))
        assert set(affixes) == {"valid_one"}
        clear_affix_cache()

    def test_affix_roll_count_by_quality(self):
        assert _affix_roll_count(QUALITY_GOD) == 2
        assert _affix_roll_count(QUALITY_MIRACLE) == 1
        assert _affix_roll_count(QUALITY_GOOD) == 1
        assert _affix_roll_count(QUALITY_BAD) == 0
        assert _affix_roll_count(QUALITY_NORMAL, random.Random(1)) == 1   # rolls 0.13
        assert _affix_roll_count(QUALITY_NORMAL, random.Random(42)) == 0  # rolls 0.63

    def test_roll_affixes_empty_pool_returns_item_unchanged(self, monkeypatch):
        monkeypatch.setattr(item_system, "load_affixes", lambda: {})
        item = make_item("Sword")
        assert roll_affixes(item, rng=random.Random(1)) is item
        assert getattr(item, "affix_ids", "unset") == "unset"

    def test_roll_affixes_applies_affix(self, monkeypatch):
        affix = Affix(id="sharp", name="鋭利", slot="weapon", weight=10, tier=1,
                      mods={"dmg_bonus": 3, "speed": 2})
        monkeypatch.setattr(item_system, "load_affixes", lambda: {"sharp": affix})
        item = make_item("Sword")
        result = roll_affixes(item, rng=random.Random(1), quality=QUALITY_GOOD)
        assert result is item
        assert result.affix_ids == ("sharp",)
        assert "鋭利" in result.name
        assert result.dmg_bonus == 3
        assert result.affix_mods["speed"] == 2

    def test_roll_affixes_god_gets_two_distinct_affixes(self, monkeypatch):
        pool = {
            "sharp": Affix(id="sharp", name="鋭利", slot="weapon", weight=10, tier=1,
                           mods={"dmg_bonus": 3}),
            "heavy": Affix(id="heavy", name="重々", slot="weapon", weight=10, tier=1,
                           mods={"pv": 2}),
        }
        monkeypatch.setattr(item_system, "load_affixes", lambda: pool)
        item = make_item("Sword")
        result = roll_affixes(item, rng=random.Random(3), quality=QUALITY_GOD)
        assert len(result.affix_ids) == 2
        assert set(result.affix_ids) == {"sharp", "heavy"}
        assert result.dmg_bonus == 3
        assert result.pv == 2

    def test_roll_affixes_breaks_when_candidates_exhausted(self, monkeypatch):
        # God quality rolls twice but the pool holds a single affix.
        affix = Affix(id="sharp", name="鋭利", slot="weapon", weight=10, tier=1,
                      mods={"dmg_bonus": 3})
        monkeypatch.setattr(item_system, "load_affixes", lambda: {"sharp": affix})
        item = make_item("Sword")
        result = roll_affixes(item, rng=random.Random(3), quality=QUALITY_GOD)
        assert result.affix_ids == ("sharp",)
        assert result.dmg_bonus == 3

    def test_roll_affixes_no_roll_for_normal_quality(self, monkeypatch):
        affix = Affix(id="sharp", name="鋭利", slot="weapon", weight=10, tier=1, mods={})
        monkeypatch.setattr(item_system, "load_affixes", lambda: {"sharp": affix})
        item = make_item("Sword")
        result = roll_affixes(item, rng=random.Random(42), quality=QUALITY_NORMAL)
        assert result is item
        assert result.affix_ids == ()
        assert result.name == "Sword"

    def test_apply_affix_accumulates_numeric_and_dynamic(self):
        item = make_item("Sword")
        _apply_affix(item, Affix(id="a", name="A", slot="any", weight=1, tier=1,
                                 mods={"dmg_bonus": 2, "fire_damage": 1}))
        _apply_affix(item, Affix(id="b", name="B", slot="any", weight=1, tier=1,
                                 mods={"dmg_bonus": 1, "fire_damage": 4}))
        assert item.dmg_bonus == 3
        assert item.affix_mods["fire_damage"] == 5


class _UseItemUser:
    def __init__(self, hp=50, max_hp=100, mp=10, max_mp=50, hunger=1000, cure_result=True):
        self.name = "テスター"
        self.hp = hp
        self.max_hp = max_hp
        self.mp = mp
        self.max_mp = max_mp
        self.hunger = hunger
        self._cure_result = cure_result
        self.removed = []

    def remove_status(self, status):
        self.removed.append(status)
        return self._cure_result


class TestIdentification:
    """Tests for can_identify / identify."""

    def test_can_identify(self):
        assert can_identify(make_item("X", identified=False)) is True
        assert can_identify(make_item("X")) is False

    def test_identify_already_identified_noop(self):
        item = make_item("X")
        assert identify(item, 10) is item
        assert item.identified is True

    def test_identify_without_gold_holder(self):
        item = make_item("X", identified=False)
        assert identify(item, 10) is item
        assert item.identified is True

    def test_identify_insufficient_gold(self):
        holder = _GoldHolder(gold=5)
        item = make_item("X", identified=False)
        assert identify(item, 10, holder) is item
        assert item.identified is False
        assert holder.gold == 5

    def test_identify_success_charges_gold(self):
        holder = _GoldHolder(gold=100)
        item = make_item("X", identified=False)
        assert identify(item, 30, holder) is item
        assert item.identified is True
        assert holder.gold == 70


class TestUseItem:
    """Tests for the module-level use_item() function."""

    def test_use_heal_potion(self):
        item = make_item("軽傷治療のポーション", CAT_POTION, "!", heal_amount=35)
        user = _UseItemUser(hp=50, max_hp=100)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.hp == 85
        assert "回復" in msg

    def test_use_heal_potion_caps_at_max_hp(self):
        item = make_item("軽傷治療のポーション", CAT_POTION, "!", heal_amount=35)
        user = _UseItemUser(hp=90, max_hp=100)
        use_item(user, item)
        assert user.hp == 100

    def test_use_cure_potion_cures_status(self):
        item = make_item("毒消しのポーション", CAT_POTION, "!")
        user = _UseItemUser(cure_result=True)
        ok, msg = use_item(user, item)
        assert ok is True
        assert "治まった" in msg
        assert "poison" in user.removed
        assert "burn" in user.removed

    def test_use_cure_potion_nothing_to_cure(self):
        item = make_item("毒消しのポーション", CAT_POTION, "!")
        user = _UseItemUser(cure_result=False)
        ok, msg = use_item(user, item)
        assert ok is True
        assert "治まった" not in msg
        assert "飲んだ" in msg

    def test_use_mana_potion(self):
        item = make_item("魔力回復のポーション", CAT_POTION, "!")
        user = _UseItemUser(mp=0, max_mp=50)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.mp == 40
        assert "MP" in msg

    def test_use_food(self):
        item = make_item("パン", CAT_FOOD, "%", nutrition=1500)
        user = _UseItemUser(hunger=1000)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.hunger == 2500
        assert "食べた" in msg

    def test_use_food_without_hunger_attribute(self):
        item = make_item("パン", CAT_FOOD, "%", nutrition=1500)
        user = _UseItemUser()
        del user.hunger
        ok, msg = use_item(user, item)
        assert ok is True
        assert "食べた" in msg

    def test_use_unusable_item(self):
        ok, msg = use_item(_UseItemUser(), make_item("Sword", CAT_WEAPON))
        assert ok is False
        assert msg == "使用できないアイテムです。"

    def test_use_plain_potion_without_effect(self):
        ok, msg = use_item(_UseItemUser(), make_item("水", CAT_POTION, "!"))
        assert ok is False
        assert msg == "使用できないアイテムです。"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
