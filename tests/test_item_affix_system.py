"""item_system.py 後半 (lines 523-899) のテスト:
create_sample_item / sell / calculate_reincarnation_drop_rate /
Affix システム / 鑑定 / use_item。
加えてモジュール全体のカバレッジを 80% 以上に引き上げるため
Item / Inventory の基本動作テストを含む。
"""

from __future__ import annotations

import dataclasses
import os
import random
import sys
from types import SimpleNamespace

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import (  # noqa: E402
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from item_system import (  # noqa: E402
    CAT_ARMOR,
    CAT_FOOD,
    CAT_ORE,
    CAT_POTION,
    CAT_SHIELD,
    CAT_SPELLBOOK,
    CAT_TOOL,
    CAT_WEAPON,
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

AFFIX_YAML = os.path.join(_ROOT, "data", "item_affixes.yaml")


# =============================================================================
# Autouse fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _repo_root_cwd():
    """data/*.yaml は相対パスで読まれるため、常にリポジトリルートで実行する"""
    old = os.getcwd()
    os.chdir(_ROOT)
    yield
    os.chdir(old)


@pytest.fixture(autouse=True)
def _fresh_affix_cache():
    clear_affix_cache()
    yield
    clear_affix_cache()


@pytest.fixture(autouse=True)
def _clean_data_cache():
    from config_manager import DataCache

    DataCache.clear()
    yield
    DataCache.clear()


# =============================================================================
# Test stubs / helpers
# =============================================================================


class GoldAttrHolder:
    """gold 属性を持つホルダー"""

    def __init__(self, gold: int = 0):
        self.gold = gold


class AddGoldHolder:
    """add_gold メソッドのみを持つホルダー"""

    def __init__(self):
        self.received: list[int] = []

    def add_gold(self, amount: int) -> None:
        self.received.append(amount)


class StatusUser:
    """remove_status を記録するユーザー"""

    def __init__(self, result=None):
        self.name = "Hero"
        self.calls: list[str] = []
        self.result = result

    def remove_status(self, key: str):
        self.calls.append(key)
        return self.result


class Enchant:
    """Inventory.get_stat_bonuses 用のエンチャントスタブ"""

    def __init__(self, type: str, target_stat=None, power: int = 0, element=None):
        self.type = type
        self.target_stat = target_stat
        self.power = power
        self.element = element


def make_user(**kw):
    base = dict(name="Hero", hp=50, max_hp=80, mp=10, max_mp=45, hunger=8000)
    base.update(kw)
    return SimpleNamespace(**base)


def _disable_items_yaml(monkeypatch) -> None:
    """DataCache.get_data が None を返すようにし、プリセット経路を強制する"""
    import config_manager

    monkeypatch.setattr(
        config_manager.DataCache, "get_data", classmethod(lambda cls, path: None)
    )


def _write_affix_yaml(path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    return str(path)


# =============================================================================
# 1. create_sample_item
# =============================================================================


class TestCreateSampleItem:
    def test_yaml_item_returns_item_from_yaml_data(self):
        item = create_sample_item("katana", x=2, y=3)
        assert isinstance(item, Item)
        assert item.name == "刀"
        assert item.category == CAT_WEAPON
        assert item.base_value == 280
        assert item.sell_price == 84
        assert item.material == "steel"
        assert (item.x, item.y) == (2, 3)

    def test_yaml_potion_fields(self):
        item = create_sample_item("potion_mana")
        assert item.name == "魔力回復のポーション"
        assert item.category == CAT_POTION
        assert item.heal_amount == 40
        assert item.identified is True

    @pytest.mark.parametrize(
        "preset,category",
        [
            ("longsword", CAT_WEAPON),
            ("shortsword", CAT_WEAPON),
            ("shield", CAT_SHIELD),
            ("leather_armor", CAT_ARMOR),
            ("potion_heal", CAT_POTION),
            ("bread", CAT_FOOD),
            ("ration", CAT_FOOD),
            ("book_fire", CAT_SPELLBOOK),
        ],
    )
    def test_preset_names_return_correct_categories(self, preset, category, monkeypatch):
        _disable_items_yaml(monkeypatch)
        assert create_sample_item(preset).category == category

    def test_preset_details(self, monkeypatch):
        _disable_items_yaml(monkeypatch)
        potion = create_sample_item("potion_heal")
        assert potion.heal_amount == 35
        assert potion.identified is True
        assert create_sample_item("bread").nutrition == 1500
        assert create_sample_item("ration").nutrition == 3200
        book = create_sample_item("book_fire")
        assert book.spell_id == "magic_dart"
        assert book.sp_stock == 50
        assert create_sample_item("shield").pv == 2
        assert create_sample_item("leather_armor").dv == 2

    def test_unknown_name_falls_back_to_longsword(self, monkeypatch):
        _disable_items_yaml(monkeypatch)
        item = create_sample_item("totally_unknown_item", x=7, y=8)
        assert item.name == "長剣"
        assert item.category == CAT_WEAPON
        assert item.base_value == 120
        assert item.dice_num == 2 and item.dice_side == 6
        assert item.hit_bonus == 2
        assert (item.x, item.y) == (7, 8)


# =============================================================================
# 2. sell
# =============================================================================


class TestSell:
    def test_uses_sell_price_when_set(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_value=100, sell_price=77)
        holder = GoldAttrHolder(gold=0)
        assert sell(item, holder) == 77
        assert holder.gold == 77

    def test_multiplies_by_count(self):
        item = Item(
            "薬", CAT_POTION, "🧪", (255, 100, 100), base_value=100, sell_price=77, count=3
        )
        holder = GoldAttrHolder(gold=10)
        assert sell(item, holder) == 231
        assert holder.gold == 241

    def test_falls_back_to_base_value_30_percent(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_value=100)
        item.sell_price = None  # Item は生成時に sell_price を埋めるため、フォールバック経路は手動で再現する
        holder = GoldAttrHolder(gold=0)
        assert sell(item, holder) == 30
        assert holder.gold == 30

    def test_fallback_multiplied_by_count(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_value=101, count=2)
        item.sell_price = None
        assert sell(item, GoldAttrHolder()) == int(101 * 0.3) * 2

    def test_add_gold_method_holder(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_value=50, sell_price=20)
        holder = AddGoldHolder()
        assert sell(item, holder) == 20
        assert holder.received == [20]

    def test_invalid_holder_raises_value_error(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        with pytest.raises(ValueError):
            sell(item, object())


# =============================================================================
# 3. calculate_reincarnation_drop_rate
# =============================================================================


class TestReincarnationDropRate:
    def test_zero_reincarnations_returns_base(self):
        assert calculate_reincarnation_drop_rate(0.1, 0) == pytest.approx(0.1)
        assert calculate_reincarnation_drop_rate(0.25, 0) == pytest.approx(0.25)

    def test_scaling_bonus_is_10_percent_per_reincarnation(self):
        assert calculate_reincarnation_drop_rate(0.1, 5) == pytest.approx(0.15)
        assert calculate_reincarnation_drop_rate(0.1, 10) == pytest.approx(0.2)
        assert calculate_reincarnation_drop_rate(0.5, 10) == pytest.approx(1.0)

    def test_capped_at_three_times(self):
        assert calculate_reincarnation_drop_rate(0.1, 100) == pytest.approx(0.3)
        assert calculate_reincarnation_drop_rate(0.1, 1000) == pytest.approx(0.3)

    def test_monotonic_non_decreasing(self):
        rates = [calculate_reincarnation_drop_rate(0.2, n) for n in range(0, 40)]
        assert rates == sorted(rates)


# =============================================================================
# 4. Affix dataclass
# =============================================================================


class TestAffixDataclass:
    def test_fields_are_stored(self):
        a = Affix(
            id="of_test", name="テストの", slot="weapon", weight=10, tier=1,
            mods={"dmg_bonus": 2},
        )
        assert a.id == "of_test"
        assert a.name == "テストの"
        assert a.slot == "weapon"
        assert a.weight == 10
        assert a.tier == 1
        assert a.mods == {"dmg_bonus": 2}
        assert a.cursed is False
        assert a.is_curse is False

    def test_is_curse_returns_cursed_flag(self):
        a = Affix(
            id="curse_of_test", name="呪い", slot="any", weight=0, tier=0,
            mods={"dv": -5}, cursed=True,
        )
        assert a.cursed is True
        assert a.is_curse is True

    def test_frozen_immutable(self):
        a = Affix(id="x", name="x", slot="any", weight=1, tier=1, mods={})
        with pytest.raises(dataclasses.FrozenInstanceError):
            a.weight = 5

    def test_equality(self):
        a = Affix(id="x", name="x", slot="any", weight=1, tier=1, mods={"dv": 1})
        b = Affix(id="x", name="x", slot="any", weight=1, tier=1, mods={"dv": 1})
        assert a == b


# =============================================================================
# 5. load_affixes / clear_affix_cache
# =============================================================================


class TestLoadAffixes:
    def test_loads_real_yaml_into_affix_objects(self):
        affixes = load_affixes()
        assert isinstance(affixes, dict)
        assert len(affixes) >= 20
        assert all(isinstance(a, Affix) for a in affixes.values())
        sharp = affixes["of_sharpness"]
        assert sharp.name == "鋭利の"
        assert sharp.slot == "weapon"
        assert sharp.weight == 12
        assert sharp.tier == 1
        assert sharp.mods == {"dmg_bonus": 4, "hit_bonus": -1}
        curse = affixes["curse_of_thinness"]
        assert curse.is_curse is True
        assert curse.weight == 0

    def test_cache_returns_same_object(self):
        assert load_affixes() is load_affixes()

    def test_clear_cache_forces_reread(self, tmp_path):
        path = _write_affix_yaml(
            tmp_path / "affixes.yaml",
            "a_one:\n  name: A\n  slot: any\n  weight: 5\n  tier: 1\n  mods: {dv: 1}\n",
        )
        first = load_affixes(path)
        assert set(first) == {"a_one"}
        # キャッシュ中はファイルを書き換えても再読込されない
        _write_affix_yaml(
            tmp_path / "affixes.yaml",
            "a_one:\n  name: A\n  slot: any\n  weight: 5\n  tier: 1\n  mods: {dv: 1}\n"
            "b_two:\n  name: B\n  slot: any\n  weight: 5\n  tier: 1\n  mods: {pv: 1}\n",
        )
        assert load_affixes(path) is first
        clear_affix_cache()
        reread = load_affixes(path)
        assert reread is not first
        assert set(reread) == {"a_one", "b_two"}

    def test_invalid_path_returns_empty_dict(self, tmp_path):
        assert load_affixes(str(tmp_path / "missing_dir" / "nope.yaml")) == {}

    def test_non_dict_entries_skipped(self, tmp_path):
        path = _write_affix_yaml(
            tmp_path / "mixed.yaml",
            "good_one:\n  name: G\n  slot: any\n  weight: 5\n  tier: 1\n  mods: {dv: 1}\n"
            "scalar_entry: 42\n"
            "list_entry:\n- 1\n- 2\n",
        )
        affixes = load_affixes(path)
        assert set(affixes) == {"good_one"}
        assert affixes["good_one"].name == "G"

    def test_empty_yaml_returns_empty_dict(self, tmp_path):
        path = _write_affix_yaml(tmp_path / "empty.yaml", "")
        assert load_affixes(path) == {}


# =============================================================================
# 6. _affix_roll_count
# =============================================================================


class TestAffixRollCount:
    @staticmethod
    def _rand(value: float):
        return SimpleNamespace(random=lambda: value)

    def test_god_always_two(self):
        assert _affix_roll_count(QUALITY_GOD) == 2
        assert _affix_roll_count(QUALITY_GOD, self._rand(0.99)) == 2

    def test_miracle_and_good_one(self):
        assert _affix_roll_count(QUALITY_MIRACLE) == 1
        assert _affix_roll_count(QUALITY_GOOD) == 1

    def test_normal_probability_gate(self):
        assert _affix_roll_count(QUALITY_NORMAL, self._rand(0.0)) == 1
        assert _affix_roll_count(QUALITY_NORMAL, self._rand(0.29)) == 1
        assert _affix_roll_count(QUALITY_NORMAL, self._rand(0.3)) == 0
        assert _affix_roll_count(QUALITY_NORMAL, self._rand(0.99)) == 0

    def test_bad_never_gets_affixes(self):
        assert _affix_roll_count(QUALITY_BAD, self._rand(0.0)) == 0

    def test_default_rand_uses_random_module(self, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.1)
        assert _affix_roll_count(QUALITY_NORMAL) == 1
        monkeypatch.setattr(random, "random", lambda: 0.9)
        assert _affix_roll_count(QUALITY_NORMAL) == 0


# =============================================================================
# 7. roll_affixes
# =============================================================================


class TestRollAffixes:
    @staticmethod
    def _weapon(quality: str = QUALITY_NORMAL) -> Item:
        return Item("ロングソード", CAT_WEAPON, "🗡️", (200, 200, 200), quality=quality)

    def test_god_quality_applies_two_affixes(self):
        item = self._weapon(QUALITY_GOD)
        result = roll_affixes(item, rng=random.Random(42))
        assert result is item
        assert isinstance(item.affix_ids, tuple)
        assert len(item.affix_ids) == 2
        assert len(set(item.affix_ids)) == 2  # 同一接尾辞の重複なし
        affixes = load_affixes()
        names = [affixes[a].name for a in item.affix_ids]
        assert item.name == f"ロングソード [{names[0]}/{names[1]}]"

    def test_bad_quality_applies_none(self):
        item = self._weapon(QUALITY_BAD)
        roll_affixes(item, rng=random.Random(42))
        assert item.affix_ids == ()
        assert item.name == "ロングソード"

    def test_seeded_rng_is_deterministic(self):
        def run() -> Item:
            item = self._weapon(QUALITY_GOD)
            roll_affixes(item, rng=random.Random(42))
            return item

        a, b = run(), run()
        assert a.affix_ids == b.affix_ids
        assert a.name == b.name

    def test_quality_defaults_to_item_quality(self):
        item = self._weapon(QUALITY_GOD)
        roll_affixes(item, rng=random.Random(42))
        assert len(item.affix_ids) == 2

    def test_quality_argument_overrides_item_quality(self):
        item = self._weapon(QUALITY_BAD)
        roll_affixes(item, rng=random.Random(42), quality=QUALITY_GOOD)
        assert len(item.affix_ids) == 1

    def test_normal_quality_low_roll_applies_none(self):
        item = self._weapon(QUALITY_NORMAL)
        rng = SimpleNamespace(random=lambda: 0.99)
        roll_affixes(item, rng=rng)
        assert item.affix_ids == ()
        assert item.name == "ロングソード"

    def test_normal_quality_high_roll_applies_one(self):
        item = self._weapon(QUALITY_NORMAL)
        rng = SimpleNamespace(random=lambda: 0.0, uniform=lambda a, b: a)
        roll_affixes(item, rng=rng)
        assert len(item.affix_ids) == 1
        assert "[" in item.name

    def test_empty_pool_returns_item_unchanged(self, monkeypatch):
        monkeypatch.setattr("item_system.load_affixes", lambda: {})
        item = self._weapon(QUALITY_GOD)
        result = roll_affixes(item, rng=random.Random(42))
        assert result is item
        assert item.name == "ロングソード"
        assert getattr(item, "affix_ids", ()) == ()

    def test_applied_affixes_modify_item(self):
        item = self._weapon(QUALITY_GOD)
        roll_affixes(item, rng=random.Random(42))
        assert isinstance(item.affix_mods, dict)

    def test_candidates_exhausted_breaks_loop(self, monkeypatch):
        single = {
            "only_one": Affix(id="only_one", name="唯一", slot="any", weight=10, tier=1,
                              mods={"dv": 1}),
        }
        monkeypatch.setattr("item_system.load_affixes", lambda: single)
        item = self._weapon(QUALITY_GOD)
        roll_affixes(item, rng=random.Random(42), quality=QUALITY_GOD)
        assert item.affix_ids == ("only_one",)
        assert item.name == "ロングソード [唯一]"

    def test_pick_beyond_total_falls_back_to_last_candidate(self, monkeypatch):
        affixes = {
            "a_first": Affix(id="a_first", name="A", slot="any", weight=10, tier=1, mods={}),
            "b_last": Affix(id="b_last", name="B", slot="any", weight=10, tier=1, mods={}),
        }
        monkeypatch.setattr("item_system.load_affixes", lambda: affixes)
        item = self._weapon(QUALITY_GOOD)
        rng = SimpleNamespace(random=lambda: 0.0, uniform=lambda lo, hi: hi + 1000.0)
        roll_affixes(item, rng=rng, quality=QUALITY_GOOD)
        assert item.affix_ids == ("b_last",)
        assert item.name == "ロングソード [B]"


# =============================================================================
# 8. _apply_affix
# =============================================================================


class TestApplyAffix:
    @staticmethod
    def _affix(mods: dict) -> Affix:
        return Affix(id="t", name="T", slot="any", weight=5, tier=1, mods=mods)

    def test_numeric_fields_applied(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), dmg_bonus=1, hit_bonus=2, pv=3, dv=4)
        _apply_affix(item, self._affix({"dmg_bonus": 5, "hit_bonus": -1, "pv": 2, "dv": 1}))
        assert (item.dmg_bonus, item.hit_bonus, item.pv, item.dv) == (6, 1, 5, 5)

    def test_dynamic_keys_go_to_affix_mods(self):
        item = Item("鎧", CAT_ARMOR, "🥋", (160, 110, 60))
        _apply_affix(
            item,
            self._affix({"str": 3, "fire_resist": 50, "max_hp": -10, "speed": 5}),
        )
        assert item.affix_mods == {"str": 3, "fire_resist": 50, "max_hp": -10, "speed": 5}
        assert item.dmg_bonus == 0 and item.dv == 0  # 数値フィールドは変化しない

    def test_accumulates_on_repeat(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        affix = self._affix({"dmg_bonus": 2, "str": 4})
        _apply_affix(item, affix)
        _apply_affix(item, affix)
        assert item.dmg_bonus == 4
        assert item.affix_mods["str"] == 8

    def test_creates_affix_mods_dict_once(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        assert getattr(item, "affix_mods", None) is None
        _apply_affix(item, self._affix({"dv": 1}))
        assert item.affix_mods == {}
        _apply_affix(item, self._affix({"max_hp": 5}))
        assert item.affix_mods == {"max_hp": 5}

    def test_unknown_mod_key_is_ignored(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        _apply_affix(item, self._affix({"strength": 8}))
        assert item.affix_mods == {}
        assert item.dmg_bonus == 0


# =============================================================================
# 9. can_identify / identify
# =============================================================================


class TestIdentify:
    def test_can_identify_flag(self):
        identified = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        unidentified = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), identified=False)
        assert can_identify(identified) is False
        assert can_identify(unidentified) is True

    def test_identify_sets_flag_without_holder(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), identified=False)
        assert identify(item, 30) is item
        assert item.identified is True

    def test_identify_deducts_cost_from_gold_holder(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), identified=False)
        holder = GoldAttrHolder(gold=100)
        result = identify(item, 30, holder)
        assert result is item
        assert holder.gold == 70
        assert item.identified is True

    def test_insufficient_gold_leaves_item_unidentified(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), identified=False)
        holder = GoldAttrHolder(gold=10)
        result = identify(item, 30, holder)
        assert result is item
        assert item.identified is False
        assert holder.gold == 10

    def test_already_identified_returns_unchanged(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        holder = GoldAttrHolder(gold=100)
        result = identify(item, 30, holder)
        assert result is item
        assert holder.gold == 100


# =============================================================================
# 10. use_item
# =============================================================================


class TestUseItem:
    @staticmethod
    def _item(category: str, name: str, **kw) -> Item:
        return Item(name, category, "🧪", (200, 200, 200), **kw)

    def test_heal_potion_restores_hp(self):
        user = make_user(hp=50, max_hp=200)
        item = self._item(CAT_POTION, "軽傷治療のポーション", heal_amount=35)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.hp == 85
        assert msg == "Heroは軽傷治療のポーションを飲み、HPが35回復した！"

    def test_heal_caps_at_max_hp(self):
        user = make_user(hp=70, max_hp=80)
        item = self._item(CAT_POTION, "軽傷治療のポーション", heal_amount=35)
        ok, _ = use_item(user, item)
        assert ok is True
        assert user.hp == 80

    def test_heal_without_max_hp_uses_large_default(self):
        user = SimpleNamespace(name="Hero", hp=1)
        item = self._item(CAT_POTION, "軽傷治療のポーション", heal_amount=35)
        ok, _ = use_item(user, item)
        assert user.hp == 36

    def test_poison_cure_calls_remove_status(self):
        user = StatusUser(result=True)
        item = self._item(CAT_POTION, "毒消しのポーション", heal_amount=0)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.calls[0] == "poison"
        assert "治まった" in msg

    def test_poison_cure_falls_back_to_japanese_keys(self):
        user = StatusUser(result=None)
        item = self._item(CAT_POTION, "毒消し", heal_amount=0)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.calls == ["poison", "毒", "burn", "炎上"]
        assert msg.endswith("飲んだ。")

    def test_poison_cure_by_item_id(self):
        user = StatusUser(result=True)
        item = self._item(CAT_POTION, "不思議な薬", heal_amount=0)
        item.item_id = "cure_poison"
        ok, msg = use_item(user, item)
        assert ok is True
        assert "治まった" in msg

    def test_poison_cure_without_remove_status_still_succeeds(self):
        user = SimpleNamespace(name="Hero")
        item = self._item(CAT_POTION, "毒消しのポーション", heal_amount=0)
        ok, msg = use_item(user, item)
        assert ok is True
        assert "飲んだ" in msg

    def test_mana_potion_restores_mp_capped(self):
        user = make_user(mp=10, max_mp=45)
        item = self._item(CAT_POTION, "魔力回復のポーション", heal_amount=0)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.mp == 45
        assert "MPが回復" in msg

    def test_mana_potion_below_cap(self):
        user = make_user(mp=10, max_mp=200)
        item = self._item(CAT_POTION, "魔力回復のポーション", heal_amount=0)
        ok, _ = use_item(user, item)
        assert ok is True
        assert user.mp == 50

    def test_mana_potion_by_item_id(self):
        user = make_user(mp=0, max_mp=100)
        item = self._item(CAT_POTION, "不思議な薬", heal_amount=0)
        item.item_id = "mana"
        ok, _ = use_item(user, item)
        assert ok is True
        assert user.mp == 40

    def test_food_restores_hunger_capped(self):
        user = make_user(hunger=9000)
        item = self._item(CAT_FOOD, "旅糧", nutrition=3200)
        ok, msg = use_item(user, item)
        assert ok is True
        assert user.hunger == 10000
        assert msg == "Heroは旅糧を食べた。"

    def test_food_below_cap(self):
        user = make_user(hunger=1000)
        item = self._item(CAT_FOOD, "パン", nutrition=1500)
        ok, _ = use_item(user, item)
        assert ok is True
        assert user.hunger == 2500

    def test_food_without_hunger_attribute_still_succeeds(self):
        user = SimpleNamespace(name="Hero")
        item = self._item(CAT_FOOD, "パン", nutrition=1500)
        ok, msg = use_item(user, item)
        assert ok is True
        assert msg == "Heroはパンを食べた。"

    def test_unknown_category_returns_failure(self):
        item = self._item(CAT_TOOL, "工具")
        ok, msg = use_item(make_user(), item)
        assert (ok, msg) == (False, "使用できないアイテムです。")

    def test_potion_without_effect_returns_failure(self):
        item = self._item(CAT_POTION, "水", heal_amount=0)
        ok, msg = use_item(make_user(), item)
        assert (ok, msg) == (False, "使用できないアイテムです。")


# =============================================================================
# 補足: Item / Inventory 基本動作 (モジュール全体のカバレッジ確保)
# =============================================================================


class TestItemBasics:
    def test_weight_uses_material_multiplier_and_count(self):
        iron = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_weight=3.5, material="iron")
        steel = Item(
            "剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_weight=3.5, material="steel", count=2
        )
        assert iron.weight == 3.5
        assert steel.weight == pytest.approx(7.7)

    def test_unknown_material_uses_default_multipliers(self):
        item = Item(
            "x", CAT_TOOL, "🔧", (100, 100, 100), base_weight=2.0, base_value=10,
            material="unobtainium",
        )
        assert item.weight == 2.0
        assert item.value == 10

    def test_value_multiplies_material_and_quality(self):
        item = Item(
            "盾", CAT_SHIELD, "🛡️", (180, 180, 180), base_value=90,
            material="steel", quality=QUALITY_GOOD,
        )
        assert item.value == 187  # int(90 * 1.4) = 125 (FP切り捨て) → int(125 * 1.5)

    def test_value_multiplies_count(self):
        item = Item("薬", CAT_POTION, "🧪", (255, 100, 100), base_value=40, count=3)
        assert item.value == 120

    def test_display_name_variants(self):
        plain = Item("長剣", CAT_WEAPON, "🗡️", (200, 200, 200), material="iron")
        assert "鉄の長剣" in plain.display_name
        cursed = Item("長剣", CAT_WEAPON, "🗡️", (200, 200, 200), cursed=True)
        assert "【呪】" in cursed.display_name
        hidden = Item("長剣", CAT_WEAPON, "🗡️", (200, 200, 200), identified=False)
        assert "(未鑑定)" in hidden.display_name
        stack = Item("パン", CAT_FOOD, "🍞", (210, 180, 100), count=3)
        assert " x3" in stack.display_name

    def test_enchantments_alias(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        assert item.enchantments == []
        item.enchantments = ["fire"]
        assert item.enchants == ("fire",)
        assert item.enchantments == ["fire"]

    def test_to_dict_from_dict_roundtrip(self):
        item = Item(
            "長剣", CAT_WEAPON, "🗡️", (200, 200, 200), base_value=120, count=2,
            quality=QUALITY_GOD, cursed=True, locked=True, enchants=("fire",),
        )
        item.rot_progress = 10
        item.is_cooling = True
        restored = Item.from_dict(item.to_dict())
        assert restored.item_id == item.item_id
        assert restored.name == item.name
        assert restored.category == item.category
        assert restored.color == item.color
        assert restored.base_value == 120
        assert restored.count == 2
        assert restored.quality == QUALITY_GOD
        assert restored.cursed is True
        assert restored.locked is True
        assert restored.enchants == ("fire",)
        assert restored.rot_progress == 10
        assert restored.is_cooling is True

    def test_from_dict_defaults(self):
        item = Item.from_dict({})
        assert item.name == "Unknown Item"
        assert item.category == CAT_TOOL
        assert item.color == (255, 255, 255)
        assert item.identified is True


class TestItemRot:
    def test_non_food_never_rots(self):
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        assert item.tick_rot(99999) is None
        assert item.rot_progress == 0

    def test_food_below_threshold(self):
        item = Item("パン", CAT_FOOD, "🍞", (210, 180, 100), nutrition=1500)
        assert item.tick_rot(4999) is None
        assert item.rot_progress == 4999
        assert item.name == "パン"

    def test_food_rots_at_threshold(self):
        item = Item("パン", CAT_FOOD, "🍞", (210, 180, 100), nutrition=1500)
        assert item.tick_rot(5000) == "腐ったパン が腐り始めた！"
        assert item.name == "腐ったパン"
        assert item.color == (120, 80, 40)
        assert item.nutrition == 1000

    def test_already_rotten_does_not_double(self):
        item = Item("パン", CAT_FOOD, "🍞", (210, 180, 100), nutrition=1500)
        item.tick_rot(5000)
        assert item.tick_rot(5000) is None
        assert item.nutrition == 1000

    def test_cooling_suspends_rot(self):
        item = Item("パン", CAT_FOOD, "🍞", (210, 180, 100), nutrition=1500)
        item.is_cooling = True
        assert item.tick_rot(5000) is None
        assert item.rot_progress == 0


class TestItemStacking:
    @staticmethod
    def _potion(**kw) -> Item:
        return Item("回復薬", CAT_POTION, "🧪", (255, 100, 100), **kw)

    def test_identical_potions_stack(self):
        assert self._potion().can_stack_with(self._potion()) is True

    def test_differing_attribute_prevents_stack(self):
        base = self._potion()
        other = self._potion()
        other.identified = False
        assert base.can_stack_with(other) is False
        assert base.can_stack_with(self._potion(locked=True)) is False
        assert base.can_stack_with(self._potion(cursed=True)) is False
        assert base.can_stack_with(self._potion(quality=QUALITY_GOOD)) is False

    def test_weapons_never_stack(self):
        a = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        assert a.can_stack_with(Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))) is False


