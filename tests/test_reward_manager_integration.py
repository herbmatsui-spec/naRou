"""
Test reward manager integration with actual item and economy systems.
"""
import sys
from pathlib import Path

# Ensure the naRou package is importable
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest
from naRou.ecs.entity import Entity
from naRou.ecs.components.components import EconomyComponent
from naRou.systems.item_system import Item, Inventory, create_sample_item
from naRou.reward_manager import RewardManager, KEY_GOLD, KEY_PLATINUM, KEY_EXP, KEY_PIETY, KEY_FAME, KEY_ITEMS, KEY_ITEM_DROPS, KEY_ARTIFACT, KEY_SPECIAL_CURRENCY, KEY_CURRENCY_AMOUNT


class DummyEngine:
    """Dummy engine for logging."""
    def __init__(self):
        self.logs = []
    def log(self, message, color=(255,255,255)):
        self.logs.append((message, color))


def make_player_entity():
    """Create a player entity with inventory and economy components."""
    player = Entity()
    # Add required components
    player.components[EconomyComponent] = EconomyComponent()
    player.components[Inventory] = Inventory()  # Using Inventory from item_system
    # Initialize some attributes for piety, etc.
    player.piety = 0
    # faction_reputation as dict
    player.faction_reputation = {}
    return player


def test_grant_gold():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    # Initially gold should be 0 (default)
    assert player.gold == 0
    # Grant 100 gold
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_GOLD: 100}})(), engine)
    assert player.gold == 100
    # Check that a log was generated
    assert any("金が100G増加した。" in msg for msg, _ in engine.logs)


def test_grant_platinum():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    assert player.platinum == 0
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_PLATINUM: 5}})(), engine)
    assert player.platinum == 5
    assert any("プラチナが5P増加した。" in msg for msg, _ in engine.logs)


def test_grant_exp():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    assert player.exp == 0
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_EXP: 200}})(), engine)
    # gain_exp adds job_exp as well, but exp should increase by 200
    assert player.exp == 200
    # Check logs from gain_exp (they are returned by gain_exp)
    # gain_exp returns list of strings; we just ensure logs not empty
    assert len(logs) > 0


def test_grant_piety():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    assert player.piety == 0
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_PIETY: 10}})(), engine)
    assert player.piety == 10
    assert any("信仰が10増加した。" in msg for msg, _ in engine.logs)


def test_grant_fame():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    assert player.faction_reputation.get("world", 0) == 0
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_FAME: 7}})(), engine)
    assert player.faction_reputation.get("world", 0) == 7
    assert any("名声が7増加した。" in msg for msg, _ in engine.logs)


def test_grant_items():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    inv: Inventory = player.components[Inventory]
    initial_count = len(inv.items)
    # Grant 2 breads (assuming create_sample_item works for "bread")
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_ITEMS: {"bread": 2}}})(), engine)
    # Check that items were added
    assert len(inv.items) >= initial_count  # at least one new item (maybe stacked)
    # Find bread item
    bread_items = [it for it in inv.items if it.name == "パン"]
    assert len(bread_items) > 0
    # The count should be 2 (or maybe stacked with existing if any)
    # Since we started with empty inventory, count should be 2
    assert bread_items[0].count == 2
    # Check log
    assert any("パン を手に入れた。" in msg for msg, _ in engine.logs)


def test_grant_item_drops():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    inv: Inventory = player.components[Inventory]
    # Use drop chance 1.0 to guarantee drop
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_ITEM_DROPS: {"potion_heal": 1.0}}})(), engine)
    # Should have added a potion_heal
    potion_items = [it for it in inv.items if it.name == "軽傷治療のポーション"]
    assert len(potion_items) > 0
    assert potion_items[0].count >= 1
    # Check log
    assert any("軽傷治療のポーション を手に入れた。" in msg for msg, _ in engine.logs)


def test_grant_artifact():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    inv: Inventory = player.components[Inventory]
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_ARTIFACT: "longsword"}})(), engine)
    # Should have added a longsword
    sword_items = [it for it in inv.items if it.name == "長剣"]
    assert len(sword_items) > 0
    assert sword_items[0].count >= 1
    assert any("長剣 を手に入れた。" in msg for msg, _ in engine.logs)


def test_grant_legacy_special_currency():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    # Legacy: special_currency = "platinum", currency_amount = 3
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_SPECIAL_CURRENCY: "platinum", KEY_CURRENCY_AMOUNT: 3}})(), engine)
    assert player.platinum == 3
    assert any("プラチナが3P増加した。" in msg for msg, _ in engine.logs)


def test_grant_unknown_currency_fallbacks_to_gold():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    # Unknown currency id "unknown" should fallback to gold
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_SPECIAL_CURRENCY: "unknown", KEY_CURRENCY_AMOUNT: 50}})(), engine)
    assert player.gold == 50
    assert any("金が50G増加した。" in msg for msg, _ in engine.logs)


def test_zero_and_negative_amounts_are_ignored():
    rm = RewardManager()
    player = make_player_entity()
    engine = DummyEngine()
    # Zero or negative amounts should not change anything
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_GOLD: 0, KEY_PLATINUM: -5}})(), engine)
    assert player.gold == 0
    assert player.platinum == 0
    # No logs should be generated for zero/negative
    # But we still might get logs from the grant functions? They return empty list for <=0.
    # So logs should be empty.
    assert len(logs) == 0


def test_missing_inventory_graceful():
    rm = RewardManager()
    player = make_player_entity()
    # Remove inventory component
    if Inventory in player.components:
        del player.components[Inventory]
    engine = DummyEngine()
    logs = rm.grant_event_rewards(player, type('EventData', (), {'rewards': {KEY_ITEMS: {"bread": 1}}})(), engine)
    # Should not crash, and should log about missing inventory
    assert any("インベントリがないためアイテムを付与できません。" in msg for msg, _ in engine.logs)


if __name__ == "__main__":
    # Simple test runner for debugging
    test_grant_gold()
    print("test_grant_gold passed")
    test_grant_platinum()
    print("test_grant_platinum passed")
    test_grant_exp()
    print("test_grant_exp passed")
    test_grant_piety()
    print("test_grant_piety passed")
    test_grant_fame()
    print("test_grant_fame passed")
    test_grant_items()
    print("test_grant_items passed")
    test_grant_item_drops()
    print("test_grant_item_drops passed")
    test_grant_artifact()
    print("test_grant_artifact passed")
    test_grant_legacy_special_currency()
    print("test_grant_legacy_special_currency passed")
    test_grant_unknown_currency_fallbacks_to_gold()
    print("test_grant_unknown_currency_fallbacks_to_gold passed")
    test_zero_and_negative_amounts_are_ignored()
    print("test_zero_and_negative_amounts_are_ignored passed")
    test_missing_inventory_graceful()
    print("test_missing_inventory_graceful passed")
    print("All tests passed!")