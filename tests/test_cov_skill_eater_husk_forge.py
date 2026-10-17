"""Coverage tests for skill_eater_husk_forge (PuppetForgeSystem)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from naRou.ecs.components.components import HuskComponent

from skill_eater_husk_forge import PuppetForgeSystem


def _make_husk(slots: int = 2, loyalty: int = 0, skills=None, codes=None) -> HuskComponent:
    return HuskComponent(
        husk_id="h1",
        source_monster="goblin",
        tier=2,
        slots=slots,
        loyalty=loyalty,
        injected_skills=list(skills or []),
        injected_codes=list(codes or []),
    )


class TestPuppetForgeSystemInit:
    def test_skill_attributes(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.skill_attributes["fire_bolt"] == "attack"
        assert forge.skill_attributes["heal"] == "defense"
        assert forge.skill_attributes["dash"] == "movement"
        assert forge.skill_attributes["unknown_skill"] == "attack"


class TestCalcControlLoad:
    def test_empty(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.calc_control_load(_make_husk()) == 0

    def test_skills_and_codes(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(skills=["fire_bolt", "ice_shard"], codes=["code_a"])
        assert forge.calc_control_load(husk) == 2 * 10 + 1 * 5  # 25


class TestInjectSkill:
    def test_normal(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(slots=3)
        forge.inject_skill(husk, "fire_bolt")
        assert husk.injected_skills == ["fire_bolt"]

    def test_slots_full_raises(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(slots=1, skills=["fire_bolt"])
        with pytest.raises(ValueError, match="slots full"):
            forge.inject_skill(husk, "ice_shard")


class TestInjectCode:
    def test_normal(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(slots=4)  # max code slots = 4 // 2 = 2
        forge.inject_code(husk, "code_a")
        assert husk.injected_codes == ["code_a"]

    def test_min_one_code_slot(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(slots=1)  # max(1, 1 // 2) = 1
        forge.inject_code(husk, "code_a")
        assert husk.injected_codes == ["code_a"]

    def test_code_slots_full_raises(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(slots=2, codes=["code_a"])  # max code slots = 1
        with pytest.raises(ValueError, match="code slots full"):
            forge.inject_code(husk, "code_b")


class TestRoleOf:
    def test_no_skills_defaults_escort(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.role_of(_make_husk(skills=[])) == "escort"

    def test_attack_majority_escort(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.role_of(_make_husk(skills=["fire_bolt", "slash"])) == "escort"

    def test_defense_majority_turret(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.role_of(_make_husk(skills=["heal", "shield"])) == "turret"

    def test_movement_majority_drone(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.role_of(_make_husk(skills=["dash", "teleport"])) == "drone"

    def test_unknown_skill_treated_as_attack(self) -> None:
        forge = PuppetForgeSystem()
        assert forge.role_of(_make_husk(skills=["mystery_skill"])) == "escort"

    def test_tie_priority_attack(self) -> None:
        forge = PuppetForgeSystem()
        # attack=1, defense=1 -> attack wins priority
        assert forge.role_of(_make_husk(skills=["fire_bolt", "heal"])) == "escort"


class TestRebellionRisk:
    def test_zero_load_zero_risk(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(loyalty=50)
        assert forge.rebellion_risk(husk) == 0.0

    def test_high_load_high_risk(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(skills=["s1", "s2", "s3"], codes=["c1"], loyalty=0)
        risk = forge.rebellion_risk(husk)
        assert risk > 0.0

    def test_clamped_at_zero(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(loyalty=100)
        assert forge.rebellion_risk(husk) == 0.0


class TestEffectivePower:
    def test_base_power(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk()
        assert forge.effective_power(husk, protocol_rank=0) == 1.0

    def test_rank_increases_power(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk()
        p0 = forge.effective_power(husk, protocol_rank=0)
        p10 = forge.effective_power(husk, protocol_rank=10)
        assert p10 > p0
        assert p10 == 2.0

    def test_minimum_0_1(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(skills=["s1"] * 20, loyalty=0)  # very high risk
        assert forge.effective_power(husk, protocol_rank=0) >= 0.1


class TestCreateUnit:
    def test_normal(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(skills=["fire_bolt"], slots=2)
        unit = forge.create_unit(husk, protocol_rank=2)
        assert unit.unit_id == "unit_h1"
        assert unit.role == "escort"
        assert unit.husk_ref == "h1"
        assert unit.hp == int((1.0 + 0.1 * 2) * 10)  # 12
        assert unit.max_hp == unit.hp
        assert unit.injected_skills == ["fire_bolt"]

    def test_turret_role(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(skills=["heal", "shield"])
        unit = forge.create_unit(husk, protocol_rank=0)
        assert unit.role == "turret"

    def test_drone_role(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(skills=["dash", "teleport"])
        unit = forge.create_unit(husk, protocol_rank=0)
        assert unit.role == "drone"

    def test_codes_copied(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk(codes=["code_a", "code_b"])
        unit = forge.create_unit(husk)
        assert unit.injected_codes == ["code_a", "code_b"]

    def test_insufficient_gold_raises(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk()
        player = MagicMock()
        player.gold = 0
        player.aldo_currency = 0
        with patch("skill_eater_husk_forge.get_config", return_value=100), \
             patch("naRou.ecs.components.components.EconomyComponent", None), \
             patch.object(type(player), "get_component", return_value=None):
            with pytest.raises(ValueError, match="Insufficient gold"):
                forge.create_unit(husk, player=player)

    def test_get_config_none_skips_resource(self) -> None:
        forge = PuppetForgeSystem()
        husk = _make_husk()
        player = MagicMock()
        player.gold = 0
        with patch("skill_eater_husk_forge.get_config", return_value=None):
            unit = forge.create_unit(husk, player=player)
        assert unit is not None
