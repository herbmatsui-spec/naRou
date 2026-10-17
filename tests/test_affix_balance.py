"""接尾辞バランス検証テスト (T32 案B: 利得/代償バランス再調整)

data/item_affixes.yaml の全戦闘系接尾辞について
- 利得/代償比率が AFFIX_BALANCE_RATIO_LIMIT (1.5) 以内であること
- 形骸化した代償 (適用時に無視されるキー/非消費ステータスの減少) が無いこと
- 品質連動ロールが仕様通り (GOD品は必ず2個 / BAD品は禁止) であること
を検証する。
"""

from __future__ import annotations

import os
import random
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import QUALITY_BAD, QUALITY_GOD  # noqa: E402
from item_generator import (  # noqa: E402
    AFFIX_BALANCE_RATIO_LIMIT,
    _affix_split,
    affix_balance_report,
)
from item_system import (  # noqa: E402
    Affix,
    Item,
    _affix_roll_count,
    _apply_affix,
    clear_affix_cache,
    load_affixes,
    roll_affixes,
)


@pytest.fixture(autouse=True)
def _repo_root_cwd_and_cache():
    """data/*.yaml は相対パスで読まれるため、常にリポジトリルートで実行する"""
    old = os.getcwd()
    os.chdir(_ROOT)
    clear_affix_cache()
    yield
    os.chdir(old)
    clear_affix_cache()


def _report() -> dict:
    """実データ (data/item_affixes.yaml) に対するバランスレポート"""
    return affix_balance_report()


# =============================================================================
# 1. 利得/代償比率
# =============================================================================


class TestAffixBalance:
    """T32 案B: 利得/代償の比率検証"""

    def test_report_covers_all_non_curse_affixes(self):
        """レポートが呪い以外の全接尾辞を網羅する"""
        report = _report()
        non_curse_ids = {
            affix_id for affix_id, a in load_affixes().items() if not a.is_curse
        }
        assert set(report["affixes"]) == non_curse_ids
        assert len(non_curse_ids) >= 19, "戦闘系接尾辞が減っていないか"

    def test_gain_cost_ratio_within_limit(self):
        """全戦闘系接尾辞の利得/代償比率が閾値 (1.5) 以内"""
        report = _report()
        over = {
            affix_id: entry["ratio"]
            for affix_id, entry in report["affixes"].items()
            if entry["ratio"] > AFFIX_BALANCE_RATIO_LIMIT
        }
        assert not over, f"利得が代償を大きく上回る接尾辞: {over}"

    def test_every_affix_has_both_gain_and_cost(self):
        """全戦闘系接尾辞が利得と代償を両方持つ (代償ゼロは不均衡)"""
        report = _report()
        costless = [
            (affix_id, entry["gain"])
            for affix_id, entry in report["affixes"].items()
            if entry["cost"] <= 0
        ]
        assert not costless, f"代償を持たない接尾辞: {costless}"

    def test_gain_is_not_dwarfed_by_cost(self):
        """代償過多 (利得が代償の半分未満) も不均衡として検出する"""
        report = _report()
        crushed = {
            affix_id: entry["ratio"]
            for affix_id, entry in report["affixes"].items()
            if entry["ratio"] < 0.5
        }
        assert not crushed, f"代償が利得を大きく上回る接尾辞: {crushed}"

    def test_overall_ratio_is_roughly_balanced(self):
        """全体合計でも利得が代償の 1.5 倍を超えない"""
        report = _report()
        assert report["total_cost"] > 0
        assert report["overall_ratio"] <= AFFIX_BALANCE_RATIO_LIMIT

    def test_ratio_threshold_is_1_5(self):
        assert AFFIX_BALANCE_RATIO_LIMIT == 1.5


# =============================================================================
# 2. 形骸化した代償の排除
# =============================================================================


