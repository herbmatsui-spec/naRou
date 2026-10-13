"""ペット性格系属性のセーブ永続化テスト (改善案2)。

背景:
- pickle 本線 (SaveSystem.save) は Engine 全体を pickle するため
  player/pet Entity 上の性格属性は保持される。
- JSON 副線 (serialize_engine_to_dict → Entity.to_dict) は明示フィールド
  列挙のため、PetPersonalitySystem が動的に付与する
  personality / bond / favorite_food_tags が欠落していた (改善案2で修復)。
- player の HuskInventoryComponent (husks) は両パスで保持される必要がある
  (既存動作の回帰固定)。
"""

from __future__ import annotations

import pickle

import pytest

from ecs.components.components import HuskComponent, HuskInventoryComponent
from ecs.entity import Entity
from item_system import Item
from save_system import SaveSystem


@pytest.fixture
def pet_with_personality() -> Entity:
    pet = Entity(name="pet", is_pet=True)
    pet.personality = "brave"
    pet.bond = 77
    pet.favorite_food_tags = ["meat", "fish"]
    return pet


def _player_with_husk() -> Entity:
    player = Entity(name="player", is_player=True)
    player.get_component(HuskInventoryComponent).husks.append(
        HuskComponent(husk_id="h1", source_monster="slime", tier=2, decay=3)
    )
    return player


def test_json_roundtrip_preserves_pet_personality(pet_with_personality):
    """JSON 副線: pet 性格3属性が to_dict/from_dict で対称に保持されること"""
    data = pet_with_personality.to_dict()
    assert data["personality"] == "brave"
    assert data["bond"] == 77
    assert data["favorite_food_tags"] == ["meat", "fish"]

    restored = Entity.from_dict(data)
    assert restored.personality == "brave"
    assert restored.bond == 77
    assert restored.favorite_food_tags == ["meat", "fish"]


def test_to_dict_omits_personality_when_unset():
    """性格未付与の Entity (敵など) には性格キーを出力しない (副作用ゼロ)"""
    plain = Entity(name="monster")
    data = plain.to_dict()
    assert "personality" not in data
    assert "bond" not in data
    assert "favorite_food_tags" not in data


def test_pickle_roundtrip_preserves_pet_personality(pet_with_personality):
    """pickle 本線: 性格属性が失われないこと (既存動作の回帰固定)"""
    restored = pickle.loads(pickle.dumps(pet_with_personality))
    assert restored.personality == "brave"
    assert restored.bond == 77
    assert restored.favorite_food_tags == ["meat", "fish"]


def test_json_roundtrip_preserves_player_husks():
    """JSON 副線: player の husks が components 経由で保持されること (回帰固定)"""
    player = _player_with_husk()
    data = player.to_dict()
    assert "HuskInventoryComponent" in data["components"]

    restored = Entity.from_dict(data)
    husks = restored.get_component(HuskInventoryComponent).husks
    assert len(husks) == 1
    assert husks[0].husk_id == "h1"
    assert husks[0].decay == 3


def test_engine_json_roundtrip_keeps_enchanted_item_and_husk():
    """SerializeEngineToDict 経由の統合: enchant 付き Item と husk が保持される"""
    engine = _minimal_engine_with_state()
    d = SaveSystem.serialize_engine_to_dict(engine)
    assert d["inventory"][-1]["enchants"] == ["sharp+1"]
    assert "HuskInventoryComponent" in d["player"]["components"]
    assert d["pet"]["personality"] == "brave"


def _minimal_engine_with_state():
    """軽量 Engine スタブ: serialize_engine_to_dict が必要な属性のみ"""
    from types import SimpleNamespace

    engine = SimpleNamespace()
    engine.player = _player_with_husk()
    engine.pet = Entity(name="pet", is_pet=True)
    engine.pet.personality = "brave"
    engine.dungeon_level = 1
    engine.turns = 0
    engine.game_state = "play"
    engine.inventory = SimpleNamespace(items=[Item(name="sword", enchants=("sharp+1",))])
    engine.pet_inventory = None
    engine.items_on_ground = []
    engine.territory_state = None
    return engine
