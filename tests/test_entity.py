"""Unit tests for the refactored Entity component model."""

from __future__ import annotations

from entity import Entity


def test_entity_default_components_present():
    e = Entity(is_player=True)
    # Component-backed attributes resolve via delegation.
    assert e.affection == 50
    assert e.pet_type == "puppy"
    assert e.emote_state is None
    assert e.pet_ai is not None


def test_entity_component_property_set():
    e = Entity(is_player=True)
    e.affection = 80
    assert e.affection == 80
    e.pet_type = "dragon"
    assert e.pet_type == "dragon"


def test_entity_to_dict_includes_components():
    e = Entity(is_player=True)
    d = e.to_dict()
    assert "components" in d
    assert "AffectionComponent" in d["components"]
    assert "PetProfileComponent" in d["components"]
    assert "EmoteComponent" in d["components"]
    assert "PetAIComponent" in d["components"]


def test_entity_roundtrip():
    e = Entity(is_player=True)
    e.affection = 77
    e.pet_type = "dragon"
    e.emote_state = "wave"
    restored = Entity.from_dict(e.to_dict())
    assert restored.affection == 77
    assert restored.pet_type == "dragon"
    assert restored.emote_state == "wave"


def test_entity_json_serializable():
    import json

    e = Entity(is_pet=True)
    json.dumps(e.to_dict())
