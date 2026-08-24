"""Unit tests for Pet Personality & Bonding System (Phase 6, Steps 49-72)"""

import pytest

from naRou.constants import (
    PERSONALITY_BRAVE,
    PERSONALITY_COWARDLY,
    PERSONALITY_CALM,
    PERSONALITY_GLUTTONOUS,
    PERSONALITY_AGGRESSIVE,
    FOOD_TAG_MEAT,
    FOOD_TAG_FISH,
    FOOD_TAG_SWEET,
)
from naRou.ecs.entity import Entity
from naRou.systems.item_system import Item
from naRou.systems.pet_personality_system import PetPersonalitySystem


def test_pet_personality_assignment():
    pet = Entity(name="Poppy", is_pet=True)
    assigned = PetPersonalitySystem.assign_random_personality(pet, [PERSONALITY_CALM, PERSONALITY_BRAVE])
    assert assigned in (PERSONALITY_CALM, PERSONALITY_BRAVE)
    assert pet.personality == assigned


def test_feed_pet_favorite_food_and_rotten_food():
    pet = Entity(name="Puppy", is_pet=True)
    pet.bond = 50
    pet.personality = PERSONALITY_BRAVE
    pet.favorite_food_tags = [FOOD_TAG_MEAT]

    meat = Item(x=0, y=0, char="%", color=(255, 100, 100), name="新鮮な肉", category="food")
    meat.food_tags = [FOOD_TAG_MEAT]

    # 1. 好物を与える (絆 +10)
    success, new_bond, msg = PetPersonalitySystem.feed_pet(pet, meat)
    assert success is True
    assert new_bond == 60
    assert pet.bond == 60
    assert "大好物" in msg

    # 2. 腐った食料を与える (絆 -5)
    rotten_food = Item(x=0, y=0, char="%", color=(150, 150, 100), name="腐ったパン", category="food")
    rotten_food.food_tags = ["vegetable"]
    rotten_food.rotten = True

    success, new_bond, msg = PetPersonalitySystem.feed_pet(pet, rotten_food)
    assert success is True
    assert new_bond == 55
    assert pet.bond == 55
    assert "苦悶" in msg


def test_pet_equipment_restrictions_by_bond():
    pet = Entity(name="Sister", is_pet=True)
    pet.bond = 30  # 絆が低い

    legendary_sword = Item(x=0, y=0, char="|", color=(255, 215, 0), name="神剣レーヴァテイン", category="weapon")
    legendary_sword.rarity = "god"

    normal_sword = Item(x=0, y=0, char="|", color=(200, 200, 200), name="ブロードソード", category="weapon")
    normal_sword.rarity = "normal"

    # 低絆では高レア装備不可
    can_equip, msg = PetPersonalitySystem.can_equip_item(pet, legendary_sword)
    assert can_equip is False
    assert "足りず" in msg

    # 通常装備は可能
    can_equip, msg = PetPersonalitySystem.can_equip_item(pet, normal_sword)
    assert can_equip is True

    # 絆が50を超えると高レア装備可能
    pet.bond = 65
    can_equip, msg = PetPersonalitySystem.can_equip_item(pet, legendary_sword)
    assert can_equip is True


def test_pet_ai_personality_decision():
    pet = Entity(name="GuardPet", is_pet=True)
    pet.max_hp = 100
    player = Entity(name="Master", is_player=True)

    enemy_weak = Entity(name="Goblin", x=5, y=5)
    enemy_weak.hp = 10
    enemy_weak.max_hp = 20

    enemy_boss = Entity(name="Dragon", x=10, y=10)
    enemy_boss.hp = 80
    enemy_boss.max_hp = 200

    enemies = [enemy_weak, enemy_boss]

    # 1. 勇敢 (BRAVE): 最強の敵を優先
    pet.personality = PERSONALITY_BRAVE
    pet.hp = 100
    decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, enemies)
    assert decision["action"] == "attack"
    assert decision["target"] == enemy_boss

    # 2. 冷静 (CALM): 瀕死/低HPの敵を優先
    pet.personality = PERSONALITY_CALM
    decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, enemies)
    assert decision["action"] == "attack"
    assert decision["target"] == enemy_weak

    # 3. 臆病 (COWARDLY): HPが50%未満になるとプレイヤーの背後へ逃走
    pet.personality = PERSONALITY_COWARDLY
    pet.hp = 30  # 30% HP
    decision = PetPersonalitySystem.evaluate_ai_behavior(pet, player, enemies)
    assert decision["action"] == "retreat_to_player"
    assert decision["target"] == player

