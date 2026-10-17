"""モンスター耐性テスト (Phase 2 Step 51)"""

from __future__ import annotations

import os
import random
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import Element  # noqa: E402
from data_manager import DataManager  # noqa: E402
from game import Engine  # noqa: E402
from renderer import NullRenderer  # noqa: E402
from skill_eater.ai.ai_system import AdvancedAISystem  # noqa: E402


def _engine() -> Engine:
    return Engine(renderer=NullRenderer())


def test_element_resistance_reduces_damage():
    """Step 51.3: monsters.yaml の resistances が Entity に適用され、ダメージが軽減される"""
    dm = DataManager()
    hound_def = dm.monsters.get("hound_fire")
    assert hound_def.resistances, "前提: hound_fire が resistances を宣言していること"
    assert hound_def.resistances.get("fire", 0) > 0, "前提: hound_fire の炎耐性が正値であること"

    # create_monster 経由で Entity に耐性が流れること
    engine = _engine()
    mob = dm.create_monster("hound_fire", x=10, y=10)
    res_set = getattr(mob, "resistances", None)
    assert res_set is not None, "resistances が Entity に設定されていない"
    assert res_set.fire > 0, f"炎耐性が Entity へ流れていない: {res_set.fire}"

    # 耐性値がダメージ計算で実際に軽減されること (CombatSystem 経由)
    from engine.systems.combat_system import CombatSystem

    base_dmg = 50
    with_res = CombatSystem.calc_element_damage(base_dmg, Element.FIRE, res_set.fire)
    without_res = CombatSystem.calc_element_damage(base_dmg, Element.FIRE, 0)
    assert with_res < without_res, (
        f"炎耐性 {res_set.fire} がダメージを軽減していない: {with_res} >= {without_res}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
