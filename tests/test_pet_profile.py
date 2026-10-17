"""
Tests for pet_quest_analyzer.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecs.entity import Entity
from pet_quest_analyzer import PetProfile, PetQuestAnalyzer


def test_pet_profile_creation():
    """Test that a PetProfile can be created."""
    profile = PetProfile(
        species="wolf",
        contract_type="loyalty",
        evolution_stage=2,
        fusion_history=["dog", "fox"],
        loyalty=80,
        affinity={"fire": 10, "water": -5}
    )

    assert profile.species == "wolf"
    assert profile.contract_type == "loyalty"
    assert profile.evolution_stage == 2
    assert profile.fusion_history == ["dog", "fox"]
    assert profile.loyalty == 80
    assert profile.affinity == {"fire": 10, "water": -5}


def test_pet_analyzer_no_pet():
    """Test that analyzing a player with no pet returns None."""
    player = Entity(name="Player")
    # No pet attribute
    analyzer = PetQuestAnalyzer()
    profile = analyzer.analyze_pet(player)
    assert profile is None


def test_pet_analyzer_with_pet():
    """Test that analyzing a player with a pet returns a profile."""
    # We'll mock a simple pet object
    class MockPet:
        def __init__(self):
            self.species = "phoenix"
            self.contract_type = "symbiosis"
            self.evolution_stage = 1
            self.fusion_history = ["bird"]
            self.loyalty = 90
            self.affinity = {"fire": 20}

    player = Entity(name="Player")
    player.pet = MockPet()

    analyzer = PetQuestAnalyzer()
    profile = analyzer.analyze_pet(player)

    assert profile is not None
    assert profile.species == "phoenix"
    assert profile.contract_type == "symbiosis"
    assert profile.evolution_stage == 1
    assert profile.fusion_history == ["bird"]
    assert profile.loyalty == 90
    assert profile.affinity == {"fire": 20}


if __name__ == "__main__":
    test_pet_profile_creation()
    test_pet_analyzer_no_pet()
    test_pet_analyzer_with_pet()
    print("All tests passed!")
