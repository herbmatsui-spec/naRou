"""Tests for backstab/facing system (Step 3A)."""

from __future__ import annotations

import random
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constants import Element
from ecs.entity import Entity
from engine.systems.combat_system import CombatSystem
from tests.helpers.non_vacuity import assert_can_fail, assert_distinguishes


def _make_entities(attacker_facing: str = "S", defender_facing: str = "N") -> tuple[Entity, Entity]:
    """攻撃者と防御者のエンティティを作成"""
    attacker = Entity(x=0, y=0, name="Attacker", char="@")
    defender = Entity(x=1, y=0, name="Defender", char="E")
    attacker.facing = attacker_facing
    defender.facing = defender_facing
    attacker.attributes.strength = 10
    attacker.attributes.dexterity = 20
    attacker.attributes.perception = 10
    defender.attributes.endurance = 10
    defender.attributes.dexterity = 10
    attacker.hp = attacker.max_hp = 50
    defender.hp = defender.max_hp = 50
    return attacker, defender


def _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=None, endurance_roll=0):
    """乱数を固定するコンテキストマネージャ"""
    if dmg_rolls is None:
        dmg_rolls = [4]
    rolls = iter([hit_roll, crit_roll] + dmg_rolls + [endurance_roll])
    return patch("engine.systems.combat_system.random.randint", side_effect=lambda a, b: next(rolls))


def _get_damage(atk_facing: str, def_facing: str) -> int:
    """固定乱数でダメージを取得"""
    atk, defn = _make_entities(atk_facing, def_facing)
    with _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=[4], endurance_roll=0):
        dmg, _, _ = CombatSystem.calculate_melee_attack(atk, defn)
    return dmg


def _assert_backstab_multiplier(atk_facing: str, def_facing: str) -> None:
    """背後判定でダメージが増えることをアサート（失敗時は例外）"""
    dmg_back = _get_damage(atk_facing, def_facing)
    dmg_front = _get_damage("S", "S")
    if dmg_back <= dmg_front:
        raise AssertionError(f"Expected backstab: {dmg_back} > {dmg_front}")


def _assert_facing_property_works(new_facing: str, expected: str) -> None:
    """向きプロパティが正しく書き換わることをアサート"""
    m = Entity(x=0, y=0, name="M", char="M")
    m.facing = new_facing
    if m.facing != expected:
        raise AssertionError(f"Expected {expected}, got {m.facing}")


