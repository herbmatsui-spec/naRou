"""Regression tests for enemy intent formation. These tests ensure that the
enemy intent logic can distinguish between correct and intentionally broken
configurations, preventing vacuously passing tests.
"""

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
from tests.helpers.non_vacuity import assert_distinguishes


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
        ai_type="aggressive",
        faction="monster",
        is_player=False,
        is_pet=False,
        name="Fake",
    ):
        self.name = name
        self.x, self.y = x, y
        self.hp, self.max_hp = hp, max_hp
        self.ai_role = ai_role
        self.ai_type = ai_type
        self.faction = faction
        self.is_player = is_player
        self.is_pet = is_pet


class FakeEngine:
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
    return FakeEntity(x=x, y=y, hp=hp, faction="player", is_player=True)


def test_adjacent_is_attack_distinguishes():
    """Adjacent entity should ATTACK; change ai_type to kiter should not."""
    def check_intent_is_attack(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        assert intent["type"] == INTENT_ATTACK
        assert intent["target"] == (5, 5)

    # Good case: adjacent brute entity
    good = FakeEntity(x=5, y=4)  # distance 1
    # Bad case: same position but kiter role (should cast or move, not attack)
    bad = FakeEntity(x=5, y=4, ai_role=AI_ROLE_KITER)
    assert_distinguishes(check_intent_is_attack, good, bad, label="adjacent intent is attack")


def test_caster_in_range_is_cast_distinguishes():
    """Caster in range should CAST; change ai_type to brute should not."""
    def check_intent_is_cast(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        assert intent["type"] == INTENT_CAST

    # Good case: caster in range
    good = FakeEntity(x=2, y=5, ai_role=AI_ROLE_KITER)  # distance 3, los=True by default
    # Bad case: brute at same position (should attack if adjacent, but not in range? Actually distance 3 -> move)
    # Let's instead change hp to make it flee? Better: change ai_type to brute and ensure it's not cast.
    bad = FakeEntity(x=2, y=5, ai_role=AI_ROLE_BRUTE)
    assert_distinguishes(check_intent_is_cast, good, bad, label="caster in range intent is cast")


def test_low_hp_flees_distinguishes():
    """Low hp coward should FLEE; change ai_type to aggressive should not."""
    def check_intent_is_flee(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        assert intent["type"] == INTENT_FLEE

    # Good case: low hp coward
    good = FakeEntity(x=3, y=5, hp=55, max_hp=100, ai_type="coward")
    # Bad case: same hp but aggressive (should not flee)
    bad = FakeEntity(x=3, y=5, hp=55, max_hp=100, ai_type="aggressive")
    assert_distinguishes(check_intent_is_flee, good, bad, label="low hp coward flees")


def test_mid_low_hp_heals_distinguishes():
    """Mid low hp coward should HEAL; change ai_type to aggressive should not."""
    def check_intent_is_heal(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        assert intent["type"] == INTENT_HEAL

    # Good case: mid low hp coward
    good = FakeEntity(x=3, y=5, hp=33, max_hp=100, ai_type="coward")
    # Bad case: same hp but aggressive (should not heal)
    bad = FakeEntity(x=3, y=5, hp=33, max_hp=100, ai_type="aggressive")
    assert_distinguishes(check_intent_is_heal, good, bad, label="mid low hp coward heals")


def test_default_is_move_with_target_distinguishes():
    """Default entity should MOVE toward player; change player position should change target."""
    def check_intent_is_move_to_player(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        assert intent["type"] == INTENT_MOVE
        assert intent["target"] == (5, 5)

    # Good case: entity at (0,0) with player at (5,5)
    good = FakeEntity(x=0, y=0)
    # Bad case: same entity but player at (10,10) -> target should be (10,10), not (5,5)
    # We need to change the engine's player position. Let's create a closure that captures player pos.
    def check_intent_is_move_to_player_at_10_10(entity):
        eng = FakeEngine(_player(10, 10))
        intent = compute_intent(entity, eng)
        assert intent["type"] == INTENT_MOVE
        assert intent["target"] == (10, 10)

    # For assert_distinguishes we need a single check function. We'll instead test that
    # changing the entity's position changes the intent target (but still move).
    # Let's do a different approach: test that moving the entity far away still results in MOVE
    # but with same target (player). Actually we want to ensure the check can distinguish
    # between correct and broken. We'll break by making the entity is_player=True (should return None intent).
    def check_intent_is_move(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        # Ensure it's not None and is MOVE
        assert intent is not None
        assert intent["type"] == INTENT_MOVE
        assert intent["target"] == (5, 5)

    good = FakeEntity(x=0, y=0)  # enemy
    bad = FakeEntity(x=0, y=0, is_player=True)  # player -> should return None
    assert_distinguishes(check_intent_is_move, good, bad, label="default is move toward player")


def test_no_intent_for_neutral_npc_distinguishes():
    """Neutral faction should return None; change faction to monster should not."""
    def check_intent_is_none(entity):
        eng = FakeEngine(_player(5, 5))
        intent = compute_intent(entity, eng)
        assert intent is None

    good = FakeEntity(x=3, y=5, faction="neutral")
    bad = FakeEntity(x=3, y=5, faction="monster")
    assert_distinguishes(check_intent_is_none, good, bad, label="neutral npc returns none")


def test_no_intent_when_player_dead_distinguishes():
    """Player dead should return None."""
    def check_intent_is_none(entity):
        eng = FakeEngine(_player(5, 5, hp=0))  # player dead
        intent = compute_intent(entity, eng)
        assert intent is None

    good = FakeEntity(x=5, y=4)
    bad = FakeEntity(x=5, y=4, ai_type="coward")
    assert_distinguishes(check_intent_is_none, good, bad, label="dead player -> no intent")
