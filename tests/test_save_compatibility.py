"""セーブ永続化の互換性テスト (改善案5)。

pickle 本線と JSON 副線の両方で、以下が保持されることを検証:
- player/pet Entity の ECS コンポーネント (husks, personality, bond, favorite_food_tags)
- Item.enchants
- Survival 状態 (gold, platinum, hunger, thirst, sleep, sleepiness, karma, karma_law_chaos, legacy_skills)
- 既知制約: pickle 本線の Engine.__getstate__ は kernel/entity_manager/ハンドラ等を除外し、
  ロード後は engine.__dict__.update() によりライブ側の kernel が維持されるため、
  kernel 保持の skill_eater システム実行状態と敵エンティティはセーブ対象外。
"""

from __future__ import annotations

import pickle

import pytest

from ecs.components.components import HuskComponent, HuskInventoryComponent
from ecs.entity import Entity
from item_system import Item
from save_system import SaveSystem


def _make_pet() -> Entity:
    pet = Entity(name="pet", is_pet=True)
    pet.personality = "brave"
    pet.bond = 77
    pet.favorite_food_tags = ["meat", "fish"]
    return pet


def _make_player_with_husk() -> Entity:
    player = Entity(name="player", is_player=True)
    player.get_component(HuskInventoryComponent).husks.append(
        HuskComponent(husk_id="h1", source_monster="slime", tier=2, decay=3)
    )
    return player


def _make_enchanted_item() -> Item:
    return Item(name="sword", enchants=("sharp+1", "fire+2"))


def _minimal_engine_with_state():
    """serialize_engine_to_dict / deserialize_dict_to_engine が必要な属性のみを持つ Engine スタブ"""
    from types import SimpleNamespace

    engine = SimpleNamespace()
    engine.player = _make_player_with_husk()
    engine.pet = _make_pet()
    engine.dungeon_level = 5
    engine.turns = 123
    engine.game_state = "play"

    engine.survival = SimpleNamespace()
    engine.survival.gold = 5000
    engine.survival.platinum = 100
    engine.survival.hunger = 6000
    engine.survival.thirst = 300
    engine.survival.sleep = 700
    engine.survival.sleepiness = 200
    engine.survival.karma = 10
    engine.survival.karma_law_chaos = 5
    engine.survival.legacy_skills = ["fire_bolt", "heal"]

    engine.inventory = SimpleNamespace(items=[_make_enchanted_item()])
    engine.pet_inventory = None
    engine.items_on_ground = []
    engine.territory_state = None
    return engine


# ---------------------------------------------------------------------------
# JSON 副線: serialize/deserialize の対称性
# ---------------------------------------------------------------------------


def test_json_roundtrip_preserves_survival_full_state():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    surv = data["survival"]
    assert surv["gold"] == 5000
    assert surv["platinum"] == 100
    assert surv["hunger"] == 6000
    assert surv["thirst"] == 300
    assert surv["sleep"] == 700
    assert surv["sleepiness"] == 200
    assert surv["karma"] == 10
    assert surv["karma_law_chaos"] == 5
    assert surv["legacy_skills"] == ["fire_bolt", "heal"]


def test_json_roundtrip_preserves_enchanted_item_and_husks():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    assert data["inventory"][-1]["enchants"] == ["sharp+1", "fire+2"]
    assert "HuskInventoryComponent" in data["player"]["components"]
    assert data["pet"]["personality"] == "brave"
    assert data["pet"]["bond"] == 77
    assert data["pet"]["favorite_food_tags"] == ["meat", "fish"]


def test_json_deserialize_restores_survival_state():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    restored = SaveSystem.deserialize_dict_to_engine(data)
    assert restored.survival.gold == 5000
    assert restored.survival.platinum == 100
    assert restored.survival.hunger == 6000
    assert restored.survival.thirst == 300
    assert restored.survival.sleep == 700
    assert restored.survival.sleepiness == 200
    assert restored.survival.karma == 10
    assert restored.survival.karma_law_chaos == 5
    assert restored.survival.legacy_skills == ["fire_bolt", "heal"]


def test_json_deserialize_restores_inventory_and_pet():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    restored = SaveSystem.deserialize_dict_to_engine(data)
    item = restored.inventory.items[-1]
    assert item.enchants == ("sharp+1", "fire+2")
    husks = restored.player.get_component(HuskInventoryComponent).husks
    assert len(husks) == 1
    assert husks[0].husk_id == "h1"
    assert restored.pet.personality == "brave"
    assert restored.pet.bond == 77


def test_json_deserialize_restores_engine_meta():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    restored = SaveSystem.deserialize_dict_to_engine(data)
    assert restored.dungeon_level == 5
    assert restored.turns == 123
    assert restored.game_state == "play"


# ---------------------------------------------------------------------------
# pickle 本線: 既存動作の回帰固定
# ---------------------------------------------------------------------------


def test_pickle_roundtrip_preserves_pet_and_player_state():
    pet = _make_pet()
    restored = pickle.loads(pickle.dumps(pet))
    assert restored.personality == "brave"
    assert restored.bond == 77
    assert restored.favorite_food_tags == ["meat", "fish"]

    player = _make_player_with_husk()
    restored_player = pickle.loads(pickle.dumps(player))
    husks = restored_player.get_component(HuskInventoryComponent).husks
    assert len(husks) == 1
    assert husks[0].decay == 3


def test_pickle_roundtrip_preserves_enchanted_item():
    item = _make_enchanted_item()
    restored = pickle.loads(pickle.dumps(item))
    assert restored.enchants == ("sharp+1", "fire+2")


# ---------------------------------------------------------------------------
# 既知制約のドキュメント化 (docstring に記載済み、ここでは回帰固定のみ)
# ---------------------------------------------------------------------------


def test_save_system_docstring_mentions_getstate_exclusion():
    """pickle 本線が kernel/entity_manager を除外する既知制約を docstring に記載していること"""
    doc = SaveSystem.__doc__ or ""
    assert "kernel" in doc
    assert "entity_manager" in doc
    assert "__getstate__" in doc
