"""Test Husk serialization through Entity"""

from narou.ecs.components.components import HuskComponent, HuskInventoryComponent
from narou.ecs.entity import Entity


def test_entity_husk_serialization():
    """Test that HuskComponent serializes correctly through Entity"""
    # Create entity with husk
    entity = Entity(name="test player")

    # Create a husk
    husk = HuskComponent(
        husk_id="test_husk_001",
        source_monster="slime",
        tier=2,
        decay=10,
        corruption=5,
        slots=3,
        injected_skills=["fire_bolt", "heal"],
        injected_codes=["synergy_fire_heal"]
    )

    # Add husk to entity's inventory
    husk_inv = entity.get_component(HuskInventoryComponent)
    husk_inv.husks.append(husk)

    # Serialize to dict
    data = entity.to_dict()

    # Check that husk data is in components
    assert "components" in data
    assert "HuskInventoryComponent" in data["components"]
    husk_data = data["components"]["HuskInventoryComponent"]
    assert "husks" in husk_data
    assert len(husk_data["husks"]) == 1

    husk_dict = husk_data["husks"][0]
    assert husk_dict["husk_id"] == "test_husk_001"
    assert husk_dict["source_monster"] == "slime"
    assert husk_dict["tier"] == 2
    assert husk_dict["decay"] == 10
    assert husk_dict["corruption"] == 5
    assert husk_dict["slots"] == 3
    assert husk_dict["injected_skills"] == ["fire_bolt", "heal"]
    assert husk_dict["injected_codes"] == ["synergy_fire_heal"]

    # Deserialize from dict
    restored_entity = Entity.from_dict(data)

    # Check that husk was restored correctly
    restored_husk_inv = restored_entity.get_component(HuskInventoryComponent)
    assert len(restored_husk_inv.husks) == 1
    restored_husk = restored_husk_inv.husks[0]

    assert restored_husk.husk_id == "test_husk_001"
    assert restored_husk.source_monster == "slime"
    assert restored_husk.tier == 2
    assert restored_husk.decay == 10
    assert restored_husk.corruption == 5
    assert restored_husk.slots == 3
    assert restored_husk.injected_skills == ["fire_bolt", "heal"]
    assert restored_husk.injected_codes == ["synergy_fire_heal"]

    print("✓ Husk serialization test passed")


def test_empty_husk_serialization():
    """Test that empty husk list serializes correctly"""
    entity = Entity(name="test player")
    # Initialize husk inventory component
    entity.get_component(HuskInventoryComponent)
    data = entity.to_dict()

    husk_data = data["components"]["HuskInventoryComponent"]
    assert "husks" in husk_data
    assert len(husk_data["husks"]) == 0

    # Should be able to deserialize empty list
    restored_entity = Entity.from_dict(data)
    restored_husk_inv = restored_entity.get_component(HuskInventoryComponent)
    assert len(restored_husk_inv.husks) == 0

    print("✓ Empty husk serialization test passed")


if __name__ == "__main__":
    test_entity_husk_serialization()
    test_empty_husk_serialization()
    print("All tests passed!")
