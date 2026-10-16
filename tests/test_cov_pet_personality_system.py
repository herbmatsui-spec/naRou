"""改善案7: ペット性格システムのテスト。

pet_personality_system.py の実装を検証:
- 性格・好物のランダム付与
- 絆度計算・正規化
- 餌やり（好物・通常・腐敗/呪い・食いしん坊ボーナス）
- 装備制限（高レアは絆50以上必要）
- 絆によるステータス補正
- 性格ベースのAI行動決定
- エンジン統合の絆HPボーナス適用
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from naRou.constants import (
    FOOD_TAG_FISH,
    FOOD_TAG_MEAT,
    PERSONALITY_AGGRESSIVE,
    PERSONALITY_BRAVE,
    PERSONALITY_CALM,
    PERSONALITY_COWARDLY,
    PERSONALITY_GLUTTONOUS,
)
from pet_personality_system import PetPersonalitySystem


def _make_pet(**kwargs) -> SimpleNamespace:
    defaults = dict(
        name="テストペット",
        personality=PERSONALITY_BRAVE,
        bond=50,
        favorite_food_tags=[],
        hp=100,
        max_hp=100,
        pet_ai=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestPetPersonalityAssignment:
    def test_assign_random_personality(self) -> None:
        pet = _make_pet()
        chosen = PetPersonalitySystem.assign_random_personality(
            pet, [PERSONALITY_BRAVE, PERSONALITY_COWARDLY]
        )
        assert chosen in (PERSONALITY_BRAVE, PERSONALITY_COWARDLY)
        assert pet.personality == chosen

    def test_initialize_pet_personality_when_unset(self) -> None:
        pet = _make_pet(personality=None, favorite_food_tags=None)
        chosen = PetPersonalitySystem.initialize_pet_personality(pet)
        assert pet.personality is not None
        assert chosen == pet.personality
        assert pet.favorite_food_tags is not None
        assert len(pet.favorite_food_tags) == 1

    def test_initialize_pet_personality_respects_existing(self) -> None:
        pet = _make_pet(personality=PERSONALITY_GLUTTONOUS, favorite_food_tags=[FOOD_TAG_MEAT])
        chosen = PetPersonalitySystem.initialize_pet_personality(pet)
        assert chosen == PERSONALITY_GLUTTONOUS
        assert pet.favorite_food_tags == [FOOD_TAG_MEAT]


class TestPetBondCalculation:
    def test_get_effective_bond_percent_entity_priority(self) -> None:
        pet = _make_pet(bond=77)
        assert PetPersonalitySystem.get_effective_bond_percent(pet) == 77

    def test_get_effective_bond_percent_clamped(self) -> None:
        pet = _make_pet(bond=150)
        assert PetPersonalitySystem.get_effective_bond_percent(pet) == 100
        pet.bond = -10
        assert PetPersonalitySystem.get_effective_bond_percent(pet) == 0

    def test_get_effective_bond_percent_from_pet_ai(self) -> None:
        pet = _make_pet(bond=None, pet_ai=SimpleNamespace(bond=700, contract_id="default"))
        with patch(
            "pet_contract_system.REGISTRY.get",
            return_value=SimpleNamespace(max_bond=1000),
        ):
            assert PetPersonalitySystem.get_effective_bond_percent(pet) == 70

    def test_get_effective_bond_percent_default(self) -> None:
        pet = _make_pet(bond=None, pet_ai=None)
        assert PetPersonalitySystem.get_effective_bond_percent(pet) == 50


class TestPetFeeding:
    def _make_food(self, category="food", tags=None, cursed=False, rotten=False) -> SimpleNamespace:
        return SimpleNamespace(
            name="テスト食料",
            category=category,
            food_tags=tags or [],
            cursed=cursed,
            rotten=rotten,
        )

    def test_feed_favorite_food(self) -> None:
        pet = _make_pet(bond=50, personality=PERSONALITY_BRAVE, favorite_food_tags=[FOOD_TAG_MEAT])
        food = self._make_food(tags=[FOOD_TAG_MEAT])
        ok, new_bond, msg = PetPersonalitySystem.feed_pet(pet, food)
        assert ok is True
        assert new_bond == 60  # 50 + 10
        assert "大喜び" in msg

    def test_feed_gluttonous_bonus(self) -> None:
        pet = _make_pet(
            bond=50, personality=PERSONALITY_GLUTTONOUS, favorite_food_tags=[FOOD_TAG_MEAT]
        )
        food = self._make_food(tags=[FOOD_TAG_MEAT])
        _, new_bond, _ = PetPersonalitySystem.feed_pet(pet, food)
        assert new_bond == 63  # 50 + 10 + 3

    def test_feed_normal_food(self) -> None:
        pet = _make_pet(bond=50, personality=PERSONALITY_BRAVE, favorite_food_tags=[FOOD_TAG_MEAT])
        food = self._make_food(tags=[FOOD_TAG_FISH])
        _, new_bond, msg = PetPersonalitySystem.feed_pet(pet, food)
        assert new_bond == 53  # 50 + 3
        assert "美味しそう" in msg

    def test_feed_gluttonous_normal_bonus(self) -> None:
        pet = _make_pet(
            bond=50, personality=PERSONALITY_GLUTTONOUS, favorite_food_tags=[FOOD_TAG_MEAT]
        )
        food = self._make_food(tags=[FOOD_TAG_FISH])
        _, new_bond, _ = PetPersonalitySystem.feed_pet(pet, food)
        assert new_bond == 55  # 50 + 3 + 2

    def test_feed_cursed_or_rotten(self) -> None:
        pet = _make_pet(bond=50, personality=PERSONALITY_BRAVE)
        food = self._make_food(tags=[FOOD_TAG_MEAT], cursed=True)
        _, new_bond, msg = PetPersonalitySystem.feed_pet(pet, food)
        assert new_bond == 45  # 50 - 5
        assert "苦悶" in msg

    def test_feed_not_food(self) -> None:
        pet = _make_pet(bond=50, personality=PERSONALITY_BRAVE)
        food = SimpleNamespace(name="剣", category="weapon", food_tags=[])
        ok, bond, msg = PetPersonalitySystem.feed_pet(pet, food)
        assert ok is False
        assert bond == 50
        assert "食べられません" in msg

    def test_feed_none(self) -> None:
        pet = _make_pet(bond=50, personality=PERSONALITY_BRAVE)
        ok, bond, msg = PetPersonalitySystem.feed_pet(pet, None)
        assert ok is False
        assert bond == 50
        assert "アイテムがありません" in msg


class TestPetEquipRestriction:
    def test_can_equip_high_rarity_requires_bond_50(self) -> None:
        pet = _make_pet(bond=30)
        item = SimpleNamespace(name="神器剣", rarity="god")
        ok, msg = PetPersonalitySystem.can_equip_item(pet, item)
        assert ok is False
        assert "信頼" in msg

    def test_can_equip_high_rarity_with_enough_bond(self) -> None:
        pet = _make_pet(bond=50)
        item = SimpleNamespace(name="神器剣", rarity="god")
        ok, msg = PetPersonalitySystem.can_equip_item(pet, item)
        assert ok is True

    def test_can_equip_normal_rarity(self) -> None:
        pet = _make_pet(bond=30)
        item = SimpleNamespace(name="鉄剣", rarity="normal")
        ok, _ = PetPersonalitySystem.can_equip_item(pet, item)
        assert ok is True


class TestPetBondStatModifiers:
    def test_get_bond_stat_modifiers_max(self) -> None:
        pet = _make_pet(bond=100)
        mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
        assert mods["hp_bonus"] == 40
        assert mods["hit_bonus"] == 10
        assert mods["damage_multiplier"] == 1.25
        assert mods["dv_bonus"] == 8

    def test_get_bond_stat_modifiers_half(self) -> None:
        pet = _make_pet(bond=50)
        mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
        assert mods["hp_bonus"] == 20
        assert mods["damage_multiplier"] == 1.12


class TestPetAIBehavior:
    def setup_method(self) -> None:
        self.player = SimpleNamespace(name="プレイヤー", x=0, y=0, hp=100, max_hp=100)

    def _make_enemy(self, x, y, hp, max_hp=None) -> SimpleNamespace:
        return SimpleNamespace(x=x, y=y, hp=hp, max_hp=max_hp or hp)

    def test_no_enemies_follow_player(self) -> None:
        pet = _make_pet(x=0, y=0)
        result = PetPersonalitySystem.evaluate_ai_behavior(pet, self.player, [])
        assert result["action"] == "follow_player"
        assert result["target"] is self.player

    def test_cowardly_retreat_when_low_hp(self) -> None:
        pet = _make_pet(x=0, y=0, hp=30, max_hp=100, personality=PERSONALITY_COWARDLY)
        enemies = [self._make_enemy(5, 5, 50)]
        result = PetPersonalitySystem.evaluate_ai_behavior(pet, self.player, enemies)
        assert result["action"] == "retreat_to_player"

    def test_brave_attacks_strongest(self) -> None:
        pet = _make_pet(x=0, y=0, personality=PERSONALITY_BRAVE)
        enemies = [self._make_enemy(1, 1, 50), self._make_enemy(2, 2, 200)]
        result = PetPersonalitySystem.evaluate_ai_behavior(pet, self.player, enemies)
        assert result["action"] == "attack"
        assert result["target"].max_hp == 200

    def test_calm_attacks_weakest(self) -> None:
        pet = _make_pet(x=0, y=0, personality=PERSONALITY_CALM)
        enemies = [self._make_enemy(1, 1, 50), self._make_enemy(2, 2, 20)]
        result = PetPersonalitySystem.evaluate_ai_behavior(pet, self.player, enemies)
        assert result["action"] == "attack"
        assert result["target"].hp == 20

    def test_aggressive_attacks_closest(self) -> None:
        pet = _make_pet(x=0, y=0, personality=PERSONALITY_AGGRESSIVE)
        enemies = [self._make_enemy(10, 10, 50), self._make_enemy(1, 1, 50)]
        result = PetPersonalitySystem.evaluate_ai_behavior(pet, self.player, enemies)
        assert result["action"] == "attack"
        assert result["target"].x == 1

    def test_gluttonous_default_attacks_first(self) -> None:
        pet = _make_pet(x=0, y=0, personality=PERSONALITY_GLUTTONOUS)
        enemies = [self._make_enemy(1, 1, 50), self._make_enemy(2, 2, 50)]
        result = PetPersonalitySystem.evaluate_ai_behavior(pet, self.player, enemies)
        assert result["action"] == "attack"
        assert result["target"] is enemies[0]


class TestApplyBondGameplayEffects:
    def test_apply_bond_hp_bonus(self) -> None:
        engine = SimpleNamespace()
        pet = _make_pet(bond=100, max_hp=100, hp=100)
        engine.pet = pet
        PetPersonalitySystem.apply_bond_gameplay_effects(engine)
        assert pet.max_hp == 140  # 100 + 40
        assert pet._bond_applied_hp == 40
        # hp は max_hp を超えていないので変更されない
        assert pet.hp == 100

    def test_apply_bond_idempotent(self) -> None:
        engine = SimpleNamespace()
        pet = _make_pet(bond=100, max_hp=100, hp=100)
        engine.pet = pet
        PetPersonalitySystem.apply_bond_gameplay_effects(engine)
        first_max = pet.max_hp
        PetPersonalitySystem.apply_bond_gameplay_effects(engine)
        assert pet.max_hp == first_max  # 冪等

    def test_apply_bond_no_pet(self) -> None:
        engine = SimpleNamespace()
        # 例外なく終了すること
        PetPersonalitySystem.apply_bond_gameplay_effects(engine)

    def test_apply_bond_dead_pet(self) -> None:
        engine = SimpleNamespace()
        pet = _make_pet(bond=100, max_hp=100, hp=0)
        engine.pet = pet
        PetPersonalitySystem.apply_bond_gameplay_effects(engine)
        assert pet.max_hp == 100  # 変更なし
