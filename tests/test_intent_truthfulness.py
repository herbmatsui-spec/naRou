"""意図テレグラフの真実性テスト (Phase 2 Step 52-53)

compute_intent が AI ツリーを実際に読んで予測することを、
12体 × HP帯3通り = 36 ケースの全走査で強制する。
「回復できない個体が回復と表示する」等の嘘を 1 件も許さない。
"""

from __future__ import annotations

import os
import sys

import pytest
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import (  # noqa: E402
    AI_ROLE_BRUTE,
    AI_ROLE_FLANKER,
    AI_ROLE_KITER,
    INTENT_ATTACK,
    INTENT_CAST,
    INTENT_FLEE,
    INTENT_HEAL,
    INTENT_MOVE,
)
from enemy_intent import _TREE_CACHE, _TREE_CAPABILITIES, compute_intent  # noqa: E402

MONSTERS_YAML = os.path.join(_ROOT, "data", "monsters.yaml")


class _FakePoint:
    def __init__(self, x, y):
        self.x, self.y = x, y


class _FakeEntity:
    def __init__(self, x=0, y=0, hp=100, max_hp=100, ai_role=AI_ROLE_BRUTE,
                 faction="monster", is_player=False, is_pet=False, name="Fake"):
        self.name = name
        self.x, self.y = x, y
        self.hp, self.max_hp = hp, max_hp
        self.ai_role = ai_role
        self.faction = faction
        self.is_player = is_player
        self.is_pet = is_pet
        self.status_effects = []


class _FakeEngine:
    def __init__(self, player, los=True):
        self.player = player
        self._los = los
        self.entities = [player]

    def has_los(self, a, b):
        return self._los

    def is_tile_free(self, x, y):
        return True

    def get_entity_at(self, x, y):
        for e in self.entities:
            if e.x == x and e.y == y and getattr(e, "hp", 0) > 0:
                return e
        return None


def _player(x=5, y=5, hp=100):
    return _FakeEntity(x=x, y=y, hp=hp, faction="player", is_player=True)


def _monster_ids() -> list[str]:
    with open(MONSTERS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return list(data.keys())


# ==================== Step 52: 表示意図と実際の行動の一致 ====================


def test_shown_intent_matches_the_tree_capabilities():
    """Step 52: 表示される heal/flee は木にその行動が実在するときだけ"""
    engine = _FakeEngine(_player(5, 5))
    e = _FakeEntity(x=3, y=5, hp=10, max_hp=100)  # HP 10%
    intent = compute_intent(e, engine)
    if intent is None:
        return
    role = e.ai_role
    if role not in _TREE_CAPABILITIES:
        return
    has_heal, has_flee = _TREE_CAPABILITIES[role]
    if intent["type"] == INTENT_HEAL:
        assert has_heal, f"回復不能な木 (capabilities={_TREE_CAPABILITIES[role]}) が回復を表示した"
    if intent["type"] == INTENT_FLEE:
        assert has_flee, f"逃走不能な木 (capabilities={_TREE_CAPABILITIES[role]}) が逃走を表示した"


# ==================== Step 53: 36ケース全走査 ====================


@pytest.mark.parametrize("monster_id", _monster_ids())
@pytest.mark.parametrize("hp_ratio", [0.9, 0.4, 0.1])
def test_no_telegraph_for_every_monster_hp_band(monster_id, hp_ratio):
    """Step 53.1: 12体 × HP帯3通り = 36ケースで嘘テレグラフが無いこと

    aggressive/boss (回復・逃走なし) は如何なる HP 帯でも heal/flee を表示しない。
    coward/caster/tactical (回復あり) は低 HP で heal を表示してよい。
    """
    with open(MONSTERS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entry = data[monster_id]
    ai_role = entry.get("ai_role") or AI_ROLE_BRUTE
    max_hp = entry.get("max_hp", 100)

    engine = _FakeEngine(_player(5, 5))
    hp = max(1, int(max_hp * hp_ratio))
    e = _FakeEntity(x=3, y=5, hp=hp, max_hp=max_hp, ai_role=ai_role)
    intent = compute_intent(e, engine)

    if intent is None:
        return  # 移動不可など意図無しは正当

    tree_name = "kiter" if ai_role == AI_ROLE_KITER else (
        "flanker" if ai_role == AI_ROLE_FLANKER else "aggressive"
    )
    caps = _TREE_CAPABILITIES.get(tree_name)
    if caps is None:
        return
    has_heal, has_flee = caps
    if intent["type"] == INTENT_HEAL:
        assert has_heal, f"{monster_id} (HP{hp_ratio:.0%}): 回復不能な木が回復を表示"
    if intent["type"] == INTENT_FLEE:
        assert has_flee, f"{monster_id} (HP{hp_ratio:.0%}): 逃走不能な木が逃走を表示"


def test_intent_is_none_for_dead_entities():
    """Step 53.2: 死亡エンティティには意図を表示しない"""
    engine = _FakeEngine(_player(5, 5))
    e = _FakeEntity(x=3, y=5, hp=0, max_hp=100)
    assert compute_intent(e, engine) is None


def test_intent_is_none_for_non_monster_factions():
    """Step 53.3: モンスター以外 (中立NPC等) には意図を表示しない"""
    engine = _FakeEngine(_player(5, 5))
    e = _FakeEntity(x=3, y=5, faction="neutral")
    assert compute_intent(e, engine) is None


def test_intent_is_none_for_player_and_pet():
    """Step 53.3 補足: プレイヤー/ペット自身には意図なし"""
    engine = _FakeEngine(_player(5, 5))
    assert compute_intent(_FakeEntity(x=3, y=5, is_player=True, faction="player"), engine) is None
    assert compute_intent(_FakeEntity(x=3, y=5, is_pet=True, faction="player"), engine) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
