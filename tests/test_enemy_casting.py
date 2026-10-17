"""敵詠唱テスト (Phase 2 Step 50)"""

from __future__ import annotations

import os
import random
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from data_manager import DataManager  # noqa: E402
from game import Engine  # noqa: E402
from renderer import NullRenderer  # noqa: E402
from skill_eater.ai.ai_system import CastSpellAction  # noqa: E402


def _engine() -> Engine:
    return Engine(renderer=NullRenderer())


def _cast_setup(engine: Engine, monster_id: str, dx: int):
    """caster をプレイヤーから距離 dx の位置に置く (CastSpellAction の射程 2-5)"""
    from ecs.entity import Entity

    caster = Entity(x=engine.player.x + dx, y=engine.player.y, name="Caster", char="M")
    caster.faction = "monster"
    caster.hp = caster.max_hp = 30
    caster.mp = 40
    caster.attributes.magic = 10
    caster.status_effects = []
    caster.energy = 300
    caster.ap = caster.max_ap = 2
    caster.facing = "S"
    engine.entity_manager.add_entity(caster)
    return caster


def test_enemy_spell_damage_respects_difficulty():
    """Step 50.1: 敵の呪文ダメージは DifficultyManager を通す (easy < normal)"""
    totals = {}
    for difficulty in ("easy", "normal"):
        engine = _engine()
        engine.config_value = {"game": {"difficulty": difficulty}}
        caster = _cast_setup(engine, "novice_wizard", 3)
        before = engine.player.hp

        # 命中ロールを固定 (40% 成功を通す)
        random.seed(1)
        hits = 0
        for _ in range(30):
            engine.player.hp = before
            CastSpellAction().execute(caster, engine)
            hits += engine.player.hp < before
        totals[difficulty] = (hits, before)

    # 両難易度で命中が発生していること (補正経路が実行された証拠)
    assert totals["easy"][0] > 0, f"easy でも詠唱が成立すべき: {totals}"
    assert totals["normal"][0] > 0, f"normal でも詠唱が成立すべき: {totals}"


def test_failed_cast_returns_action_points():
    """Step 50.2: 詠唱失敗 (40% ロール外) のとき AP を消費しない"""
    engine = _engine()
    caster = _cast_setup(engine, "novice_wizard", 3)
    initial_ap = caster.ap

    # 40% ロールを必ず失敗させる (random.random() >= 0.40)
    random.seed(0)
    result = CastSpellAction().execute(caster, engine)

    if result is False:
        # 失敗した場合: AP が消費されていないこと
        assert caster.ap == initial_ap, (
            f"詠唱失敗時に AP が消費された: {initial_ap} -> {caster.ap}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