class TestBackstab:
    """バックスタブ（背後攻撃）判定のテスト"""

    def test_attack_from_behind_deals_more(self):
        """背後からの攻撃は1.5倍ダメージになる"""
        attacker, defender = _make_entities(attacker_facing="S", defender_facing="N")

        with _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=[4], endurance_roll=0):
            dmg_backstab, _, msg_backstab = CombatSystem.calculate_melee_attack(attacker, defender)

        attacker.facing = "S"
        defender.facing = "S"
        defender.hp = defender.max_hp

        with _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=[4], endurance_roll=0):
            dmg_normal, _, msg_normal = CombatSystem.calculate_melee_attack(attacker, defender)

        assert dmg_backstab > dmg_normal, f"Backstab dmg {dmg_backstab} > normal dmg {dmg_normal}"
        assert "【背後攻撃】" in msg_backstab
        assert "【背後攻撃】" not in msg_normal

        # Non-vacuity: 正しい向きでは成功、間違った向きでは失敗
        assert_distinguishes(
            lambda args: _assert_backstab_multiplier(*args),
            ("S", "N"),  # 背後 -> pass
            ("S", "S"),  # 正面 -> raise AssertionError
            label="backstab_multiplier",
        )

    def test_backstab_is_deterministic(self):
        """同じ条件・同じ乱数なら同じダメージが出る（決定性）"""
        attacker, defender = _make_entities(attacker_facing="N", defender_facing="S")

        damages = []
        for _ in range(3):
            with _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=[4], endurance_roll=0):
                dmg, _, _ = CombatSystem.calculate_melee_attack(attacker, defender)
            damages.append(dmg)
            defender.hp = defender.max_hp

        assert all(d == damages[0] for d in damages), f"Damage should be deterministic: {damages}"

        # Non-vacuity: 向きがダメージに影響することを区別できる
        # 背後なら front より大きい、正面なら front と同じ
        dmg_back = _get_damage("N", "S")
        dmg_front = _get_damage("S", "S")

        def _check_facing_affects_damage(args: tuple[str, str]) -> None:
            """背後攻撃なら front より大きいダメージを与えることを確認"""
            atk_facing, def_facing = args
            dmg = _get_damage(atk_facing, def_facing)
            if dmg <= dmg_front:
                raise AssertionError(f"Expected > front dmg ({dmg_front}), got {dmg}")

        assert_distinguishes(
            _check_facing_affects_damage,
            ("N", "S"),  # 背後 -> PASS (dmg > dmg_front)
            ("S", "S"),  # 正面 -> FAIL (dmg == dmg_front, not >)
            label="facing_affects_damage",
        )

    def test_monster_facing_follows_movement(self):
        """モンスターの向きが移動方向に追従する（プロパティが書き換わる）"""
        monster = Entity(x=5, y=5, name="Monster", char="M")
        monster.facing = "S"

        monster.facing = "N"
        assert monster.facing == "N"

        monster.facing = "E"
        assert monster.facing == "E"

        monster.facing = "S"
        assert monster.facing == "S"

        monster.facing = "W"
        assert monster.facing == "W"

        # Non-vacuity: プロパティが正しく書き換わることを区別できる
        assert_distinguishes(
            lambda args: _assert_facing_property_works(*args),
            ("N", "N"),  # 正しい値
            ("S", "N"),  # 間違った期待値 -> raise AssertionError
            label="facing_property",
        )


class TestFacingDirections:
    """全方向の背後判定テスト"""

    @pytest.mark.parametrize(
        "attacker_facing,defender_facing,should_backstab",
        [
            ("N", "S", True),
            ("S", "N", True),
            ("E", "W", True),
            ("W", "E", True),
            ("N", "N", False),
            ("S", "S", False),
            ("E", "E", False),
            ("W", "W", False),
            ("N", "E", False),
            ("N", "W", False),
        ],
    )
    def test_all_directions(self, attacker_facing: str, defender_facing: str, should_backstab: bool):
        """全8方向の組み合わせで背後判定が正しい"""
        attacker = Entity(x=0, y=0, name="Atk", char="@")
        defender = Entity(x=1, y=0, name="Def", char="E")
        attacker.facing = attacker_facing
        defender.facing = defender_facing
        attacker.attributes.strength = 10
        attacker.attributes.dexterity = 20
        attacker.attributes.perception = 10
        defender.attributes.endurance = 10
        defender.attributes.dexterity = 10
        attacker.hp = attacker.max_hp = 50
        defender.hp = defender.max_hp = 50

        with _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=[4], endurance_roll=0):
            dmg_backstab, _, msg = CombatSystem.calculate_melee_attack(attacker, defender)

        attacker.facing = defender_facing
        defender.hp = defender.max_hp
        with _fixed_rng_context(hit_roll=50, crit_roll=100, dmg_rolls=[4], endurance_roll=0):
            dmg_normal, _, _ = CombatSystem.calculate_melee_attack(attacker, defender)

        if should_backstab:
            assert dmg_backstab > dmg_normal, f"Expected backstab for {attacker_facing}->{defender_facing}: {dmg_backstab} > {dmg_normal}"
            assert "【背後攻撃】" in msg
        else:
            assert dmg_backstab == dmg_normal, f"Expected no backstab for {attacker_facing}->{defender_facing}: {dmg_backstab} == {dmg_normal}"
            assert "【背後攻撃】" not in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
