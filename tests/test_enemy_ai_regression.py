"""敵AI回帰テスト (Phase 2 Step 55)

seed を固定し、ai_role ごとの 1 ターン挙動をスナップショットとして固定する。
同じ seed で同じ行動列になることを assertion にする。
"""

from __future__ import annotations

import os
import random
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import ENERGY_THRESHOLD  # noqa: E402
from data_manager import DataManager  # noqa: E402
from game import Engine  # noqa: E402
from renderer import NullRenderer  # noqa: E402
from skill_eater.ai.ai_system import AdvancedAISystem  # noqa: E402

# seed 固定での期待行動スナップショット (monster_id -> (seed, 期待シグナル))
# シグナル: hp_down=攻撃, moved=移動, healed=回復, buffed=防御上昇
SNAPSHOTS = {
    # brute: 隣接攻撃
    "orc": {"dx": 1, "seed": 1, "expect_hp_down": True},
    # flanker: 隣接攻撃
    "kobold": {"dx": 1, "seed": 1, "expect_hp_down": True},
    # caster: 射程内詠唱
    "novice_wizard": {"dx": 3, "seed": 1, "expect_any": True},
}


def _engine() -> Engine:
    return Engine(renderer=NullRenderer())


@pytest.mark.parametrize("monster_id", sorted(SNAPSHOTS.keys()))
def test_ai_behavior_is_deterministic_per_seed(monster_id):
    """Step 55.2: 同じ seed なら同じ行動列になること (2回実行して一致)"""
    cfg = SNAPSHOTS[monster_id]
    dm = DataManager()

    def _run_once() -> dict:
        # ダンジョン生成も含めて完全決定的にする: seed は engine 生成前に固定
        random.seed(cfg["seed"])
        engine = _engine()
        mob = dm.create_monster(monster_id, x=engine.player.x + cfg["dx"], y=engine.player.y)
        mob.energy = ENERGY_THRESHOLD * 3
        mob.reset_ap()
        engine.entity_manager.add_entity(mob)

        hp0 = engine.player.hp
        pos0 = (mob.x, mob.y)
        mob_hp0 = mob.hp
        mob_end0 = getattr(mob, "endurance", 0)

        random.seed(cfg["seed"])
        AdvancedAISystem().process_ai(mob, engine)

        return {
            "player_hp": engine.player.hp,
            "mob_pos": (mob.x, mob.y),
            "mob_hp": mob.hp,
            "mob_endurance": getattr(mob, "endurance", 0),
            "hp_down": engine.player.hp < hp0,
            "moved": (mob.x, mob.y) != pos0,
            "healed": mob.hp > mob_hp0,
            "buffed": getattr(mob, "endurance", 0) > mob_end0,
            "logs": tuple(m.text for m in engine.msg_log.messages),
        }

    run1 = _run_once()
    run2 = _run_once()

    assert run1["player_hp"] == run2["player_hp"], (
        f"{monster_id}: seed={cfg['seed']} で非決定的 (HP {run1['player_hp']} vs {run2['player_hp']})"
    )
    assert run1["mob_pos"] == run2["mob_pos"], (
        f"{monster_id}: seed={cfg['seed']} で移動が非決定的"
    )
    assert run1["logs"] == run2["logs"], (
        f"{monster_id}: seed={cfg['seed']} でログ列が非決定的"
    )


@pytest.mark.parametrize("monster_id", sorted(SNAPSHOTS.keys()))
def test_ai_behavior_matches_snapshot_signal(monster_id):
    """Step 55.1: 各ロールの期待シグナルが観測されること"""
    cfg = SNAPSHOTS[monster_id]
    dm = DataManager()
    engine = _engine()
    mob = dm.create_monster(monster_id, x=engine.player.x + cfg["dx"], y=engine.player.y)
    mob.energy = ENERGY_THRESHOLD * 3
    mob.reset_ap()
    engine.entity_manager.add_entity(mob)

    hp0 = engine.player.hp
    random.seed(cfg["seed"])
    AdvancedAISystem().process_ai(mob, engine)

    if cfg.get("expect_hp_down"):
        assert engine.player.hp < hp0, f"{monster_id}: 期待された攻撃が発生しなかった"
    if cfg.get("expect_any"):
        assert engine.player.hp != hp0, f"{monster_id}: 何も起きなかった"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
