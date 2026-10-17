"""Test economy and quest gold fixes (Step 25, 26)."""

from __future__ import annotations

import pytest

from item_system import Item, sell
from managers.combat_manager import CombatManager


class MockQuest:
    def __init__(self, target_monster, target_count, reward_gold, reward_platinum):
        self.target_monster = target_monster
        self.target_count = target_count
        self.current_count = 0
        self.completed = False
        self.reward_gold = reward_gold
        self.reward_platinum = reward_platinum


class MockSurvival:
    def __init__(self):
        self.gold = 0
        self.platinum = 0


class MockEntityManager:
    def __init__(self):
        self.items = []
        self.removed_entities = []

    def add_item(self, item):
        self.items.append(item)

    def remove_entity(self, entity):
        self.removed_entities.append(entity)


class MockEngine:
    def __init__(self):
        self.dungeon_level = 1
        self.player = MockPlayer()
        self.quests = []
        self.survival = MockSurvival()
        self.entity_manager = MockEntityManager()
        self.logs = []

    def log(self, msg, color=None):
        self.logs.append(msg)


class MockPlayer:
    def __init__(self):
        self.exp = 0
        self.reincarnation_count = 0

    def gain_exp(self, amount):
        self.exp += amount
        return [f"Gained {amount} exp"]


def test_quest_gold_only_paid_on_completion():
    """Quest gold should only be awarded when quest completes, not on every kill."""
    engine = MockEngine()
    engine.dungeon_level = 1

    # Add a quest: kill 3 goblins for 100 gold
    quest = MockQuest("ゴブリン", 3, 100, 0)
    engine.quests.append(quest)

    manager = CombatManager()

    # Create mock goblin entity
    class MockEntity:
        name = "ゴブリン"
        x, y = 0, 0

    entity = MockEntity()

    # Kill 1st goblin - quest NOT complete, should get 0 gold
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.gold == 0, f"After 1st kill: got {engine.survival.gold} gold, expected 0"

    # Kill 2nd goblin - quest NOT complete, should get 0 gold
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.gold == 0, f"After 2nd kill: got {engine.survival.gold} gold, expected 0"

    # Kill 3rd goblin - quest COMPLETES, should get 100 gold ONCE
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.gold == 100, f"After 3rd kill: got {engine.survival.gold} gold, expected 100"

    # Kill 4th goblin - quest already complete, should get NO additional gold
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.gold == 100, f"After 4th kill: got {engine.survival.gold} gold, expected 100 (no more)"


def test_quest_platinum_only_paid_on_completion():
    """Quest platinum should only be awarded when quest completes."""
    engine = MockEngine()
    engine.dungeon_level = 1

    quest = MockQuest("スライム", 2, 50, 5)  # 50 gold, 5 platinum
    engine.quests.append(quest)

    manager = CombatManager()

    class MockEntity:
        name = "スライム"
        x, y = 0, 0

    entity = MockEntity()

    # Kill 1st slime - no platinum
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.platinum == 0

    # Kill 2nd slime - completes, gets 5 platinum
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.platinum == 5

    # Kill 3rd slime - no more platinum
    manager.handle_kill_rewards(engine, entity)
    assert engine.survival.platinum == 5


def test_items_can_be_sold_for_gold():
    """Items can be sold for gold at 30% of base_value."""
    # Create a mock item with base_value and sell_price
    item = Item(
        name="テスト剣",
        category="weapon",
        char="🗡️",
        color=(200, 200, 200),
        base_weight=3.0,
        base_value=100,
        sell_price=30,  # 30% of base_value
        count=1,
    )

    class GoldHolder:
        def __init__(self):
            self.gold = 0

    holder = GoldHolder()

    # Sell single item
    gold = sell(item, holder)
    assert gold == 30
    assert holder.gold == 30

    # Sell stacked items
    item.count = 5
    holder2 = GoldHolder()
    gold = sell(item, holder2)
    assert gold == 150  # 30 * 5
    assert holder2.gold == 150

    # Test default sell_price (30% of base_value) when not specified
    item_no_price = Item(
        name="テスト盾",
        category="shield",
        char="🛡️",
        color=(180, 180, 180),
        base_weight=2.0,
        base_value=200,
        count=1,
    )
    holder3 = GoldHolder()
    gold = sell(item_no_price, holder3)
    assert gold == 60  # 30% of 200
    assert holder3.gold == 60
