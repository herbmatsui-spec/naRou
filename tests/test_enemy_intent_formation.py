"""敵の意図可視化 (提案2) と 陣形・連携タクティクス (提案4) のテスト。"""

from __future__ import annotations

import pytest

from constants import (
    AI_ROLE_BRUTE,
    AI_ROLE_KITER,
    INTENT_ATTACK,
    INTENT_CAST,
    INTENT_FLEE,
    INTENT_HEAL,
    INTENT_MOVE,
)

from enemy_intent import compute_intent


class FakePoint:
    def __init__(self, x, y):
        self.x, self.y = x, y


class FakeEntity:
    """compute_intent 用の軽量偽エンティティ"""

    def __init__(
        self,
        x=0,
        y=0,
        hp=100,
        max_hp=100,
        ai_role=AI_ROLE_BRUTE,
        faction="monster",
        is_player=False,
        is_pet=False,
    ):
        self.x, self.y = x, y
        self.hp, self.max_hp = hp, max_hp
        self.ai_role = ai_role
        self.faction = faction
        self.is_player = is_player
        self.is_pet = is_pet


class FakeEngine:
    def __init__(self, player, los=True):
        self.player = player
        self._los = los

    def has_los(self, a, b):
        return self._los


def _player(x=5, y=5, hp=100):
    return FakeEntity(x=x, y=y, hp=hp, faction="player", is_player=True)


def test_skeleton():
    assert True


def test_none_when_no_engine():
    assert compute_intent(FakeEntity(), None) is None


def test_adjacent_is_attack():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=5, y=4)  # 距離1
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_ATTACK
    assert intent["target"] == (5, 5)


def test_caster_in_range_is_cast():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=2, y=5, ai_role=AI_ROLE_KITER)  # 距離3, 視認
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_CAST


def test_caster_out_of_range_is_move():
    eng = FakeEngine(_player(7, 5), los=True)
    e = FakeEntity(x=0, y=5, ai_role=AI_ROLE_KITER)  # 距離7 -> 射程外
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_MOVE


def test_low_hp_flees():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=3, y=5, hp=20, max_hp=100)
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_FLEE


def test_mid_low_hp_heals():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=3, y=5, hp=33, max_hp=100)
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_HEAL


def test_default_is_move_with_target():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=0, y=0)
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_MOVE
    assert intent["target"] == (5, 5)


def test_no_intent_for_neutral_npc():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=3, y=5, faction="neutral")
    assert compute_intent(e, eng) is None


def test_no_intent_when_player_dead():
    eng = FakeEngine(_player(5, 5, hp=0))
    e = FakeEntity(x=5, y=4)
    assert compute_intent(e, eng) is None


@pytest.mark.parametrize(
    "intent_type",
    [INTENT_ATTACK, INTENT_CAST, INTENT_FLEE, INTENT_HEAL, INTENT_MOVE],
)
def test_intent_shape(intent_type):
    # _make の出力形を確認（glyph/label が必ず存在）
    from enemy_intent import _make

    d = _make(intent_type, (1, 1))
    assert set(d.keys()) == {"type", "glyph", "label", "target"}
    assert d["glyph"]
    assert d["label"]