class TestVestigialCostsRemoved:
    """T32 案B: 代償は実効ステータスに再定義されていること"""

    # 実戦で消費されるステータス (戦闘解決の参照先) + 装備数値フィールド
    # (fire_resist/cold_resist は get_elemental_resistance 経由で被ダメ計算に消費される)
    _EFFECTIVE_KEYS = {
        "dmg_bonus", "hit_bonus", "pv", "dv", "max_hp", "speed",
        "str", "endurance", "dexterity", "perception", "magic",
        "hp_regen", "mp_regen",
        "fire_resist", "cold_resist", "fire_damage", "ice_damage",
    }

    def test_costs_target_effective_stats(self):
        """代償 (負値 mods) は実効ステータスに限る"""
        vestigial = []
        for affix_id, a in load_affixes().items():
            if a.is_curse:
                continue
            for key, value in a.mods.items():
                if value < 0 and key not in self._EFFECTIVE_KEYS:
                    vestigial.append((affix_id, key, value))
        assert not vestigial, f"実効性のない代償が残っている: {vestigial}"

    def test_no_unknown_mod_keys(self):
        """適用時に無視される未定義 mods キーは存在してはならない

        過去に of_wisdom の代償 (strength) / of_the_titan の利得 (strength) が
        item_system._apply_affix の動的キーに無く空振りしていたため、
        T32 案B で str に正常化した。
        """
        report = _report()
        unknown = {
            affix_id: entry["unknown_keys"]
            for affix_id, entry in report["affixes"].items()
            if entry["unknown_keys"]
        }
        assert not unknown, f"適用時に無視される mods キー: {unknown}"

    def test_apply_affix_ignores_strength_key(self):
        """回帰抑止: strength キーは item_system の動的キーに存在しない"""
        item = Item("剣", "weapon", "/", (200, 200, 200))
        _apply_affix(
            item,
            Affix(id="t", name="T", slot="any", weight=1, tier=1,
                  mods={"strength": 8}),
        )
        assert item.affix_mods == {}

    def test_vulture_keeps_readme_example_mods(self):
        """README 記載の《秃鷹の》(筋力+3/回避-2) の主な損得が維持される"""
        vulture = load_affixes()["of_the_vulture"]
        assert vulture.mods["str"] == 3
        assert vulture.mods["dv"] == -2


# =============================================================================
# 3. 品質連動ロール (README: GOD品は必ず2個、BAD品は禁止)
# =============================================================================


class TestQualityLinkedRolling:
    """品質に連動した接尾辞ロール仕様"""

    @staticmethod
    def _weapon(quality: str) -> Item:
        return Item("ロングソード", "weapon", "/", (200, 200, 200), quality=quality)

    def test_god_quality_always_rolls_two_affixes(self):
        """GOD品はシードによらず必ず2個の接尾辞を持つ"""
        for seed in range(30):
            random.seed(seed)
            item = self._weapon(QUALITY_GOD)
            roll_affixes(item, quality=QUALITY_GOD)
            assert len(item.affix_ids) == 2, f"GOD品の接尾辞数が2でない: seed={seed}"

    def test_bad_quality_never_gets_affixes(self):
        """BAD品はシードによらず接尾辞禁止"""
        for seed in range(30):
            random.seed(seed)
            item = self._weapon(QUALITY_BAD)
            roll_affixes(item, quality=QUALITY_BAD)
            assert item.affix_ids == (), f"BAD品に接尾辞が付与された: seed={seed}"

    def test_affix_roll_count_table(self):
        assert _affix_roll_count(QUALITY_GOD) == 2
        assert _affix_roll_count(QUALITY_BAD) == 0


# =============================================================================
# 4. affix_balance_report / _affix_split の動作
# =============================================================================


class TestAffixBalanceReport:
    """集計関数そのものの動作"""

    def test_affix_split_classifies_signs(self):
        gain, cost, unknown = _affix_split({"dmg_bonus": 4, "pv": -2, "typo_key": 9})
        assert gain == pytest.approx(4.0)
        assert cost == pytest.approx(1.6)
        assert unknown == ["typo_key"]

    def test_affix_split_reports_invalid_strength_key(self):
        _, _, unknown = _affix_split({"strength": 8})
        assert unknown == ["strength"]

    def test_report_counts_curses_out(self):
        """呪い (cursed=true) はレポート対象外"""
        report = _report()
        assert "curse_of_thinness" not in report["affixes"]
        assert "curse_of_sloth" not in report["affixes"]

    def test_report_ratio_is_gain_over_cost(self):
        """ratio は利得/代償の比と一致する"""
        report = _report()
        for entry in report["affixes"].values():
            if entry["cost"] > 0:
                assert entry["ratio"] == pytest.approx(
                    entry["gain"] / entry["cost"], abs=0.01
                )

    def test_report_accepts_explicit_path(self):
        """path 引数で明示読み込みできる"""
        path = os.path.join(_ROOT, "data", "item_affixes.yaml")
        report = affix_balance_report(path)
        assert "of_sharpness" in report["affixes"]

    def test_report_is_json_dumpable(self):
        """CLI (python3 -c) で json.dumps できる"""
        import json

        text = json.dumps(_report(), ensure_ascii=False)
        assert "of_sharpness" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
