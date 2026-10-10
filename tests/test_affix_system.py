"""接尾辞 (Affix) システムテスト (Phase 3 Step 57-58)"""

from __future__ import annotations

import os
import random
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import (  # noqa: E402
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from item_system import (  # noqa: E402
    Affix,
    Item,
    clear_affix_cache,
    load_affixes,
    roll_affixes,
)

# 戦闘に影響する mods キー (利得と代償のペア検証に使用)
_BUFF_KEYS = {"dmg_bonus", "hit_bonus", "pv", "dv", "hp_regen", "mp_regen",
              "life_steal", "thorns", "stealth", "fire_resist", "cold_resist",
              "fire_damage", "ice_damage", "max_hp"}
_ATTR_KEYS = {"str", "endurance", "dexterity", "perception", "learning",
              "will", "magic", "charisma", "speed"}


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_affix_cache()
    yield
    clear_affix_cache()


def _mods_values(mods: dict[str, int]) -> tuple[list[int], list[int]]:
    """mods を (正値リスト, 負値リスト) に分解する"""
    positives = [v for v in mods.values() if v > 0]
    negatives = [v for v in mods.values() if v < 0]
    return positives, negatives


class TestAffixData:
    """Step 57.4: 接尾辞データ定義の整合性"""

    def test_affix_schema_is_valid(self):
        """全接尾辞が必須フィールド (name/slot/weight/tier/mods) を持つ"""
        affixes = load_affixes()
        assert len(affixes) >= 20, f"接尾辞は20種以上必要: {len(affixes)}"

        for affix_id, a in affixes.items():
            assert a.name, f"{affix_id}: name が空"
            assert a.slot in ("weapon", "armor", "any"), f"{affix_id}: 不正な slot {a.slot}"
            assert a.weight >= 0, f"{affix_id}: 負の weight"
            assert isinstance(a.mods, dict) and a.mods, f"{affix_id}: mods が空"
            if a.cursed:
                assert a.weight == 0, f"{affix_id}: 呪いはロール対象外 (weight=0) であるべき"

    def test_non_curse_affixes_trade_off_two_ways(self):
        """Step 58.4: 戦闘系接尾辞は必ず利得と代償の両方を持つ"""
        affixes = load_affixes()
        combat_affixes = {k: a for k, a in affixes.items() if not a.is_curse}
        assert combat_affixes, "戦闘系接尾辞が存在しない"

        bad = []
        for affix_id, a in combat_affixes.items():
            positives, negatives = _mods_values(a.mods)
            # 利得: 正値 or フィールドボーナス増加 (pv/dv/dmg_bonus/hit_bonus の負値は「軽量鎧」等の正当な利得)
            has_gain = bool(positives) or any(
                k in ("dv", "speed") and v > 0 or k in ("pv", "dmg_bonus", "hit_bonus") and v > 0
                for k, v in a.mods.items()
            )
            has_cost = bool(negatives)
            if not (has_gain and has_cost):
                bad.append((affix_id, dict(a.mods)))

        assert not bad, f"損得の片方しかない接尾辞: {bad}"


class TestAffixRolling:
    """Step 58: 品質連動ロール"""

    def _weapon(self) -> Item:
        return Item("longsword", "weapon", "/", (200, 200, 200), quality=QUALITY_NORMAL)

    def test_item_generation_attaches_affixes(self):
        """Step 58.3: 生成経路 (data_manager.get_random_item_for_floor) が接尾辞を載せる"""
        from data_manager import DataManager

        dm = DataManager()
        attached = 0
        trials = 60
        for i in range(trials):
            random.seed(i)
            item = dm.get_random_item_for_floor(15)
            if getattr(item, "affix_ids", ()):
                attached += 1
        # GOD/MIRACLE/GOOD は必須、NORMAL は 30% なので全体で >20% が付与されるはず
        assert attached > trials * 0.15, (
            f"生成経路で接尾辞が付与されていない: {attached}/{trials}"
        )

    def test_god_quality_always_gets_two_affixes(self):
        """Step 58.2: QUALITY_GOD は必ず2個の接尾辞を持つ"""
        results = set()
        for seed in range(20):
            random.seed(seed)
            item = self._weapon()
            roll_affixes(item, quality=QUALITY_GOD)
            results.add(len(getattr(item, "affix_ids", ())))
        assert results == {2}, f"GOD品の接尾辞数: {results} (期待: 常に2)"

    def test_bad_quality_never_gets_affixes(self):
        """Step 58.2: QUALITY_BAD は接尾辞禁止"""
        for seed in range(20):
            random.seed(seed)
            item = self._weapon()
            roll_affixes(item, quality=QUALITY_BAD)
            assert not getattr(item, "affix_ids", ()), f"BAD品に接尾辞が付いた (seed={seed})"

    def test_affixes_visible_in_item_name(self):
        """Step 66.2 前提: 接尾辞が表示名に出る (同一基底の比較可能性)"""
        random.seed(7)
        item = self._weapon()
        roll_affixes(item, quality=QUALITY_GOD)
        assert getattr(item, "affix_ids", ()), "前提: 接尾辞が付与されていること"
        assert "[" in item.name, f"表示名に接尾辞が出ていない: {item.name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
