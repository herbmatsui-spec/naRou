"""Tests for Pet Proposals 6-9."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pet_systems import (
    PetEquipmentManager,
    PetGuildManager,
    PetLegacyManager,
    PetTrainingManager,
)


class FakePet:
    def __init__(self, bond=0, level=1):
        self.bond = bond
        self.level = level
        self.equipment = {}
        self.completed_pet_training = []
        self.pet_legacy_flags = {}


# 提案6: equipment
def test_equipment():
    mgr = PetEquipmentManager()
    pet = FakePet(bond=300, level=20)
    assert mgr.can_equip(pet, "magic_collar")
    assert mgr.equip(pet, "collar", "magic_collar")
    bonuses = mgr.aggregate_bonuses(pet)
    assert bonuses.get("mp") == 15
    assert bonuses.get("intelligence") == 3
    # low bond pet can't equip
    low = FakePet(bond=0, level=1)
    assert not mgr.can_equip(low, "magic_collar")
    print("PASS: pet equipment equip + bonuses")


# 提案7: training
def test_training():
    mgr = PetTrainingManager()
    pet = FakePet(bond=300, level=15)
    assert mgr.can_enroll(pet, "magic_training", ["magic_tower", "library"])
    assert not mgr.can_enroll(
        pet, "magic_training", ["magic_tower"]
    )  # missing facility
    assert mgr.complete(pet, "magic_training")
    assert "magic_training" in pet.completed_pet_training
    print("PASS: pet training enroll + complete")


# 提案8: guild
def test_guild():
    mgr = PetGuildManager()
    lvl = mgr.guild_level("default_guild", 1600)
    assert lvl == 3
    buffs = mgr.active_buffs("default_guild", 1600)
    types = {b["type"] for b in buffs}
    assert "bond_gain_bonus" in types and "exp_bonus" in types
    print("PASS: pet guild level + buffs")


# 提案9: legacy
def test_legacy():
    mgr = PetLegacyManager()
    pts = mgr.compute_legacy_points(
        level=100, max_bond=1200, evolved_pets=1, legendary_pets=0
    )
    # base20 + (100//10)*3=30 + max_bond>=1000 ->5 + evolved1*8=8 = 63
    assert pts == 63
    pet = FakePet()
    avail = mgr.available_transfers({"max_bond_1000": True, "has_evolved_pet": True})
    assert len(avail) == 2
    mgr.apply_transfer(pet, avail[0])
    assert pet.pet_legacy_flags.get("bloodline_bonus") is True
    print("PASS: pet legacy points + transfer")


if __name__ == "__main__":
    test_equipment()
    test_training()
    test_guild()
    test_legacy()
    print("\nALL PET SYSTEM TESTS PASSED")
