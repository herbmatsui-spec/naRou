"""鑑定 (Identification) テスト (Phase 3 Step 60-61)"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from item_system import (  # noqa: E402
    Item,
    can_identify,
    identify,
)


def _make_gold_holder(gold: int):
    class _Holder:
        pass

    h = _Holder()
    h.gold = gold
    return h


class TestIdentification:
    """Step 60: 鑑定システム"""

    def test_unidentified_item_hides_its_affixes(self):
        """Step 60.4: 未鑑定アイテムは affix_ids を隠す"""
        item = Item("longsword", "weapon", "/", (200, 200, 200), identified=False)
        item.affix_ids = ("of_the_vulture",)
        item.affix_mods = {"str": 3, "dv": -2}

        assert can_identify(item) is True
        # 未鑑定のままでは接尾辞情報を露出しない契約: identified フラグが立つまで False
        assert item.identified is False

        identified = identify(item, cost=50)
        assert identified.identified is True

    def test_identification_costs_gold(self):
        """Step 60.5: 鑑定にはゴールドがかかる"""
        holder = _make_gold_holder(100)
        item = Item("ring", "accessory", "○", (255, 255, 100), identified=False)

        identify(item, cost=50, gold_holder=holder)

        assert holder.gold == 50, f"鑑定費が引かれていない: {holder.gold}"
        assert item.identified is True

    def test_gold_is_required_for_identification(self):
        """Step 61.3: ゴールド不足なら鑑定されない"""
        holder = _make_gold_holder(10)
        item = Item("ring", "accessory", "○", (255, 255, 100), identified=False)

        result = identify(item, cost=50, gold_holder=holder)

        assert result.identified is False, "費用不足なのに鑑定された"
        assert holder.gold == 10, "費用不足なのにゴールドが引かれた"

    def test_already_identified_is_free(self):
        """鑑定済みアイテムの再鑑定は何もしない"""
        holder = _make_gold_holder(100)
        item = Item("ring", "accessory", "○", (255, 255, 100), identified=True)

        result = identify(item, cost=50, gold_holder=holder)

        assert result.identified is True
        assert holder.gold == 100, "鑑定済みなのに費用が引かれた"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
