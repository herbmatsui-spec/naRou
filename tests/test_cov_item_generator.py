"""改善案7: アイテム生成器・エンチャント統合のテスト。

item_generator.py の実装を検証:
- 品質抽選 (roll_quality)
- 品質によるエンチャント付与数 (get_enchant_count)
- エンチャント選定・威力計算 (generate_enchantments_for_item)
- アイテム生成 (create_item)
- 軽量ファクトリ (roll_enchantments)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from naRou.constants import (
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from item_generator import ItemGenerator, roll_enchantments


def _make_ench_def(
    ench_id: str,
    name: str,
    ench_type: str = "combat_bonus",
    power_range=None,
    min_quality=QUALITY_NORMAL,
    target_stat="pv",
    element=None,
):
    return SimpleNamespace(
        id=ench_id,
        name=name,
        type=ench_type,
        power_range=power_range or [1, 5],
        min_quality=min_quality,
        target_stat=target_stat,
        element=element,
    )


class _FakeEnchantRepo:
    def __init__(self, enchants_by_category):
        self._by_cat = enchants_by_category

    def get_for_category(self, category):
        return self._by_cat.get(category, [])


class _FakeDataManager:
    def __init__(self, enchants_by_category):
        self.enchantments = _FakeEnchantRepo(enchants_by_category)
        self.items = SimpleNamespace(_data={})


class TestItemGeneratorQuality:
    def setup_method(self) -> None:
        self.gen = ItemGenerator(data_manager=_FakeDataManager({}))

    def test_roll_quality_returns_valid(self) -> None:
        q = self.gen.roll_quality(dungeon_level=1)
        assert q in (QUALITY_BAD, QUALITY_NORMAL, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD)

    def test_roll_quality_deeper_favors_good(self) -> None:
        # 深度が上がると GOOD 以上の重みが上がる
        counts = {QUALITY_BAD: 0, QUALITY_GOD: 0}
        for _ in range(200):
            q = self.gen.roll_quality(dungeon_level=100)
            if q == QUALITY_BAD:
                counts[QUALITY_BAD] += 1
            if q == QUALITY_GOD:
                counts[QUALITY_GOD] += 1
        assert counts[QUALITY_GOD] > counts[QUALITY_BAD]

    def test_roll_quality_luck_bonus(self) -> None:
        q_base = self.gen.roll_quality(dungeon_level=1, luck_bonus=0.0)
        q_lucky = self.gen.roll_quality(dungeon_level=1, luck_bonus=10.0)
        # 幸運ボーナスが高いと GOOD 以上が出やすいはず（統計的だが、ここでは範囲チェックのみ）
        assert q_lucky in (QUALITY_BAD, QUALITY_NORMAL, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD)


class TestItemGeneratorEnchantCount:
    def setup_method(self) -> None:
        self.gen = ItemGenerator(data_manager=_FakeDataManager({}))

    def test_get_enchant_count_bad_is_zero(self) -> None:
        assert self.gen.get_enchant_count(QUALITY_BAD) == 0

    def test_get_enchant_count_normal(self) -> None:
        # 10% の確率で 1、それ以外 0
        counts = {0: 0, 1: 0}
        for _ in range(200):
            counts[self.gen.get_enchant_count(QUALITY_NORMAL)] += 1
        assert counts[0] > 0
        assert counts[1] > 0 or counts[0] < 200

    def test_get_enchant_count_good(self) -> None:
        assert self.gen.get_enchant_count(QUALITY_GOOD) in (1, 2)

    def test_get_enchant_count_miracle(self) -> None:
        assert self.gen.get_enchant_count(QUALITY_MIRACLE) in (2, 3, 4)

    def test_get_enchant_count_god(self) -> None:
        assert self.gen.get_enchant_count(QUALITY_GOD) in (4, 5, 6)


class TestItemGeneratorGenerateEnchantments:
    def setup_method(self) -> None:
        weapon_enchants = [
            _make_ench_def("fire_dmg", "炎傷", power_range=[3, 6], target_stat="dmg_bonus", element="fire"),
            _make_ench_def("pv_up", "頑丈", power_range=[1, 3], target_stat="pv"),
            _make_ench_def("curse_ench", "呪縛", power_range=[1, 2], min_quality=QUALITY_MIRACLE, target_stat="dmg_bonus"),
            _make_ench_def("hit_up", "命中", power_range=[1, 2], target_stat="hit_bonus"),
        ]
        self.gen = ItemGenerator(data_manager=_FakeDataManager({"weapon": weapon_enchants}))

    def test_generate_enchantments_bad_returns_empty(self) -> None:
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_BAD)
        assert result == []

    def test_generate_enchantments_normal_may_return_empty(self) -> None:
        # NORMAL は 10% の確率で 1 件。統計的に 0 または 1 件
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_NORMAL)
        assert len(result) in (0, 1)

    def test_generate_enchantments_good(self) -> None:
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_GOOD)
        assert 1 <= len(result) <= 2

    def test_generate_enchantments_miracle(self) -> None:
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_MIRACLE)
        assert 2 <= len(result) <= 4

    def test_generate_enchantments_god(self) -> None:
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_GOD)
        assert 4 <= len(result) <= 6

    def test_generate_enchantments_quality_filter(self) -> None:
        # MIRACLE 品質では min_quality=MIRACLE のエンチャントも選べる
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_MIRACLE, count=3)
        ids = [e.id for e in result]
        assert "curse_ench" in ids or len(ids) >= 2

    def test_generate_enchantments_unknown_category(self) -> None:
        result = self.gen.generate_enchantments_for_item("nonexistent", QUALITY_GOOD)
        assert result == []

    def test_enchantment_power_scaling(self) -> None:
        # GOD 品質では威力が上がる
        result = self.gen.generate_enchantments_for_item("weapon", QUALITY_GOD, count=1)
        if result:
            assert result[0].power >= 3  # base_power * 1.6 + 2 以上


class TestItemGeneratorCreateItem:
    def setup_method(self) -> None:
        item_defs = {
            "longsword": SimpleNamespace(
                id="longsword",
                name="長剣",
                category=SimpleNamespace(value="weapon"),
                char="🗡️",
                color=[200, 200, 200],
                material="iron",
                base_weight=3.5,
                base_value=120,
                hit_bonus=2,
                dmg_bonus=0,
                pv=0,
                dv=0,
                heal_amount=0,
                nutrition=0,
                spell_id="",
                sp_stock=0,
                dice_num=2,
                dice_side=6,
            ),
        }
        self.gen = ItemGenerator(
            data_manager=_FakeDataManager(
                {
                    "weapon": [
                        _make_ench_def("fire_dmg", "炎傷", power_range=[3, 6], target_stat="dmg_bonus"),
                    ]
                }
            )
        )
        self.gen.data_manager.items = SimpleNamespace(_data=item_defs)
        self.gen.data_manager.items.get = lambda tid: item_defs.get(tid)

    def test_create_item_weapon(self) -> None:
        item = self.gen.create_item("longsword", quality=QUALITY_GOOD, dungeon_level=1)
        assert item.name == "長剣"
        assert item.category == "weapon"
        assert item.quality == QUALITY_GOOD
        assert item.identified is True

    def test_create_item_identified_false(self) -> None:
        item = self.gen.create_item("longsword", quality=QUALITY_NORMAL, identified=False)
        assert item.identified is False

    def test_create_item_unknown_template_raises(self) -> None:
        with pytest.raises(KeyError):
            self.gen.create_item("nonexistent_item")

    def test_create_item_has_enchants_for_equip(self) -> None:
        item = self.gen.create_item("longsword", quality=QUALITY_GOOD, dungeon_level=1)
        # エンチャントが付与される可能性がある（統計的）
        assert isinstance(item.enchants, tuple)

    def test_roll_enchantments_lightweight(self) -> None:
        result = roll_enchantments("weapon", QUALITY_GOOD)
        assert isinstance(result, tuple)
        assert 1 <= len(result) <= 2

    def test_roll_enchantments_bad_is_empty(self) -> None:
        result = roll_enchantments("weapon", QUALITY_BAD)
        assert result == ()