class TestEquipmentSlot:
    def test_can_equip(self):
        slot = EquipmentSlot("main_hand", "利き手")
        item = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        assert slot.can_equip(item) is True
        slot.disabled = True
        assert slot.can_equip(item) is False


class TestInventory:
    @staticmethod
    def _potion(**kw) -> Item:
        return Item("回復薬", CAT_POTION, "🧪", (255, 100, 100), base_value=40, **kw)

    # --- add / weight ---

    def test_add_new_item(self):
        inv = Inventory()
        ok, msg = inv.add_item(self._potion())
        assert ok is True
        assert "手に入れた" in msg
        assert len(inv.items) == 1

    def test_add_stackable_duplicates(self):
        inv = Inventory()
        inv.add_item(self._potion())
        ok, msg = inv.add_item(self._potion())
        assert ok is True
        assert "スタック" in msg
        assert len(inv.items) == 1
        assert inv.items[0].count == 2

    def test_add_full_inventory(self):
        inv = Inventory(max_items=1)
        inv.add_item(self._potion())
        ok, msg = inv.add_item(Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200)))
        assert ok is False
        assert "いっぱい" in msg

    def test_total_weight_and_overburdened(self):
        inv = Inventory(max_weight=5.0)
        rock = Item("岩", CAT_ORE, "🪨", (120, 120, 120), base_weight=6.0)
        inv.add_item(rock)
        assert inv.total_weight == 6.0
        assert inv.is_overburdened() is True
        rock.base_weight = 1.0
        assert inv.total_weight == 1.0
        assert inv.is_overburdened() is False

    def test_get_slot_and_equipment_view(self):
        inv = Inventory()
        assert inv.get_slot("main_hand").slot_name == "main_hand"
        assert inv.get_slot("nope") is None
        assert set(inv.equipment) == {"main_hand", "off_hand", "head", "body", "ring1", "ring2"}

    # --- equip / unequip ---

    def test_equip_and_unequip(self):
        inv = Inventory()
        weapon = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        ok, msg = inv.equip(weapon, "main_hand")
        assert ok is True
        assert inv.get_slot("main_hand").item is weapon
        ok, msg = inv.unequip(weapon)
        assert ok is True
        assert inv.get_slot("main_hand").item is None

    def test_equip_invalid_slot(self):
        inv = Inventory()
        ok, msg = inv.equip(Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200)), "tail")
        assert ok is False

    def test_equip_disabled_slot(self):
        inv = Inventory()
        inv.get_slot("off_hand").disabled = True
        ok, msg = inv.equip(Item("盾", CAT_SHIELD, "🛡️", (180, 180, 180)), "off_hand")
        assert ok is False
        assert "変異" in msg

    def test_equip_occupied_slot_swaps(self):
        inv = Inventory()
        first = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        second = Item("槍", CAT_WEAPON, "🔱", (190, 190, 150))
        inv.equip(first, "main_hand")
        ok, msg = inv.equip(second, "main_hand")
        assert ok is True
        assert inv.get_slot("main_hand").item is second

    def test_unequip_cursed_fails(self):
        inv = Inventory()
        weapon = Item("呪剣", CAT_WEAPON, "🗡️", (200, 200, 200), cursed=True)
        inv.equip(weapon, "main_hand")
        ok, msg = inv.unequip(weapon)
        assert ok is False
        assert "呪われており" in msg

    def test_unequip_not_equipped(self):
        inv = Inventory()
        ok, msg = inv.unequip(Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200)))
        assert ok is False

    # --- remove ---

    def test_remove_item_absent(self):
        inv = Inventory()
        assert inv.remove_item(Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))) is None

    def test_remove_item_whole(self):
        inv = Inventory()
        item = self._potion()
        inv.add_item(item)
        assert inv.remove_item(item) is item
        assert item not in inv.items

    def test_remove_item_partial_creates_copy(self):
        inv = Inventory()
        item = self._potion(count=5)
        inv.add_item(item)
        dropped = inv.remove_item(item, 2)
        assert dropped is not item
        assert dropped.count == 2
        assert dropped.item_id != item.item_id
        assert item.count == 3
        assert item in inv.items

    def test_remove_item_equipped_unequips_first(self):
        inv = Inventory()
        weapon = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        inv.add_item(weapon)
        inv.equip(weapon, "main_hand")
        assert inv.remove_item(weapon) is weapon
        assert inv.get_slot("main_hand").item is None
        assert weapon not in inv.items

    def test_remove_equipped_cursed_returns_none(self):
        inv = Inventory()
        weapon = Item("呪剣", CAT_WEAPON, "🗡️", (200, 200, 200), cursed=True)
        inv.add_item(weapon)
        inv.equip(weapon, "main_hand")
        assert inv.remove_item(weapon) is None
        assert weapon in inv.items
        assert inv.get_slot("main_hand").item is weapon

    def test_equip_over_cursed_occupied_slot_fails(self):
        inv = Inventory()
        cursed = Item("呪剣", CAT_WEAPON, "🗡️", (200, 200, 200), cursed=True)
        inv.equip(cursed, "main_hand")
        ok, msg = inv.equip(Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200)), "main_hand")
        assert ok is False
        assert "呪われており" in msg
        assert inv.get_slot("main_hand").item is cursed

    # --- rot ---

    def test_tick_food_rot(self):
        inv = Inventory()
        inv.add_item(Item("パン", CAT_FOOD, "🍞", (210, 180, 100), nutrition=1500))
        assert inv.tick_food_rot(5000) == ["腐ったパン が腐り始めた！"]

    def test_tick_food_rot_no_logs(self):
        inv = Inventory()
        inv.add_item(self._potion())
        assert inv.tick_food_rot(100) == []

    # --- filter / sort ---

    def test_filter_items(self):
        inv = Inventory()
        sword = Item("剣", CAT_WEAPON, "🗡️", (200, 200, 200))
        armor = Item("鎧", CAT_ARMOR, "🥋", (160, 110, 60))
        potion = self._potion()
        bread = Item("パン", CAT_FOOD, "🍞", (210, 180, 100))
        for it in (sword, armor, potion, bread):
            inv.add_item(it)
        assert inv.filter_items("equipment") == [sword, armor]
        assert inv.filter_items("consumable") == [potion, bread]
        assert inv.filter_items(CAT_ARMOR) == [armor]
        assert inv.filter_items("rod") == []

    def test_sort_items_quality_locked_first(self):
        inv = Inventory()
        god = Item("神剣", CAT_WEAPON, "🗡️", (200, 200, 200), quality=QUALITY_GOD)
        bad = Item("粗剣", CAT_WEAPON, "🗡️", (200, 200, 200), quality=QUALITY_BAD)
        locked = Item("普剣", CAT_WEAPON, "🗡️", (200, 200, 200), quality=QUALITY_NORMAL)
        for it in (bad, god, locked):
            inv.add_item(it)
        locked.locked = True
        assert inv.sort_items("quality") == [locked, bad, god]
        assert inv.sort_items("quality", reverse=True) == [locked, god, bad]

    def test_sort_items_name_value_weight(self):
        inv = Inventory()
        a = Item("あ", CAT_POTION, "🧪", (255, 100, 100), base_value=10)
        b = Item("い", CAT_POTION, "🧪", (255, 100, 100), base_value=99, base_weight=2.0)
        for it in (b, a):
            inv.add_item(it)
        assert inv.sort_items("name") == [a, b]
        assert inv.sort_items("value", reverse=True) == [b, a]
        assert inv.sort_items("weight") == [a, b]
        assert inv.sort_items("weight", reverse=True) == [b, a]
        assert inv.sort_items("bogus_key") == [a, b]  # 不明キーは名前順フォールバック

    # --- sell / destroy / lock ---

    def test_can_sell(self):
        inv = Inventory()
        plain = self._potion()
        locked = self._potion()
        locked.locked = True
        cursed = Item("呪薬", CAT_POTION, "🧪", (255, 100, 100), cursed=True)
        equipped = self._potion()
        for it in (plain, locked, cursed, equipped):
            inv.add_item(it)
        inv.equip(equipped, "main_hand")
        assert inv.can_sell(plain)[0] is True
        ok, msg = inv.can_sell(locked)
        assert ok is False and "ロック" in msg
        ok, msg = inv.can_sell(cursed)
        assert ok is False and "呪われている" in msg
        ok, msg = inv.can_sell(equipped)
        assert ok is False and "装備中" in msg

    def test_can_destroy(self):
        inv = Inventory()
        plain = self._potion()
        locked = self._potion()
        locked.locked = True
        cursed = Item("呪薬", CAT_POTION, "🧪", (255, 100, 100), cursed=True)
        equipped = self._potion()
        for it in (plain, locked, cursed, equipped):
            inv.add_item(it)
        inv.equip(equipped, "main_hand")
        assert inv.can_destroy(plain)[0] is True
        assert inv.can_destroy(locked)[0] is False
        assert inv.can_destroy(equipped)[0] is False
        assert inv.can_destroy(cursed)[0] is True  # 呪いは破棄できる

    def test_toggle_lock(self):
        inv = Inventory()
        item = self._potion()
        inv.add_item(item)
        assert inv.toggle_lock(item) is True
        assert item.locked is True
        assert inv.toggle_lock(item) is False
        assert inv.toggle_lock(self._potion()) is False  # 所持外アイテム

    # --- stat bonuses / elements ---

    def test_get_stat_bonuses(self):
        inv = Inventory()
        armor = Item("鎧", CAT_ARMOR, "🥋", (160, 110, 60))
        armor.enchants = (
            Enchant("stat_bonus", "str", 3),
            Enchant("combat_bonus", "dmg", 2),
            Enchant("stat_bonus", None, 5),  # target_stat 無しは無視
        )
        inv.equip(armor, "body")
        assert inv.get_stat_bonuses() == {"str": 3, "dmg": 2}

    def test_get_stat_bonuses_empty(self):
        assert Inventory().get_stat_bonuses() == {}

    def test_get_weapon_element_damages(self):
        inv = Inventory()
        weapon = Item("炎剣", CAT_WEAPON, "🗡️", (255, 100, 100))
        weapon.enchants = (
            Enchant("stat_bonus", "str", 1),
            Enchant("element_damage", None, 5, element="fire"),
        )
        inv.equip(weapon, "main_hand")
        assert inv.get_weapon_element_damages() == [("fire", 5)]

    def test_get_weapon_element_damages_no_weapon(self):
        inv = Inventory()
        inv.equip(Item("鎧", CAT_ARMOR, "🥋", (160, 110, 60)), "body")
        assert inv.get_weapon_element_damages() == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
