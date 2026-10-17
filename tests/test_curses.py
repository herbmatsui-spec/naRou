"""呪い (Curses) テスト (Phase 3 Step 62)"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from item_system import Item, load_affixes  # noqa: E402


class TestCurses:
    """Step 62: 呪いシステム"""

    def test_cursed_item_has_a_named_penalty(self):
        """Step 62.3: 呪い接尾辞は必ず名前付きの具体的ペナルティを持つ"""
        affixes = load_affixes()
        curses = {k: a for k, a in affixes.items() if a.is_curse}

        assert curses, "呪い接尾辞が定義されていない"
        for curse_id, c in curses.items():
            assert c.name, f"{curse_id}: 呪いに名前が無い"
            assert c.mods, f"{curse_id}: 呪いにペナルティ (mods) が無い"
            # ペナルティは数値で観測できること (文字列ではなく)
            assert all(isinstance(v, int) and v != 0 for v in c.mods.values()), (
                f"{curse_id}: ペナルティが数値でない: {c.mods}"
            )

    def test_cursed_item_is_never_better_than_its_clean_twin(self):
        """Step 62.4: 呪い品は呪いの無い同一品より良いことは決してない"""
        affixes = load_affixes()
        curses = [a for a in affixes.values() if a.is_curse]
        assert curses, "前提: 呪い接尾辞が存在すること"

        for curse in curses:
            # 呪いの mods に正値 (利得) が一つでもあれば「呪いなのに強い」ことになる
            gains = [v for v in curse.mods.values() if v > 0]
            assert not gains, (
                f"{curse.id}: 呪いに利得が含まれている {curse.mods} — 呪いは純代償であるべき"
            )

    def test_curse_penalty_is_numeric(self):
        """Step 62.4 補足: 呪いの影響が文字列ではなく数値で観測できる"""
        from item_system import _apply_affix

        affixes = load_affixes()
        curse_of_thinness = affixes.get("curse_of_thinness")
        assert curse_of_thinness is not None, "curse_of_thinness が未定義"

        item = Item("ring_mail", "armor", "]", (150, 150, 150))
        base_dv = item.dv
        _apply_affix(item, curse_of_thinness)
        assert item.dv == base_dv + curse_of_thinness.mods["dv"], (
            f"呪いペナルティが数値として適用されていない: {base_dv} -> {item.dv}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
